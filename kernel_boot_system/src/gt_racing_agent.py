"""
GT Racing Expert Agent — Integrates TypeScript GT Racing kernel as Python agent.
Executes deterministic racing simulation via Node.js bridge and verifies Replay Court.
"""

from typing import Dict, Any, Optional
import json
import hashlib
from datetime import datetime, timezone

from agent_pool import ExpertAgent
from node_bridge import NodeBridge
from replay_court_bridge import ReplayCourtBridge


class GTRacingAgent(ExpertAgent):
    """
    Expert agent that runs GT Racing '26 deterministic kernel.
    Uses Node.js subprocess to execute TypeScript simulation.
    """

    def __init__(self, ipfs_client=None):
        super().__init__("gt_racing")
        self.node_bridge = NodeBridge()
        self.replay_bridge = ReplayCourtBridge(ipfs_client) if ipfs_client else None
        self.last_replay_hash: Optional[str] = None
        self.last_replay_cid: Optional[str] = None

    def process(self, tick: int, runtime_block: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute GT Racing simulation and return leaderboard + Replay Court hash.
        
        Args:
            tick: Current kernel tick
            runtime_block: Unified tensor runtime block
        
        Returns:
            Agent output with leaderboard, Replay Court hash, and vehicles
        """
        # Extract GT Racing configuration from runtime block
        gt_config = self._extract_racing_config(runtime_block)
        
        print(f"  GT Racing config: seed={gt_config['seed']}, ticks={gt_config['sim_ticks']}")
        
        # Execute GT Racing simulation via Node.js bridge
        try:
            result = self.node_bridge.run_simulation(
                seed=gt_config["seed"],
                ticks=gt_config["sim_ticks"],
                remote_agents=False
            )
        except Exception as e:
            # Fail-closed: if GT Racing fails, return error but don't crash kernel
            return {
                "agent": self.name,
                "tick": tick,
                "error": str(e),
                "status": "FAILED"
            }
        
        # Verify Replay Court integrity
        if not result["ledger_valid"]:
            return {
                "agent": self.name,
                "tick": tick,
                "error": "Replay Court ledger verification failed",
                "status": "FAILED"
            }
        
        # Store hash for checkpoint
        self.last_replay_hash = result["ledger_head_hash"]
        
        # Pin Replay Court to IPFS (if bridge available)
        if self.replay_bridge:
            try:
                self.last_replay_cid = self.replay_bridge.pin_replay_court(
                    ledger_hash=result["ledger_head_hash"],
                    metadata={
                        "kernel_tick": tick,
                        "runtime_block_id": runtime_block["block_id"],
                        "seed": gt_config["seed"],
                        "ticks_simulated": result["ticks_simulated"]
                    }
                )
                print(f"  ✓ Replay Court pinned: {self.last_replay_cid}")
            except Exception as e:
                print(f"  ⚠️  IPFS pinning failed: {e}")
        
        # Return agent output
        output = {
            "agent": self.name,
            "tick": tick,
            "output": {
                "leaderboard": result["leaderboard"],
                "replay_court_hash": result["ledger_head_hash"],
                "replay_court_cid": self.last_replay_cid,
                "vehicles": result["vehicles"],
                "ticks_simulated": result["ticks_simulated"],
                "ledger_entries": result["ledger_entry_count"]
            }
        }
        
        self.outputs.append(output)
        return output

    def _extract_racing_config(self, runtime_block: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract GT Racing configuration from unified tensor runtime block.
        Uses tensor coordinates to derive racing parameters deterministically.
        """
        normalized_params = runtime_block["runtime_config"]["normalized_params"]
        tensor_coords = runtime_block["tensor_semantic"]["coordinates"]
        
        # Use tensor embedding to derive racing parameters
        # Coords[0-3] → track geometry
        # Coords[4-7] → vehicle params (reserved for future use)
        # Coords[8-11] → AI behaviors (reserved for future use)
        
        # Map coordinates to positive range [0, 1]
        def norm_coord(val: float) -> float:
            return (val + 1.0) / 2.0  # Assumes coords in [-1, 1]
        
        # Derive parameters (with sensible defaults if coords missing)
        if len(tensor_coords) >= 4:
            track_radius = 40 + (norm_coord(tensor_coords[0]) * 30)  # 40-70m
            sim_ticks = 50 + int(norm_coord(tensor_coords[1]) * 150)  # 50-200 ticks
        else:
            track_radius = 50
            sim_ticks = 100
        
        # Get seed from runtime block or metadata
        seed = runtime_block.get("metadata", {}).get("seed")
        if not seed:
            # Generate seed from runtime block integrity hash
            seed = runtime_block["integrity_hash"][:16]
        
        return {
            "seed": seed,
            "track_radius": int(track_radius),
            "sim_ticks": int(sim_ticks)
        }

    def get_replay_summary(self) -> Dict[str, Any]:
        """Get summary of last Replay Court execution"""
        return {
            "agent": self.name,
            "last_replay_hash": self.last_replay_hash,
            "last_replay_cid": self.last_replay_cid,
            "total_executions": len(self.outputs)
        }
