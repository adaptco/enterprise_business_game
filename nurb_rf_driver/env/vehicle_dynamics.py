"""
Vehicle Dynamics Model (Bicycle Model).
Implements 2D vehicle physics for the simulation environment.
"""

import math
from dataclasses import dataclass

@dataclass
class VehicleParams:
    """Physical parameters of the vehicle."""
    mass_kg: float = 1500.0  # GT3 car approx
    iz_kgm2: float = 2500.0  # Yaw inertia
    lf_m: float = 1.25       # CG to front axle
    lr_m: float = 1.45       # CG to rear axle
    cf_n_rad: float = 160000.0 # Front cornering stiffness
    cr_n_rad: float = 180000.0 # Rear cornering stiffness
    drag_coeff: float = 0.35
    frontal_area_m2: float = 2.2
    max_engine_force_n: float = 8000.0 # ~500 hp equiv at speed
    max_brake_force_n: float = 15000.0
    tire_grip_coeff: float = 1.0

class VehicleDynamics:
    """
    Dynamic bicycle model with linear tire physics (for stability)
    and longitudinal load transfer approximations.
    """
    
    def __init__(self, params: VehicleParams = VehicleParams()):
        self.params = params
        self.rho_air = 1.225
        
    def update(
        self,
        dt: float,
        current_speed: float,
        current_vx: float,
        current_vy: float,
        current_heading: float,
        current_yaw_rate: float,
        steering_norm: float,
        throttle_norm: float,
        brake_norm: float
    ) -> tuple:
        """
        Calculate next state.
        
        Returns:
            (new_speed, new_vx, new_vy, new_heading, new_yaw_rate)
        """
        p = self.params
        
        # Inputs
        delta = steering_norm * 0.5 # Max steering angle ~ 30 deg (~0.5 rad)
        
        # Longitudinal Forces
        f_aero = 0.5 * self.rho_air * p.drag_coeff * p.frontal_area_m2 * (current_speed ** 2)
        f_roll = 200.0 # approx rolling resistance
        
        f_drive = throttle_norm * p.max_engine_force_n
        if current_speed > 0:
            # Power limited at high speed (P = F*v)
            # Approx 370 kW (500hp)
            max_force_power = 370000.0 / max(1.0, current_speed)
            f_drive = min(f_drive, max_force_power)
            
        f_brake = brake_norm * p.max_brake_force_n
        
        fx = f_drive - f_brake - f_aero - f_roll
        
        # Prevent reversing for this simple model
        if current_speed < 0.1 and fx < 0:
            fx = 0
            
        ax = fx / p.mass_kg
        
        # Lateral Dynamics (Bicycle Model)
        # Avoid singular denominator at low speed
        v_blend = max(1.0, current_speed)
        
        # Slip angles
        alpha_f = delta - math.atan2(current_vy + p.lf_m * current_yaw_rate, current_vx)
        alpha_r = -math.atan2(current_vy - p.lr_m * current_yaw_rate, current_vx)
        
        # Tire forces (Linear simplified cap)
        fy_f = p.cf_n_rad * alpha_f
        fy_r = p.cr_n_rad * alpha_r
        
        # Saturation (Grip circle approx)
        max_fy = p.mass_kg * 9.81 * p.tire_grip_coeff * 0.5 # approx load per axle
        fy_f = max(-max_fy, min(max_fy, fy_f))
        fy_r = max(-max_fy, min(max_fy, fy_r))
        
        # Equations of motion
        # Local acceleration
        # m(vx_dot - vy*r) = fx
        # m(vy_dot + vx*r) = fy_f + fy_r
        # Iz * r_dot = lf*fy_f - lr*fy_r
        
        # In vehicle frame
        # We handle longitudinal separately as 'speed' for v1 stability
        # But let's try to be consistent:
        # vx is roughly speed
        
        ay = (fy_f + fy_r) / p.mass_kg
        r_dot = (p.lf_m * fy_f - p.lr_m * fy_r) / p.iz_kgm2
        
        # Integration
        new_yaw_rate = current_yaw_rate + r_dot * dt
        new_heading = current_heading + current_yaw_rate * dt
        
        # Update speed/velocity
        # This is a bit hybrid. For robust training, we often calculate
        # speed directly from ax, and side-slip separately.
        
        current_vx += (ax + current_yaw_rate * current_vy) * dt
        current_vy += (ay - current_yaw_rate * current_vx) * dt
        
        # Damping for stability at zero speed
        if current_speed < 0.5:
            current_vy *= 0.9
            new_yaw_rate *= 0.9
            
        new_speed = math.sqrt(current_vx**2 + current_vy**2)
        
        # Re-align vx to be positive
        if new_speed < 0.1:
            current_vx = 0
            current_vy = 0
            new_speed = 0
        
        return new_speed, current_vx, current_vy, new_heading, new_yaw_rate
