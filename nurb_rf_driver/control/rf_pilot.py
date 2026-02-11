"""
Random Forest Pilot.
Uses trained RF model to control the vehicle based on extracted features.
"""

import os
import joblib
import numpy as np
from typing import Tuple

from ..state.feature_extractor import FeatureExtractor
from ..track.track_model import TrackModel

MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models", "rf_driver_v1.joblib")

class RFPilot:
    def __init__(self, track_model: TrackModel):
        self.track = track_model # Not used by RF directly (reactive), but kept for interface consistency
        self.extractor = FeatureExtractor()
        
        print(f"🤖 Loading RF Model from {MODEL_PATH}...")
        self.model = joblib.load(MODEL_PATH)
        print("   Model loaded.")
        
    def compute_control(
        self, 
        current_speed_mps: float,
        current_heading_rad: float,
        track_x_m: float,
        track_y_m: float,
        current_dist_m: float,
        vehicle_state_obj=None 
    ) -> Tuple[float, float, float]:
        """
        Compute control inputs using RF model.
        Requires full vehicle state object for feature extraction.
        """
        
        if vehicle_state_obj is None:
            # Fallback or error?
            # Ideally we pass state object. 
            # If the interface in simulation loop passes unpacked args, we need to reconstructing 
            # or update the loop to pass the object.
            # ExpertPilot uses unpacked args to compute Pure Pursuit.
            # RFPilot needs FEATURES.
            # Most features are in the args (speed, heading, dist), but some (curvature lookahead) 
            # come from track model or state object.
            # SimEnv state object has them all.
            raise ValueError("RFPilot requires vehicle_state_obj")
            
        # Extract features
        # 1. Extract raw
        raw_features = self.extractor.extract_features(vehicle_state_obj)
        
        # 2. Normalize
        norm_features = self.extractor.normalize_features(raw_features)
        
        # 3. Predict
        # Reshape to (1, n_features)
        X = np.array([norm_features])
        y_pred = self.model.predict(X)[0]
        
        # 4. Unpack
        # Target order from FeatureExtractor
        # ["steering_command", "throttle_command", "brake_command"]
        steering = float(y_pred[0])
        throttle = float(y_pred[1])
        brake = float(y_pred[2])
        
        # Clip/Clamp
        steering = max(-1.0, min(1.0, steering))
        throttle = max(0.0, min(1.0, throttle))
        brake = max(0.0, min(1.0, brake))
        
        return steering, throttle, brake
