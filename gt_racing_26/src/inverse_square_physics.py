"""
Inverse Square Law Physics Module
Integrates with GT Racing for drafting, aerodynamic effects, and distance-based forces.

F = k / r²

Where:
- F: Force magnitude
- k: Coupling constant
- r: Distance between objects
"""

import numpy as np
from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class PhysicsBody:
    """Represents a body in the physics simulation"""
    id: str
    x: float  # meters
    y: float  # meters
    velocity: float  # m/s
    heading: float  # radians
    mass: float  # kg


class InverseSquareLaw:
    """
    Calculates inverse square law forces between physics bodies.
    Compatible with deterministic GT Racing physics engine.
    """
    
    def __init__(self, coupling_constant: float = 1.0, min_distance: float = 0.1):
        """
        Initialize inverse square law calculator.
        
        Args:
            coupling_constant: Strength multiplier (k in F = k/r²)
            min_distance: Minimum distance to prevent singularities
        """
        self.k = coupling_constant
        self.min_distance = min_distance
    
    def compute_force_magnitude(self, distance: float) -> float:
        """
        Compute force magnitude using inverse square law.
        
        F = k / r²
        
        Args:
            distance: Distance between objects (meters)
        
        Returns:
            Force magnitude
        """
        # Clamp distance to prevent division by zero
        r = max(distance, self.min_distance)
        return self.k / (r * r)
    
    def compute_distance(self, body1: PhysicsBody, body2: PhysicsBody) -> float:
        """Calculate Euclidean distance between two bodies"""
        dx = body2.x - body1.x
        dy = body2.y - body1.y
        return np.sqrt(dx * dx + dy * dy)
    
    def compute_force_vector(
        self,
        body1: PhysicsBody,
        body2: PhysicsBody
    ) -> Tuple[float, float]:
        """
        Compute force vector from body1 to body2.
        
        Returns:
            (fx, fy): Force components in x and y directions
        """
        dx = body2.x - body1.x
        dy = body2.y - body1.y
        distance = np.sqrt(dx * dx + dy * dy)
        
        # Compute force magnitude
        force_mag = self.compute_force_magnitude(distance)
        
        # Normalize direction and scale by force
        if distance > self.min_distance:
            fx = force_mag * (dx / distance)
            fy = force_mag * (dy / distance)
        else:
            fx, fy = 0.0, 0.0
        
        return fx, fy


class DraftingPhysics(InverseSquareLaw):
    """
    Specialized inverse square law for vehicle drafting effects.
    
    Drafting reduces air resistance when following another vehicle.
    Effect strength follows inverse square law with distance.
    """
    
    def __init__(
        self,
        max_draft_benefit: float = 0.3,  # 30% drag reduction at minimum distance
        effective_range: float = 10.0,   # meters
        cone_angle: float = 30.0          # degrees
    ):
        """
        Initialize drafting physics.
        
        Args:
            max_draft_benefit: Maximum drag reduction factor (0-1)
            effective_range: Distance at which drafting effect becomes negligible
            cone_angle: Cone angle behind vehicle where drafting applies
        """
        # Set coupling constant based on desired range
        # At effective_range, we want benefit ≈ 0.01 (1%)
        k = 0.01 * (effective_range ** 2)
        super().__init__(coupling_constant=k, min_distance=0.5)
        
        self.max_benefit = max_draft_benefit
        self.effective_range = effective_range
        self.cone_angle_rad = np.deg2rad(cone_angle)
    
    def is_in_draft_cone(
        self,
        follower: PhysicsBody,
        leader: PhysicsBody
    ) -> bool:
        """
        Check if follower is in the draft cone behind leader.
        
        Args:
            follower: Vehicle attempting to draft
            leader: Vehicle being drafted
        
        Returns:
            True if follower is in draft zone
        """
        # Vector from leader to follower
        dx = follower.x - leader.x
        dy = follower.y - leader.y
        
        # Leader's heading vector
        leader_dir_x = np.cos(leader.heading)
        leader_dir_y = np.sin(leader.heading)
        
        # Dot product to check if follower is behind
        dot = dx * leader_dir_x + dy * leader_dir_y
        
        if dot >= 0:  # Follower is ahead or beside, no drafting
            return False
        
        # Calculate angle between leader's direction and vector to follower
        follower_distance = np.sqrt(dx * dx + dy * dy)
        if follower_distance < self.min_distance:
            return False
        
        # Normalize
        dx_norm = dx / follower_distance
        dy_norm = dy / follower_distance
        
        # Angle between vectors
        cos_angle = abs(dx_norm * leader_dir_x + dy_norm * leader_dir_y)
        angle = np.arccos(np.clip(cos_angle, -1.0, 1.0))
        
        return angle <= self.cone_angle_rad
    
    def compute_draft_benefit(
        self,
        follower: PhysicsBody,
        leader: PhysicsBody
    ) -> float:
        """
        Compute drag reduction factor due to drafting.
        
        Returns:
            Drag reduction factor (0 = no benefit, 1 = full drag elimination)
        """
        if not self.is_in_draft_cone(follower, leader):
            return 0.0
        
        distance = self.compute_distance(follower, leader)
        
        if distance > self.effective_range:
            return 0.0
        
        # Inverse square falloff
        benefit_ratio = self.compute_force_magnitude(distance) / self.compute_force_magnitude(self.min_distance)
        
        # Scale to max benefit
        return min(benefit_ratio * self.max_benefit, self.max_benefit)
    
    def apply_draft_to_vehicle(
        self,
        vehicle: PhysicsBody,
        other_vehicles: List[PhysicsBody],
        base_drag_force: float
    ) -> float:
        """
        Calculate modified drag force accounting for drafting.
        
        Args:
            vehicle: Vehicle experiencing drag
            other_vehicles: Other vehicles that could provide draft
            base_drag_force: Original drag force without drafting
        
        Returns:
            Modified drag force after drafting effects
        """
        max_draft_benefit = 0.0
        
        # Find maximum draft benefit from any vehicle
        for other in other_vehicles:
            if other.id == vehicle.id:
                continue
            
            benefit = self.compute_draft_benefit(vehicle, other)
            max_draft_benefit = max(max_draft_benefit, benefit)
        
        # Apply best draft benefit
        return base_drag_force * (1.0 - max_draft_benefit)


