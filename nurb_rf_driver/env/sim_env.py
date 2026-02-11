"""
Deterministic simulation environment for Nürburgring RF driver.
Implements stable tick loop with fixed-point coordinates and hash chain.
"""

import random
import hashlib
import struct
import math
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, Tuple
import os

from .vehicle_dynamics import VehicleDynamics, VehicleParams
from ..track.track_model import TrackModel

# Default track path
TRACK_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "track", "track_nordschleife.json")


@dataclass
class VehicleState:
    """Complete vehicle state at a single tick."""
    # Position (meters)
    track_x_m: float
    track_y_m: float
    track_z_m: float
    
    # Velocity (m/s)
    speed_mps: float
    vx_mps: float
    vy_mps: float
    
    # Orientation (radians)
    heading_rad: float
    yaw_rate_rps: float
    
    # Controls (normalized [-1, 1] or [0, 1])
    steering_angle_norm: float
    throttle_norm: float
    brake_norm: float
    
    # Track metrics
    track_progress: float  # [0, 1]
    dist_to_centerline_m: float
    heading_error_rad: float
    
    # Track curvature lookahead
    curvature_now: float
    curvature_ahead_10m: float
    curvature_ahead_30m: float
    curvature_ahead_60m: float


@dataclass
class CoordInt:
    """Integer coordinate for deterministic phase space."""
    x: int
    y: int
    z: int
    
    def to_tuple(self) -> Tuple[int, int, int]:
        return (self.x, self.y, self.z)


