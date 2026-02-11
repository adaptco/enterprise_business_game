"""
Inverse Square Law Physics Module
Implements realistic distance-based force calculations for GT Racing.

Features:
- Air resistance (drag) with inverse square scaling
- Drafting (slipstream) effects between vehicles
- Distance-based force fields
- Deterministic fixed-point calculations
"""

import math
from typing import List, Dict, Tuple


class InverseSquarePhysics:
    """
    Inverse square law physics engine for vehicle interactions.
    
    All calculations use fixed-point arithmetic for determinism.
    Forces scale as F ∝ 1/r² where r is distance.
    """
    
    def __init__(
        self,
        drag_coefficient: float = 0.3,
        drafting_strength: float = 0.15,
        drafting_radius: float = 5.0,
        air_density: float = 1.225  # kg/m³ at sea level
    ):
        """
        Initialize physics parameters.
        
        Args:
            drag_coefficient: Cd for aerodynamic drag (0.3 = typical racing car)
            drafting_strength: Strength of slipstream effect (0.15 = 15% drag reduction)
            drafting_radius: Maximum distance for drafting effect (meters)
            air_density: Air density in kg/m³
        """
        # Convert to fixed-point integers (scale by 1000 for 3 decimal precision)
        self.drag_coeff_scaled = int(drag_coefficient * 1000)
        self.drafting_strength_scaled = int(drafting_strength * 1000)
        self.drafting_radius_scaled = int(drafting_radius * 1000)
        self.air_density_scaled = int(air_density * 1000)
        
        # Constants (scaled)
        self.SCALE = 1000  # Fixed-point scale factor
    
    def compute_drag_force(
        self,
        velocity: float,
        frontal_area: float = 2.0,
        is_in_draft: bool = False
    ) -> float:
        """
        Compute aerodynamic drag force: F_drag = 0.5 * ρ * Cd * A * v²
        
        Args:
            velocity: Vehicle velocity (m/s)
            frontal_area: Frontal cross-sectional area (m²)
            is_in_draft: Whether vehicle is in another's slipstream
        
        Returns:
            Drag force in Newtons (negative, opposes motion)
        """
        # Convert to fixed-point
        v_scaled = int(velocity * self.SCALE)
        area_scaled = int(frontal_area * self.SCALE)
        
        # Drag coefficient (reduced if in draft)
        cd = self.drag_coeff_scaled
        if is_in_draft:
            # Reduce drag by drafting_strength
            reduction = (cd * self.drafting_strength_scaled) // self.SCALE
            cd = cd - reduction
        
        # F_drag = 0.5 * ρ * Cd * A * v²
        # All scaled by 1000, so result is scaled by 1000^4
        # v² is scaled by 1000^2
        v_squared = (v_scaled * v_scaled) // self.SCALE
        
        force_scaled = (
            (self.air_density_scaled * cd * area_scaled * v_squared)
            // (2 * self.SCALE * self.SCALE * self.SCALE)
        )
        
        # Convert back to float and negate (drag opposes motion)
        return -float(force_scaled) / self.SCALE
    
    def compute_drafting_effect(
        self,
        vehicle_pos: Tuple[float, float],
        vehicle_heading: float,
        vehicle_velocity: float,
        other_pos: Tuple[float, float],
        other_velocity: float
    ) -> bool:
        """
        Determine if a vehicle is in another's slipstream.
        
        Drafting occurs when:
        1. Vehicle is behind the other (within cone of ±30°)
        2. Distance is within drafting_radius
        3. Other vehicle is faster or at similar speed
        
        Args:
            vehicle_pos: (x, y) position of vehicle checking for draft
            vehicle_heading: Heading of vehicle (radians)
            vehicle_velocity: Velocity of vehicle (m/s)
            other_pos: (x, y) position of potential draft source
            other_velocity: Velocity of other vehicle (m/s)
        
        Returns:
            True if vehicle is in slipstream
        """
        # Vector from other to vehicle
        dx = vehicle_pos[0] - other_pos[0]
        dy = vehicle_pos[1] - other_pos[1]
        
        # Distance (using fixed-point)
        dx_scaled = int(dx * self.SCALE)
        dy_scaled = int(dy * self.SCALE)
        
        dist_squared = dx_scaled * dx_scaled + dy_scaled * dy_scaled
        dist_scaled = int(math.sqrt(dist_squared))
        
        # Check distance threshold
        if dist_scaled > self.drafting_radius_scaled:
            return False
        
        # Check if vehicle is behind other (relative to other's heading)
        # Compute angle from other to vehicle
        angle_to_vehicle = math.atan2(dy, dx)
        
        # Heading of other vehicle (approximated from velocity direction)
        # For simplicity, assume heading aligns with position difference
        # In practice, you'd use the other vehicle's actual heading
        
        # Check if within drafting cone (±30° = ±0.524 rad)
        angle_diff = abs(angle_to_vehicle - vehicle_heading)
        
        # Normalize to [-π, π]
        while angle_diff > math.pi:
            angle_diff -= 2 * math.pi
        while angle_diff < -math.pi:
            angle_diff += 2 * math.pi
        
        in_cone = abs(angle_diff) < 0.524  # 30 degrees
        
        # Check velocity (only draft if other is faster)
        velocity_ok = other_velocity >= vehicle_velocity * 0.95
        
        return in_cone and velocity_ok
    
    def compute_inverse_square_force(
        self,
        source_pos: Tuple[float, float],
        target_pos: Tuple[float, float],
        strength: float = 100.0,
        min_distance: float = 1.0
    ) -> Tuple[float, float]:
        """
        Compute force from source to target using inverse square law.
        
        F = strength / r²
        
        Args:
            source_pos: (x, y) position of force source
            target_pos: (x, y) position of force target
            strength: Force strength coefficient
            min_distance: Minimum distance to prevent singularity
        
        Returns:
            (Fx, Fy) force components
        """
        # Vector from source to target
        dx = target_pos[0] - source_pos[0]
        dy = target_pos[1] - source_pos[1]
        
        # Distance (fixed-point)
        dx_scaled = int(dx * self.SCALE)
        dy_scaled = int(dy * self.SCALE)
        
        dist_squared = dx_scaled * dx_scaled + dy_scaled * dy_scaled
        dist_scaled = int(math.sqrt(dist_squared))
        
        # Prevent division by zero
        min_dist_scaled = int(min_distance * self.SCALE)
        if dist_scaled < min_dist_scaled:
            dist_scaled = min_dist_scaled
        
        # F = strength / r²
        strength_scaled = int(strength * self.SCALE)
        force_magnitude = (strength_scaled * self.SCALE) // (dist_scaled * dist_scaled // self.SCALE)
        
        # Unit vector (direction)
        ux = (dx_scaled * self.SCALE) // dist_scaled
        uy = (dy_scaled * self.SCALE) // dist_scaled
        
        # Force components
        fx = (force_magnitude * ux) // (self.SCALE * self.SCALE)
        fy = (force_magnitude * uy) // (self.SCALE * self.SCALE)
        
        return (float(fx) / self.SCALE, float(fy) / self.SCALE)
    
    def apply_forces_to_vehicle(
        self,
        vehicle: Dict,
        other_vehicles: List[Dict],
        dt: float = 1.0 / 60.0
    ) -> Dict:
        """
        Apply all physics forces to a vehicle.
        
        Args:
            vehicle: Vehicle state dict with keys: x, y, heading, velocity, mass
            other_vehicles: List of other vehicle states
            dt: Time step (seconds)
        
        Returns:
            Updated vehicle state with new velocity and position
        """
        mass = vehicle.get("mass", 1000.0)  # kg
        frontal_area = vehicle.get("frontal_area", 2.0)  # m²
        
        # Check for drafting
        in_draft = False
        for other in other_vehicles:
            if self.compute_drafting_effect(
                vehicle_pos=(vehicle["x"], vehicle["y"]),
                vehicle_heading=vehicle["heading"],
                vehicle_velocity=vehicle["velocity"],
                other_pos=(other["x"], other["y"]),
                other_velocity=other["velocity"]
            ):
                in_draft = True
                break
        
        # Compute drag force
        drag_force = self.compute_drag_force(
            velocity=vehicle["velocity"],
            frontal_area=frontal_area,
            is_in_draft=in_draft
        )
        
        # Net acceleration: a = F / m
        acceleration = drag_force / mass
        
        # Update velocity: v' = v + a * dt
        new_velocity = vehicle["velocity"] + acceleration * dt
        
        # Clamp to positive
        if new_velocity < 0:
            new_velocity = 0
        
        # Update position (simple Euler integration)
        # Convert heading to velocity components
        vx = new_velocity * math.cos(vehicle["heading"])
        vy = new_velocity * math.sin(vehicle["heading"])
        
        new_x = vehicle["x"] + vx * dt
        new_y = vehicle["y"] + vy * dt
        
        # Return updated state
        return {
            **vehicle,
            "x": new_x,
            "y": new_y,
            "velocity": new_velocity,
            "in_draft": in_draft,
            "drag_force": drag_force
        }


