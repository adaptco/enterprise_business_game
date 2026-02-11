"""
Minimal v1 state space for Nürburgring RF driver.
Canonical data structures for simulation state.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class VehicleStateV1:
    """
    Minimal v1 vehicle state (13 core features).
    """
    # Core kinematics
    speed_mps: float
    yaw_rate_rad_s: float
    
    # Track-relative geometry
    track_progress_m: float
    distance_to_center_m: float  # + right, - left
    curvature_now_1pm: float
    curvature_10m_ahead_1pm: float
    curvature_30m_ahead_1pm: float
    grad_now: float
    
    # Local environment (raycast distances)
    dist_left_edge_m: float
    dist_right_edge_m: float
    
    # Control history (for smoothness)
    prev_steering_command: float
    prev_throttle_command: float
    prev_brake_command: float
    
    def to_feature_vector(self) -> list[float]:
        """Convert to RF input vector (ordered)."""
        return [
            self.speed_mps,
            self.yaw_rate_rad_s,
            self.track_progress_m,
            self.distance_to_center_m,
            self.curvature_now_1pm,
            self.curvature_10m_ahead_1pm,
            self.curvature_30m_ahead_1pm,
            self.grad_now,
            self.dist_left_edge_m,
            self.dist_right_edge_m,
            self.prev_steering_command,
            self.prev_throttle_command,
            self.prev_brake_command
        ]
    
    @staticmethod
    def feature_names() -> list[str]:
        """Return ordered feature names for RF training."""
        return [
            "speed_mps",
            "yaw_rate_rad_s",
            "track_progress_m",
            "distance_to_center_m",
            "curvature_now_1pm",
            "curvature_10m_ahead_1pm",
            "curvature_30m_ahead_1pm",
            "grad_now",
            "dist_left_edge_m",
            "dist_right_edge_m",
            "prev_steering_command",
            "prev_throttle_command",
            "prev_brake_command"
        ]


@dataclass
class ControlCommand:
    """AI control output."""
    steering_command: float  # -1.0 to 1.0 (normalized)
    throttle_command: float  # 0.0 to 1.0
    brake_command: float     # 0.0 to 1.0


@dataclass
class TrainingSample:
    """
    Single training sample (state + action + metadata).
    Maps directly to schema_training_sample.json.
    """
    # Metadata
    session_id: str
    lap_id: int
    timestep: int
    timestamp_ms: Optional[int] = None
    
    # State (current controls included in state for context)
    speed_mps: float = 0.0
    yaw_rate_rad_s: float = 0.0
    steering_angle_rad: float = 0.0
    throttle_input: float = 0.0
    brake_input: float = 0.0
    track_progress_m: float = 0.0
    distance_to_center_m: float = 0.0
    curvature_now_1pm: float = 0.0
    curvature_10m_ahead_1pm: float = 0.0
    curvature_30m_ahead_1pm: float = 0.0
    grad_now: float = 0.0
    dist_left_edge_m: float = 0.0
    dist_right_edge_m: float = 0.0
    
    # Action (expert labels)
    steering_command: float = 0.0
    throttle_command: float = 0.0
    brake_command: float = 0.0
    
    # Quality
    valid: bool = True
    event: str = ""  # '' | 'offtrack' | 'spin' | 'crash'
    
    def to_dict(self) -> dict:
        """Convert to dict for NDJSON export."""
        return {
            'session_id': self.session_id,
            'lap_id': self.lap_id,
            'timestep': self.timestep,
            'timestamp_ms': self.timestamp_ms,
            'speed_mps': self.speed_mps,
            'yaw_rate_rad_s': self.yaw_rate_rad_s,
            'steering_angle_rad': self.steering_angle_rad,
            'throttle_input': self.throttle_input,
            'brake_input': self.brake_input,
            'track_progress_m': self.track_progress_m,
            'distance_to_center_m': self.distance_to_center_m,
            'curvature_now_1pm': self.curvature_now_1pm,
            'curvature_10m_ahead_1pm': self.curvature_10m_ahead_1pm,
            'curvature_30m_ahead_1pm': self.curvature_30m_ahead_1pm,
            'grad_now': self.grad_now,
            'dist_left_edge_m': self.dist_left_edge_m,
            'dist_right_edge_m': self.dist_right_edge_m,
            'steering_command': self.steering_command,
            'throttle_command': self.throttle_command,
            'brake_command': self.brake_command,
            'valid': self.valid,
            'event': self.event
        }