class SimEnv:
    """
    Deterministic simulation environment with:
    - Fixed-point integer coordinates
    - Hash tensor chain for replay verification
    - Stable tick progression
    """
    
    def __init__(
        self,
        seed: int = 42,
        dt: float = 0.02,  # 50 Hz tick rate
        run_id: str = "sim_001",
        root_identity: str = "Han",
        track_path: str = TRACK_PATH
    ):
        self.seed = seed
        self.dt = dt
        self.run_id = run_id
        self.root_identity = root_identity
        
        # Initialize deterministic RNG
        random.seed(seed)
        
        # Initialize Physics & Track
        self.dynamics = VehicleDynamics()
        self.track = TrackModel(track_path)
        
        # Internal state tracking
        self.current_dist_m = 0.0
        
        # Tick state
        self.tick = 0
        self.time_elapsed = 0.0
        
        # Vehicle state
        self.vehicle_state = VehicleState(
            track_x_m=0.0,
            track_y_m=0.0,
            track_z_m=0.0,
            speed_mps=0.0,
            vx_mps=0.0,
            vy_mps=0.0,
            heading_rad=0.0,
            yaw_rate_rps=0.0,
            steering_angle_norm=0.0,
            throttle_norm=0.0,
            brake_norm=0.0,
            track_progress=0.0,
            dist_to_centerline_m=0.0,
            heading_error_rad=0.0,
            curvature_now=0.0,
            curvature_ahead_10m=0.0,
            curvature_ahead_30m=0.0,
            curvature_ahead_60m=0.0
        )
        
        # Hash chain state
        self.prev_chain_hash: Optional[str] = None
        
        # Fixed-point scaling factors
        self.SCALE_POS = 1000  # millimeters
        self.SCALE_ANG = 1_000_000  # microradians
        self.SCALE_VEL = 1000  # mm/s
    
    def seed_u64(self, namespace: str) -> int:
        """
        Generate deterministic 64-bit seed from root identity + run_id + tick.
        
        Args:
            namespace: Purpose namespace ("STATE", "RAG", "TENSOR")
        
        Returns:
            Deterministic unsigned 64-bit integer seed
        """
        msg = f"{self.root_identity}|{self.run_id}|{self.tick}|{namespace}"
        h = hashlib.sha256(msg.encode('utf-8')).digest()
        return int.from_bytes(h[:8], 'big', signed=False)
    
    def q_fixed(self, x: float, scale: int) -> int:
        """Quantize float to fixed-point integer."""
        return int(round(x * scale))
    
    def coord_from_state(self) -> CoordInt:
        """
        Convert vehicle state to integer coordinate.
        Enforces origin rule: [0,0,0] = 1 (z=1 basis).
        """
        x_i = self.q_fixed(self.vehicle_state.track_x_m, self.SCALE_POS)
        y_i = self.q_fixed(self.vehicle_state.track_y_m, self.SCALE_POS)
        z_i = self.q_fixed(self.vehicle_state.track_z_m, self.SCALE_POS)
        
        # Origin basis rule
        if x_i == 0 and y_i == 0 and z_i == 0:
            z_i = 1
        
        return CoordInt(x=x_i, y=y_i, z=z_i)
    
    def hash_state_tensor(self) -> str:
        """
        Compute deterministic hash over state tensor.
        Returns SHA256 hex string.
        """
        # Pack state into bytes with stable ordering
        buf = bytearray()
        buf += b"STATEv1\x00"
        buf += struct.pack(">Q", self.tick)
        buf += struct.pack(">d", self.time_elapsed)
        
        # Pack all state fields in fixed order
        state_dict = asdict(self.vehicle_state)
        for key in sorted(state_dict.keys()):
            buf += struct.pack(">f", float(state_dict[key]))
        
        return hashlib.sha256(bytes(buf)).hexdigest()
    
    def chain_hash(self, current_hex: str) -> str:
        """
        Chain current hash with previous hash.
        
        Args:
            current_hex: Current tick's state hash
        
        Returns:
            Chained hash hex string
        """
        if self.prev_chain_hash is None:
            prev = b"\x00" * 32
        else:
            prev = bytes.fromhex(self.prev_chain_hash)
        
        cur = bytes.fromhex(current_hex)
        return hashlib.sha256(prev + cur).hexdigest()
    
    def reset(self) -> VehicleState:
        """
        Reset environment to initial state.
        Returns initial vehicle state.
        """
        random.seed(self.seed)
        self.tick = 0
        self.time_elapsed = 0.0
        self.prev_chain_hash = None
        self.current_dist_m = 0.0
        
        # Reset vehicle to start position
        self.vehicle_state = VehicleState(
            track_x_m=0.0,
            track_y_m=0.0,
            track_z_m=0.0,
            speed_mps=0.0,
            vx_mps=0.0,
            vy_mps=0.0,
            heading_rad=0.0,
            yaw_rate_rps=0.0,
            steering_angle_norm=0.0,
            throttle_norm=0.0,
            brake_norm=0.0,
            track_progress=0.0,
            dist_to_centerline_m=0.0,
            heading_error_rad=0.0,
            curvature_now=0.0,
            curvature_ahead_10m=0.0,
            curvature_ahead_30m=0.0,
            curvature_ahead_60m=0.0
        )
        
        # Compute initial metadata
        return self.vehicle_state, self._compute_metadata()

    def _compute_metadata(self) -> Dict[str, Any]:
        """Compute current tick metadata and hashes."""
        coord_int = self.coord_from_state()
        seed_state = self.seed_u64("STATE")
        state_hash = self.hash_state_tensor()
        chained_hash = self.chain_hash(state_hash)
        self.prev_chain_hash = chained_hash
        
        return {
            "tick": self.tick,
            "timestamp_ms": int(self.time_elapsed * 1000),
            "coord_int": coord_int.to_tuple(),
            "seed_u64": seed_state,
            "state_hash": state_hash,
            "chain_hash": chained_hash
        }
        
        return self.vehicle_state
    
    def step(
        self,
        steering_command: float,
        throttle_command: float,
        brake_command: float
    ) -> Tuple[VehicleState, Dict[str, Any]]:
        """
        Advance simulation by one tick with given control inputs.
        
        Args:
            steering_command: Normalized steering [-1, 1]
            throttle_command: Normalized throttle [0, 1]
            brake_command: Normalized brake [0, 1]
        
        Returns:
            (new_state, metadata)
            metadata contains: tick, coord_int, seed, state_hash, chain_hash
        """
        # Update controls
        self.vehicle_state.steering_angle_norm = steering_command
        self.vehicle_state.throttle_norm = throttle_command
        self.vehicle_state.brake_norm = brake_command
        
        # Vehicle Dynamics Update
        new_speed, new_vx, new_vy, new_heading, new_yaw_rate = self.dynamics.update(
            dt=self.dt,
            current_speed=self.vehicle_state.speed_mps,
            current_vx=self.vehicle_state.vx_mps,
            current_vy=self.vehicle_state.vy_mps,
            current_heading=self.vehicle_state.heading_rad,
            current_yaw_rate=self.vehicle_state.yaw_rate_rps,
            steering_norm=steering_command,
            throttle_norm=throttle_command,
            brake_norm=brake_command
        )
        
        # Update State
        self.vehicle_state.speed_mps = new_speed
        self.vehicle_state.vx_mps = new_vx
        self.vehicle_state.vy_mps = new_vy
        self.vehicle_state.heading_rad = new_heading
        self.vehicle_state.yaw_rate_rps = new_yaw_rate
        
        # Update Position (Global)
        # Dynamics update returns velocity in vehicle frame usually, but our simple update 
        # returned global vx/vy updates if we assume small angle approx or if dyn handled it.
        # Let's verify vehicle_dynamics.py... It does:
        # current_vx += (ax + ...) * dt.
        # And pos update: track_x += vx * dt.
        
        # We need to integrate position here using the updated velocities
        self.vehicle_state.track_x_m += self.vehicle_state.vx_mps * self.dt
        self.vehicle_state.track_y_m += self.vehicle_state.vy_mps * self.dt
        
        # Update distance along track (projected)
        dist_step = self.vehicle_state.speed_mps * self.dt
        self.current_dist_m += dist_step
        if self.current_dist_m > self.track.total_length_m:
            self.current_dist_m -= self.track.total_length_m
            
        self.vehicle_state.track_progress = self.current_dist_m / self.track.total_length_m
        
        # Track Queries
        track_state = self.track.get_state_at_distance(self.current_dist_m)
        
        # Lateral error (simplified: distance between vehicle pos and track centerline point)
        # Get centerline point
        cx, cy = track_state["x"], track_state["y"]
        cheading = track_state["heading"]
        
        # Vector from centerline to vehicle
        dx = self.vehicle_state.track_x_m - cx
        dy = self.vehicle_state.track_y_m - cy
        
        # Project onto normal vector (-sin, cos)
        # Normal points Left if we follow standard frenet?
        # Tangent: (cos, sin). Normal (Left): (-sin, cos)
        lat_error = -math.sin(cheading) * dx + math.cos(cheading) * dy
        self.vehicle_state.dist_to_centerline_m = lat_error
        
        # Heading error
        ang_diff = self.vehicle_state.heading_rad - cheading
        # Normalize to [-pi, pi]
        ang_diff = (ang_diff + math.pi) % (2 * math.pi) - math.pi
        self.vehicle_state.heading_error_rad = ang_diff
        
        # Curvature Lookahead
        self.vehicle_state.curvature_now = track_state["curvature"]
        
        s_10 = self.current_dist_m + 10.0
        s_30 = self.current_dist_m + 30.0
        s_60 = self.current_dist_m + 60.0
        
        self.vehicle_state.curvature_ahead_10m = self.track.get_state_at_distance(s_10)["curvature"]
        self.vehicle_state.curvature_ahead_30m = self.track.get_state_at_distance(s_30)["curvature"]
        self.vehicle_state.curvature_ahead_60m = self.track.get_state_at_distance(s_60)["curvature"]
        
        # Advance tick
        # Advance tick
        self.tick += 1
        self.time_elapsed += self.dt
        
        metadata = self._compute_metadata()
        
        return self.vehicle_state, metadata
        
        return self.vehicle_state, metadata
    
    def get_state_dict(self) -> Dict[str, Any]:
        """Export current state as dictionary."""
        return asdict(self.vehicle_state)