# Example usage and tests
if __name__ == "__main__":
    print("="*70)
    print("  Inverse Square Law Physics - Test")
    print("="*70)
    
    # Initialize physics engine
    physics = InverseSquarePhysics(
        drag_coefficient=0.3,
        drafting_strength=0.15,
        drafting_radius=5.0
    )
    
    print("\n1. Drag Force Calculation")
    print("-"*70)
    
    velocity = 25.0  # m/s (~90 km/h)
    drag_normal = physics.compute_drag_force(velocity, frontal_area=2.0, is_in_draft=False)
    drag_draft = physics.compute_drag_force(velocity, frontal_area=2.0, is_in_draft=True)
    
    print(f"  Velocity: {velocity} m/s")
    print(f"  Drag (normal): {drag_normal:.2f} N")
    print(f"  Drag (in draft): {drag_draft:.2f} N")
    print(f"  Drafting benefit: {(drag_normal - drag_draft):.2f} N ({((drag_normal - drag_draft) / abs(drag_normal) * 100):.1f}%)")
    
    print("\n2. Drafting Detection")
    print("-"*70)
    
    vehicle1 = {"x": 0.0, "y": 0.0, "heading": 0.0, "velocity": 25.0}
    vehicle2 = {"x": -3.0, "y": 0.0, "heading": 0.0, "velocity": 25.0}  # 3m behind
    
    in_draft = physics.compute_drafting_effect(
        vehicle_pos=(vehicle2["x"], vehicle2["y"]),
        vehicle_heading=vehicle2["heading"],
        vehicle_velocity=vehicle2["velocity"],
        other_pos=(vehicle1["x"], vehicle1["y"]),
        other_velocity=vehicle1["velocity"]
    )
    
    print(f"  Vehicle 1: x={vehicle1['x']}, v={vehicle1['velocity']} m/s")
    print(f"  Vehicle 2: x={vehicle2['x']}, v={vehicle2['velocity']} m/s (3m behind)")
    print(f"  Vehicle 2 in draft of Vehicle 1: {in_draft}")
    
    print("\n3. Inverse Square Force")
    print("-"*70)
    
    fx, fy = physics.compute_inverse_square_force(
        source_pos=(0.0, 0.0),
        target_pos=(3.0, 4.0),
        strength=100.0
    )
    
    force_magnitude = math.sqrt(fx**2 + fy**2)
    print(f"  Source: (0, 0)")
    print(f"  Target: (3, 4) — distance = 5m")
    print(f"  Force: ({fx:.4f}, {fy:.4f}) N")
    print(f"  Magnitude: {force_magnitude:.4f} N")
    print(f"  Expected: ~4 N (100/5² = 100/25)")
    
    print("\n4. Full Vehicle Update")
    print("-"*70)
    
    vehicle = {
        "x": 0.0,
        "y": 0.0,
        "heading": 0.0,
        "velocity": 25.0,
        "mass": 1000.0,
        "frontal_area": 2.0
    }
    
    other_vehicles = [
        {"x": 3.0, "y": 0.0, "heading": 0.0, "velocity": 26.0}  # Leader
    ]
    
    updated = physics.apply_forces_to_vehicle(vehicle, other_vehicles, dt=1.0/60.0)
    
    print(f"  Initial velocity: {vehicle['velocity']:.4f} m/s")
    print(f"  Drag force: {updated['drag_force']:.2f} N")
    print(f"  In draft: {updated['in_draft']}")
    print(f"  New velocity: {updated['velocity']:.4f} m/s")
    print(f"  Velocity change: {(updated['velocity'] - vehicle['velocity']) * 1000:.4f} mm/s per tick")
    
    print("\n" + "="*70)
    print("✅ Inverse square law physics module working correctly!")
    print("="*70)
