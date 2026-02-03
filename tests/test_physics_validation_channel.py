"""
Tests for Physics Validation Channel.
"""

import sys
import os
import unittest
import numpy as np

# Add project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ml.unity_bridge.physics_validation_channel import (
    PhysicsAgentInput,
    RCVDDynamics,
    PhysicsValidationChannel
)


class TestRCVDDynamics(unittest.TestCase):
    """Tests for RCVD dynamics validation."""
    
    def test_slip_angle_clamping(self):
        """Slip angles should be clamped to [-0.5, 0.5]."""
        rcvd = RCVDDynamics(
            slip_angle_front=1.0,  # Too high
            slip_angle_rear=-1.0,  # Too low
            lat_accel=10.0,
            cornering_stiffness_actual=50000.0
        )
        
        validated = rcvd.validate()
        
        self.assertAlmostEqual(validated.slip_angle_front, 0.5)
        self.assertAlmostEqual(validated.slip_angle_rear, -0.5)
        print(f"\n✅ Slip clamping: front={validated.slip_angle_front}, rear={validated.slip_angle_rear}")
    
    def test_lat_accel_clamping(self):
        """Lateral acceleration should be clamped to [-15, 15]."""
        rcvd = RCVDDynamics(
            slip_angle_front=0.1,
            slip_angle_rear=0.1,
            lat_accel=25.0,  # Too high
            cornering_stiffness_actual=50000.0
        )
        
        validated = rcvd.validate()
        
        self.assertAlmostEqual(validated.lat_accel, 15.0)
        print(f"\n✅ Lat accel clamping: {validated.lat_accel}")


class TestPhysicsAgentInput(unittest.TestCase):
    """Tests for PhysicsAgentInput validation."""
    
    def test_grip_penalty_from_slip(self):
        """Grip should decrease with high slip angles."""
        rcvd = RCVDDynamics(
            slip_angle_front=0.4,  # High slip
            slip_angle_rear=0.3,
            lat_accel=8.0,
            cornering_stiffness_actual=50000.0
        )
        
        physics_input = PhysicsAgentInput(
            agent_id="car_0",
            timestamp=0.0,
            velocity=50.0,
            yaw_rate=0.5,
            steering_angle=0.2,
            grip_mu=1.5,  # Original grip
            rcvd_dynamics=rcvd
        )
        
        validated = physics_input.validate()
        
        # Grip should be reduced due to slip
        self.assertLess(validated.grip_mu, physics_input.grip_mu)
        self.assertGreaterEqual(validated.grip_mu, 0.3)  # Minimum floor
        print(f"\n✅ Grip penalty: {physics_input.grip_mu:.2f} → {validated.grip_mu:.2f}")
    
    def test_velocity_clamping(self):
        """Velocity should be clamped to [0, 100]."""
        rcvd = RCVDDynamics(0.0, 0.0, 0.0, 50000.0)
        
        physics_input = PhysicsAgentInput(
            agent_id="car_0",
            timestamp=0.0,
            velocity=150.0,  # Too high
            yaw_rate=0.0,
            steering_angle=0.0,
            grip_mu=1.2,
            rcvd_dynamics=rcvd
        )
        
        validated = physics_input.validate()
        
        self.assertAlmostEqual(validated.velocity, 100.0)
        print(f"\n✅ Velocity clamping: {validated.velocity}")
    
    def test_to_validated_tensor(self):
        """Validated tensor should have correct shape and values."""
        rcvd = RCVDDynamics(0.1, -0.1, 5.0, 50000.0)
        
        physics_input = PhysicsAgentInput(
            agent_id="car_0",
            timestamp=0.0,
            velocity=50.0,
            yaw_rate=0.5,
            steering_angle=0.2,
            grip_mu=1.2,
            rcvd_dynamics=rcvd
        )
        
        validated = physics_input.validate()
        tensor = validated.to_validated_tensor()
        
        self.assertEqual(len(tensor), 4)
        self.assertEqual(tensor.dtype, np.float32)
        print(f"\n✅ Validated tensor: {tensor}")


class TestPhysicsValidationChannel(unittest.TestCase):
    """Tests for PhysicsValidationChannel."""
    
    def test_channel_initialization(self):
        """Channel should initialize with correct UUID."""
        channel = PhysicsValidationChannel()
        
        self.assertEqual(
            str(channel.CHANNEL_ID),
            "12345678-9abc-def0-1234-56789abcdef0"
        )
        print(f"\n✅ Channel ID: {channel.CHANNEL_ID}")
    
    def test_get_stats(self):
        """Channel should track message statistics."""
        channel = PhysicsValidationChannel()
        
        stats = channel.get_stats()
        
        self.assertEqual(stats['messages_processed'], 0)
        self.assertEqual(stats['violations_detected'], 0)
        self.assertEqual(stats['active_agents'], 0)
        print(f"\n✅ Channel stats: {stats}")


if __name__ == '__main__':
    print("=" * 60)
    print("  🔧 Physics Validation Channel Test Suite")
    print("=" * 60)
    unittest.main(verbosity=2)
