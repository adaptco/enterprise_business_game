"""
Code Sight WebSocket Server

Bridges the Python observability engine with TypeScript/React frontend,
streaming real-time observations and handling dynamic instrumentation commands.
"""

import asyncio
import json
import websockets
from typing import Set
from code_sight.core import get_code_sight, Observation, SightPoint


class CodeSightServer:
    """WebSocket server for real-time Code Sight streaming"""
    
    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.sight_engine = get_code_sight()
        self.running = False
        
    async def register_client(self, websocket: websockets.WebSocketServerProtocol):
        """Register a new client connection"""
        self.clients.add(websocket)
        print(f"[CodeSight Server] Client connected. Total clients: {len(self.clients)}")
        
        # Send current state to new client
        await self.send_initial_state(websocket)
        
    async def unregister_client(self, websocket: websockets.WebSocketServerProtocol):
        """Unregister a disconnected client"""
        self.clients.discard(websocket)
        print(f"[CodeSight Server] Client disconnected. Total clients: {len(self.clients)}")
    
    async def send_initial_state(self, websocket: websockets.WebSocketServerProtocol):
        """Send current sight points and recent observations to new client"""
        # Send all registered sight points
        for sp_name, sp in self.sight_engine.sight_points.items():
            await websocket.send(json.dumps({
                "type": "sight_point_registered",
                "payload": sp.to_dict()
            }))
        
        # Send recent observations
        recent_obs = self.sight_engine.ledger.get_observations(limit=50)
        for obs in recent_obs:
            await websocket.send(json.dumps({
                "type": "observation",
                "payload": obs.to_dict()
            }))
    
    async def broadcast_observation(self, observation: Observation):
        """Broadcast new observation to all connected clients"""
        if not self.clients:
            return
        
        message = json.dumps({
            "type": "observation",
            "payload": observation.to_dict()
        })
        
        # Send to all clients concurrently
        await asyncio.gather(
            *[client.send(message) for client in self.clients],
            return_exceptions=True
        )
    
    async def broadcast_sight_point(self, sight_point: SightPoint):
        """Broadcast new sight point registration to all clients"""
        if not self.clients:
            return
        
        message = json.dumps({
            "type": "sight_point_registered",
            "payload": sight_point.to_dict()
        })
        
        await asyncio.gather(
            *[client.send(message) for client in self.clients],
            return_exceptions=True
        )
    
    async def handle_client_message(self, websocket: websockets.WebSocketServerProtocol, message: str):
        """Handle incoming client commands"""
        try:
            data = json.loads(message)
            msg_type = data.get("type")
            payload = data.get("payload", {})
            
            if msg_type == "inject_metric":
                # Dynamic metric injection
                target = payload.get("target")
                metric_name = payload.get("metricName")
                threshold = payload.get("threshold")
                
                self.sight_engine.inject_metric(target, metric_name, threshold)
                print(f"[CodeSight Server] Injected metric: {target}.{metric_name}")
                
            elif msg_type == "inject_log":
                # Dynamic log injection
                target = payload.get("target")
                condition = payload.get("condition")
                message_text = payload.get("message")
                
                self.sight_engine.inject_log(target, condition, message_text)
                print(f"[CodeSight Server] Injected log: {target}")
                
            elif msg_type == "enable_sight_point":
                # Enable sight point
                name = payload.get("name")
                if name in self.sight_engine.sight_points:
                    self.sight_engine.sight_points[name].enabled = True
                    print(f"[CodeSight Server] Enabled sight point: {name}")
                    
            elif msg_type == "disable_sight_point":
                # Disable sight point
                name = payload.get("name")
                if name in self.sight_engine.sight_points:
                    self.sight_engine.sight_points[name].enabled = False
                    print(f"[CodeSight Server] Disabled sight point: {name}")
                    
        except Exception as e:
            print(f"[CodeSight Server] Error handling message: {e}")
    
    async def handler(self, websocket: websockets.WebSocketServerProtocol, path: str):
        """Handle WebSocket connection lifecycle"""
        await self.register_client(websocket)
        
        try:
            async for message in websocket:
                await self.handle_client_message(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            await self.unregister_client(websocket)
    
    async def observation_streamer(self):
        """Background task to stream observations from ledger"""
        last_seen_count = 0
        
        while self.running:
            # Check for new observations
            current_count = len(self.sight_engine.ledger.observations)
            
            if current_count > last_seen_count:
                # Get new observations
                new_obs = self.sight_engine.ledger.observations[last_seen_count:]
                
                for obs in new_obs:
                    await self.broadcast_observation(obs)
                
                last_seen_count = current_count
            
            await asyncio.sleep(0.1)  # 10Hz polling
    
    async def start(self):
        """Start the WebSocket server"""
        self.running = True
        
        print(f"[CodeSight Server] Starting on ws://{self.host}:{self.port}")
        
        # Start observation streamer in background
        streamer_task = asyncio.create_task(self.observation_streamer())
        
        # Start WebSocket server
        async with websockets.serve(self.handler, self.host, self.port):
            print(f"[CodeSight Server] Ready to accept connections")
            await asyncio.Future()  # Run forever
        
        streamer_task.cancel()
    
    def run(self):
        """Run the server (blocking)"""
        try:
            asyncio.run(self.start())
        except KeyboardInterrupt:
            print("\n[CodeSight Server] Shutting down...")


# Monkey-patch the sight engine to broadcast new sight points
_original_register = get_code_sight().register_sight_point
_server_instance = None

def _register_with_broadcast(sight_point: SightPoint):
    """Wrapper to broadcast sight point registration"""
    _original_register(sight_point)
    
    # Broadcast to connected clients if server is running
    if _server_instance and _server_instance.clients:
        asyncio.create_task(_server_instance.broadcast_sight_point(sight_point))

get_code_sight().register_sight_point = _register_with_broadcast


def start_server(host: str = "localhost", port: int = 8765):
    """Start the Code Sight WebSocket server"""
    global _server_instance
    _server_instance = CodeSightServer(host, port)
    _server_instance.run()


if __name__ == "__main__":
    import sys
    
    # Example: Start server with custom host/port
    host = sys.argv[1] if len(sys.argv) > 1 else "localhost"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8765
    
    print("""
    ============================================================
             Code Sight WebSocket Server
      Real-time Agent Observability & Multimodal Debugging
    ============================================================
    """)
    
    start_server(host, port)
