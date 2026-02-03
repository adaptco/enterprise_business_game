"""
Physics Validation SideChannel for Unity ML-Agents Integration.

This SideChannel enables real-time physics validation between Python and Unity:
- Receives raw physics data from Unity agents
- Validates using Olley RCVD physics constraints  
- Returns validated tensor to Unity for observation space

Tensor Schema (12 floats):
0-2:  velocity_xyz (normalized by 80)
3-5:  angular_velocity_xyz (normalized by 5)
6:    grip_mu (validated, normalized by 2.0)
7:    lat_accel (validated, normalized by 15)
8:    slip_front (validated, [-0.5, 0.5])
9:    slip_rear (validated, [-0.5, 0.5])
10:   throttle_history (prev action)
11:   steer_history (prev action)
"""

# Try importing ML-Agents, fall back to stub for testing
try:
    from mlagents_envs.side_channel.side_channel import SideChannel, IncomingMessage, OutgoingMessage
    MLAGENTS_AVAILABLE = True
except ImportError:
    # Stub classes for testing without mlagents installed
    MLAGENTS_AVAILABLE = False
    
    class SideChannel:

        def __init__(self, channel_id):
            self.channel_id = channel_id

        def queue_message_to_send(self, msg):
            pass
    
    class IncomingMessage:

        def read_float32_list(self):
            return []
    
    class OutgoingMessage:

        def write_float32_list(self, data):
            pass

from uuid import UUID
import numpy as np
import logging
from dataclasses import dataclass
from typing import Optional, Dict
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class RCVDDynamics:
    """RCVD (Race Car Vehicle Dynamics) validated state."""
    slip_angle_front: float
    slip_angle_rear: float
    lat_accel: float
    cornering_stiffness_actual: float
    
    def validate(self) -> 'RCVDDynamics':
        """Apply physics constraints."""
        return RCVDDynamics(
            slip_angle_front=np.clip(self.slip_angle_front, -0.5, 0.5),
            slip_angle_rear=np.clip(self.slip_angle_rear, -0.5, 0.5),
            lat_accel=np.clip(self.lat_accel, -15.0, 15.0),
            cornering_stiffness_actual=np.clip(self.cornering_stiffness_actual, 0.0, 200000.0)
        )


@dataclass  
class PhysicsAgentInput:
    """Complete physics state for a racing agent."""
    agent_id: str
    timestamp: float
    velocity: float
    yaw_rate: float
    steering_angle: float
    grip_mu: float
    rcvd_dynamics: RCVDDynamics
    validator_mode: str = "soft"
    
    def validate(self) -> 'PhysicsAgentInput':
        """Apply all physics validations."""
        validated_rcvd = self.rcvd_dynamics.validate()
        
        # Grip clamping based on slip
        max_slip = max(abs(validated_rcvd.slip_angle_front), abs(validated_rcvd.slip_angle_rear))
        grip_penalty = 1.0 - (max_slip * 0.5)  # Lose grip with slip
        validated_grip = np.clip(self.grip_mu * grip_penalty, 0.3, 2.0)
        
        return PhysicsAgentInput(
            agent_id=self.agent_id,
            timestamp=self.timestamp,
            velocity=np.clip(self.velocity, 0.0, 100.0),
            yaw_rate=np.clip(self.yaw_rate, -5.0, 5.0),
            steering_angle=np.clip(self.steering_angle, -0.6, 0.6),
            grip_mu=validated_grip,
            rcvd_dynamics=validated_rcvd,
            validator_mode=self.validator_mode
        )
    
    def to_validated_tensor(self) -> np.ndarray:
        """Extract validated physics tensor (indices 6-9 in observation)."""
        return np.array([
            self.grip_mu,
            self.rcvd_dynamics.lat_accel,
            self.rcvd_dynamics.slip_angle_front,
            self.rcvd_dynamics.slip_angle_rear
        ], dtype=np.float32)


