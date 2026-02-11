"""
Expert Pilot Controller.
Implements Pure Pursuit for steering and Curvature-based speed control.
Generates 'expert' driving behavior for training the RF model.
"""

import math
import numpy as np
from dataclasses import dataclass
from typing import Tuple

from ..track.track_model import TrackModel

@dataclass
class PilotConfig:
    lookahead_min_m: float = 15.0
    lookahead_gain: float = 0.8  # lookahead = min + gain * speed
    steer_gain: float = 1.2
    
    max_speed_mps: float = 80.0 # ~290 km/h (Dottinger Hohe)
    cornering_speed_factor: float = 3.5 # speed = sqrt(lat_accel / curvature)
    max_lat_accel_g: float = 2.5 # High downforce GT3
    
    throttle_kp: float = 2.0
    brake_kp: float = 5.0

class ExpertPilot:
    def __init__(self, track_model: TrackModel, config: PilotConfig = PilotConfig()):
        self.track = track_model
        self.config = config
        
    def compute_control(
        self, 
        current_speed_mps: float,
        current_heading_rad: float,
        track_x_m: float,
        track_y_m: float,
        current_dist_m: float
    ) -> Tuple[float, float, float]:
        """
        Compute control inputs (steering, throttle, brake).
        """
        cfg = self.config
        
        # 1. Pure Pursuit Steering
        # Calculate lookahead distance
        lookahead_dist = cfg.lookahead_min_m + cfg.lookahead_gain * current_speed_mps
        
        # Get target point on track centerline
        target_dist = current_dist_m + lookahead_dist
        target_state = self.track.get_state_at_distance(target_dist)
        tx, ty = target_state["x"], target_state["y"]
        
        # Transform target to vehicle frame
        dx = tx - track_x_m
        dy = ty - track_y_m
        
        # Rotate into vehicle frame
        # P_veh = Rot(-heading) * P_global
        local_x = math.cos(-current_heading_rad) * dx - math.sin(-current_heading_rad) * dy
        local_y = math.sin(-current_heading_rad) * dx + math.cos(-current_heading_rad) * dy
        
        # Pure Pursuit curvature = 2*y / L^2
        pp_curvature = 2.0 * local_y / (lookahead_dist ** 2)
        
        # Steering angle (kinematic approx: delta = atan(L*k))
        # wheelbase ~ 2.7m
        steer_cmd = math.atan(2.7 * pp_curvature) * cfg.steer_gain
        
        # Normalize steering [-1, 1] (Assuming ~30 deg max lock = 0.5 rad)
        steering_norm = max(-1.0, min(1.0, steer_cmd / 0.5))
        
        # 2. Longitudinal Control (Speed Profile)
        # Lookahead curvature for speed limit
        # Check specific points ahead to find max curvature constraint
        curvatures = []
        for d in [0, 20, 50, 100, 150]:
            s = self.track.get_state_at_distance(current_dist_m + d)
            curvatures.append(abs(s["curvature"]))
            
        max_curv = max(curvatures) if curvatures else 0.0
        max_curv = max(0.0001, max_curv) # avoid div0
        
        # v_max = sqrt(a_lat_max / k)
        target_speed = math.sqrt((cfg.max_lat_accel_g * 9.81) / max_curv)
        target_speed = min(cfg.max_speed_mps, target_speed)
        
        # Simple P-Controller for speed
        speed_error = target_speed - current_speed_mps
        
        throttle_norm = 0.0
        brake_norm = 0.0
        
        if speed_error > 0:
            throttle_norm = min(1.0, speed_error * cfg.throttle_kp / 10.0)
        else:
            brake_norm = min(1.0, -speed_error * cfg.brake_kp / 20.0)
            
        return steering_norm, throttle_norm, brake_norm