def demo_inverse_square_law():
    """Demonstrate inverse square law physics"""
    print("\n" + "="*60)
    print("🔬 INVERSE SQUARE LAW PHYSICS DEMO")
    print("="*60)
    
    # Create test bodies
    leader = PhysicsBody(
        id="leader",
        x=0.0,
        y=0.0,
        velocity=30.0,  # m/s (~108 km/h)
        heading=0.0,  # East
        mass=1200.0
    )
    
    follower = PhysicsBody(
        id="follower",
        x=-5.0,  # 5m behind
        y=0.0,
        velocity=30.0,
        heading=0.0,
        mass=1200.0
    )
    
    # Test drafting physics
    drafting = DraftingPhysics(
        max_draft_benefit=0.3,
        effective_range=10.0,
        cone_angle=30.0
    )
    
    print("\n📊 Drafting Scenario:")
    print(f"  Leader:   ({leader.x:.1f}, {leader.y:.1f}) @ {leader.velocity:.1f} m/s")
    print(f"  Follower: ({follower.x:.1f}, {follower.y:.1f}) @ {follower.velocity:.1f} m/s")
    
    distance = drafting.compute_distance(follower, leader)
    print(f"\n  Distance: {distance:.2f} m")
    
    in_cone = drafting.is_in_draft_cone(follower, leader)
    print(f"  In draft cone: {in_cone}")
    
    benefit = drafting.compute_draft_benefit(follower, leader)
    print(f"  Draft benefit: {benefit*100:.1f}% drag reduction")
    
    # Apply to drag force
    base_drag = 400.0  # N
    modified_drag = drafting.apply_draft_to_vehicle(
        follower,
        [leader],
        base_drag
    )
    
    print(f"\n  Base drag:     {base_drag:.1f} N")
    print(f"  Modified drag: {modified_drag:.1f} N")
    print(f"  Force saved:   {base_drag - modified_drag:.1f} N")
    
    # Test at different distances
    print("\n📈 Drafting Effect vs Distance:")
    print("  " + "-"*40)
    for dist in [1.0, 2.0, 5.0, 8.0, 10.0, 15.0]:
        test_follower = PhysicsBody(
            id="test",
            x=-dist,
            y=0.0,
            velocity=30.0,
            heading=0.0,
            mass=1200.0
        )
        benefit = drafting.compute_draft_benefit(test_follower, leader)
        print(f"  {dist:5.1f}m: {benefit*100:5.1f}% reduction")
    
    print("\n" + "="*60)
    print("✅ Inverse square law physics ready for GT Racing integration")
    print("="*60)


if __name__ == "__main__":
    demo_inverse_square_law()