class PhysicsValidationChannel(SideChannel):
    """
    ML-Agents SideChannel for physics validation.
    
    Receives raw physics from Unity, validates via RCVD constraints,
    returns validated tensor for observation space.
    """
    
    # Unique channel ID (must match Unity C# side)
    CHANNEL_ID = UUID("12345678-9abc-def0-1234-56789abcdef0")
    
    def __init__(self, audit_log_path: Optional[str]=None):
        super().__init__(self.CHANNEL_ID)
        self.audit_log_path = audit_log_path
        self.violation_count = 0
        self.message_count = 0
        self.agent_states: Dict[str, PhysicsAgentInput] = {}
        
        logger.info(f"PhysicsValidationChannel initialized (ID: {self.CHANNEL_ID})")
    
    def on_message_received(self, msg: IncomingMessage) -> None:
        """
        Handle incoming physics data from Unity.
        
        Expected format: 16 floats (velocity, yaw_rate, steering, grip, + rcvd)
        """
        self.message_count += 1
        
        try:
            # Read raw physics data
            raw_data = msg.read_float32_list()
            
            if len(raw_data) < 16:
                logger.warning(f"Incomplete physics data: got {len(raw_data)}, expected 16")
                return
            
            # Parse into PhysicsAgentInput
            agent_id = f"car_{self.message_count % 64}"  # Support 64 parallel cars
            
            physics_input = PhysicsAgentInput(
                agent_id=agent_id,
                timestamp=raw_data[0],
                velocity=raw_data[1],
                yaw_rate=raw_data[2],
                steering_angle=raw_data[3],
                grip_mu=raw_data[4],
                rcvd_dynamics=RCVDDynamics(
                    slip_angle_front=raw_data[12],
                    slip_angle_rear=raw_data[13],
                    lat_accel=raw_data[14],
                    cornering_stiffness_actual=raw_data[15]
                ),
                validator_mode="soft"
            )
            
            # Validate physics
            validated = physics_input.validate()
            
            # Check for violations
            if self._check_violation(physics_input, validated):
                self.violation_count += 1
                if self.audit_log_path:
                    self._log_violation(physics_input, validated)
            
            # Store validated state
            self.agent_states[agent_id] = validated
            
            # Send validated tensor back to Unity
            validated_tensor = validated.to_validated_tensor()
            out_msg = OutgoingMessage()
            out_msg.write_float32_list(validated_tensor.tolist())
            self.queue_message_to_send(out_msg)
            
        except Exception as e:
            logger.error(f"Physics validation error: {e}")
    
    def _check_violation(self, raw: PhysicsAgentInput, validated: PhysicsAgentInput) -> bool:
        """Check if validation made significant changes."""
        grip_delta = abs(raw.grip_mu - validated.grip_mu)
        lat_accel_delta = abs(raw.rcvd_dynamics.lat_accel - validated.rcvd_dynamics.lat_accel)
        
        # Threshold for "significant" violation
        return grip_delta > 0.1 or lat_accel_delta > 1.0
    
    def _log_violation(self, raw: PhysicsAgentInput, validated: PhysicsAgentInput) -> None:
        """Log physics violation to audit file."""
        violation = {
            "timestamp": datetime.now().isoformat(),
            "agent_id": raw.agent_id,
            "raw_grip": raw.grip_mu,
            "validated_grip": validated.grip_mu,
            "raw_lat_accel": raw.rcvd_dynamics.lat_accel,
            "validated_lat_accel": validated.rcvd_dynamics.lat_accel
        }
        
        with open(self.audit_log_path, "a") as f:
            import json
            f.write(json.dumps(violation) + "\n")
    
    def get_stats(self) -> Dict[str, int]:
        """Get channel statistics."""
        return {
            "messages_processed": self.message_count,
            "violations_detected": self.violation_count,
            "active_agents": len(self.agent_states)
        }


# Singleton for trainer integration
_physics_channel: Optional[PhysicsValidationChannel] = None


def get_physics_channel(audit_log: Optional[str]=None) -> PhysicsValidationChannel:
    """Get or create the physics validation channel."""
    global _physics_channel
    if _physics_channel is None:
        _physics_channel = PhysicsValidationChannel(audit_log)
    return _physics_channel
