"""
Random Forest Driver Agent.
Clean tick-based API for real-time control.
"""

import joblib
import numpy as np
from pathlib import Path
from typing import Optional
import json

# Add state module
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from state.state_space import VehicleStateV1, ControlCommand


class RandomForestDriver:
    """
    RF-based driver agent with clean tick API.
    
    Usage:
        driver = RandomForestDriver.load_from_directory("data/models")
        
        for tick in simulation_loop:
            state_v1 = get_current_state()  # VehicleStateV1
            control = driver.tick(state_v1)
            apply_control(control)
    """
    
    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.metadata = None
        
        # Control history (for smoothness features)
        self.prev_steering = 0.0
        self.prev_throttle = 0.0
        self.prev_brake = 0.0
    
    @classmethod
    def load_from_directory(cls, model_dir: str) -> 'RandomForestDriver':
        """
        Load trained models from directory.
        
        Args:
            model_dir: Path to directory containing .joblib files and metadata
        
        Returns:
            Initialized RandomForestDriver
        """
        instance = cls()
        model_path = Path(model_dir)
        
        # Load models
        for target in ['steering', 'throttle', 'brake']:
            instance.models[target] = joblib.load(model_path / f"{target}.joblib")
        
        # Load scalers
        for name in ['features', 'steering', 'throttle', 'brake']:
            instance.scalers[name] = joblib.load(model_path / f"scaler_{name}.joblib")
        
        # Load metadata
        with open(model_path / "model_metadata.json") as f:
            instance.metadata = json.load(f)
        
        print(f"✓ Loaded RF driver from {model_dir}")
        print(f"  - Model version: {instance.metadata.get('version', 'unknown')}")
        print(f"  - Avg test R²: {instance._avg_test_r2():.4f}")
        
        return instance
    
    def tick(self, state: VehicleStateV1) -> ControlCommand:
        """
        Compute control commands for current state.
        
        Args:
            state: Current vehicle state (VehicleStateV1)
        
        Returns:
            ControlCommand with steering/throttle/brake
        """
        # Build feature vector (includes prev controls for smoothness)
        features = [
            state.speed_mps,
            state.yaw_rate_rad_s,
            state.track_progress_m,
            state.distance_to_center_m,
            state.curvature_now_1pm,
            state.curvature_10m_ahead_1pm,
            state.curvature_30m_ahead_1pm,
            state.grad_now,
            state.dist_left_edge_m,
            state.dist_right_edge_m,
            self.prev_steering,
            self.prev_throttle,
            self.prev_brake
        ]
        
        X = np.array([features], dtype=np.float32)
        
        # Normalize
        X_scaled = self.scalers['features'].transform(X)
        
        # Predict (scaled)
        predictions = {}
        for target in ['steering', 'throttle', 'brake']:
            y_pred_scaled = self.models[target].predict(X_scaled)
            y_pred = self.scalers[target].inverse_transform(
                y_pred_scaled.reshape(-1, 1)
            ).ravel()[0]
            predictions[target] = float(y_pred)
        
        # Clamp to valid ranges
        steering = np.clip(predictions['steering'], -1.0, 1.0)
        throttle = np.clip(predictions['throttle'], 0.0, 1.0)
        brake = np.clip(predictions['brake'], 0.0, 1.0)
        
        # Update history
        self.prev_steering = steering
        self.prev_throttle = throttle
        self.prev_brake = brake
        
        return ControlCommand(
            steering_command=steering,
            throttle_command=throttle,
            brake_command=brake
        )
    
    def reset(self):
        """Reset control history (e.g., at lap start)."""
        self.prev_steering = 0.0
        self.prev_throttle = 0.0
        self.prev_brake = 0.0
    
    def get_model_info(self) -> dict:
        """Return model metadata for logging."""
        if not self.metadata:
            return {}
        
        return {
            'model_version': self.metadata.get('version'),
            'train_data_hash': self.metadata.get('train_data_hash'),
            'n_estimators': self.metadata.get('n_estimators'),
            'timestamp': self.metadata.get('timestamp'),
            'avg_test_r2': self._avg_test_r2()
        }
    
    def _avg_test_r2(self) -> float:
        """Compute average test R² across all models."""
        if not self.metadata or 'metrics' not in self.metadata:
            return 0.0
        
        r2_values = [
            self.metadata['metrics'][target]['test_r2']
            for target in ['steering', 'throttle', 'brake']
            if target in self.metadata['metrics']
        ]
        
        return np.mean(r2_values) if r2_values else 0.0


# Example usage
if __name__ == "__main__":
    print("Example: Loading and using RF driver\n")
    
    # Simulate loading
    try:
        driver = RandomForestDriver.load_from_directory("../data/models")
        
        # Simulate tick
        state = VehicleStateV1(
            speed_mps=45.0,
            yaw_rate_rad_s=0.1,
            track_progress_m=1000.0,
            distance_to_center_m=0.5,
            curvature_now_1pm=0.02,
            curvature_10m_ahead_1pm=0.025,
            curvature_30m_ahead_1pm=0.03,
            grad_now=0.01,
            dist_left_edge_m=5.0,
            dist_right_edge_m=5.0,
            prev_steering_command=0.0,
            prev_throttle_command=0.8,
            prev_brake_command=0.0
        )
        
        control = driver.tick(state)
        
        print(f"\nPredicted control:")
        print(f"  - Steering: {control.steering_command:.4f}")
        print(f"  - Throttle: {control.throttle_command:.4f}")
        print(f"  - Brake: {control.brake_command:.4f}")
        
        print(f"\nModel info:")
        info = driver.get_model_info()
        for k, v in info.items():
            print(f"  - {k}: {v}")
    
    except FileNotFoundError:
        print("⚠️  Models not found. Train first with:")
        print("   python training/train_random_forest.py --data data/raw/expert.ndjson")
