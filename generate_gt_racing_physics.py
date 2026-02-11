"""
GT Racing Simulation with Inverse Square Law Physics
Enhanced version with realistic drafting and aerodynamic effects.
"""

import json
import math
from datetime import datetime, timezone
from inverse_square_physics import InverseSquarePhysics


def generate_gt_racing_with_physics():
    """
    Generate a GT Racing simulation with inverse square law physics.
    300 frames at 60Hz with drafting effects.
    """
    
    TOTAL_FRAMES = 300
    FPS = 60
    DT = 1.0 / FPS
    TRACK_RADIUS = 50.0  # meters
    
    # Initialize physics engine
    physics = InverseSquarePhysics(
        drag_coefficient=0.3,
        drafting_strength=0.15,  # 15% drag reduction
        drafting_radius=5.0,     # 5m drafting zone
        air_density=1.225
    )
    
    # Vehicle parameters with physics properties
    vehicles = {
        "car_1": {
            "id": "car_1",
            "x": 50.0,
            "y": 0.0,
            "heading": math.pi / 2,  # perpendicular to radius
            "velocity": 26.0,  # m/s (slightly faster)
            "mass": 1000.0,  # kg
            "frontal_area": 2.0,  # m²
            "color": "#00ff9d",
            "lap": 0,
            "distance_along_track": 0.0
        },
        "car_2": {
            "id": "car_2",
            "x": 49.75,
            "y": -4.99,
            "heading": math.pi / 2 - 0.1,  # slightly behind
            "velocity": 25.5,  # m/s (slower, will try to draft)
            "mass": 1000.0,
            "frontal_area": 2.0,
            "color": "#00d4ff",
            "lap": 0,
            "distance_along_track": 0.0
        }
    }
    
    log_entries = []
    
    print("="*70)
    print("  GT Racing with Inverse Square Law Physics")
    print("="*70)
    print(f"\nSimulation: {TOTAL_FRAMES} frames @ {FPS}Hz")
    print(f"Physics: Drag + Drafting (15% reduction within 5m)")
    print()
    
    for frame in range(TOTAL_FRAMES):
        t = frame * DT
        
        # Convert dict to list for physics updates
        vehicle_list = list(vehicles.values())
        
        # Apply physics to each vehicle
        updated_vehicles = []
        for i, vehicle in enumerate(vehicle_list):
            # Other vehicles (for drafting detection)
            other_vehicles = [v for j, v in enumerate(vehicle_list) if i != j]
            
            # Apply forces
            updated = physics.apply_forces_to_vehicle(vehicle, other_vehicles, dt=DT)
            
            # Update circular motion (velocity affects angular velocity)
            angular_velocity = updated["velocity"] / TRACK_RADIUS
            updated["heading"] = updated["heading"] + angular_velocity * DT
            
            # Update position on circle
            updated["x"] = TRACK_RADIUS * math.cos(updated["heading"] - math.pi/2)
            updated["y"] = TRACK_RADIUS * math.sin(updated["heading"] - math.pi/2)
            
            # Distance and lap tracking
            updated["distance_along_track"] += updated["velocity"] * DT
            updated["lap"] = int(updated["distance_along_track"] / (2 * math.pi * TRACK_RADIUS))
            
            updated_vehicles.append(updated)
        
        # Update vehicles dict
        for updated in updated_vehicles:
            vehicles[updated["id"]] = updated
        
        # Create state snapshot
        state_snapshot = {
            "event_type": "STATE_SNAPSHOT",
            "tick": frame,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "runtime": "python_v1_physics",
            "vehicles": []
        }
        
        for vehicle in updated_vehicles:
            vehicle_state = {
                "id": vehicle["id"],
                "x": round(vehicle["x"], 2),
                "y": round(vehicle["y"], 2),
                "heading": round(vehicle["heading"], 4),
                "velocity": round(vehicle["velocity"], 2),
                "lap": vehicle["lap"],
                "distance_along_track": round(vehicle["distance_along_track"], 2),
                "in_draft": vehicle.get("in_draft", False),
                "drag_force": round(vehicle.get("drag_force", 0.0), 2)
            }
            state_snapshot["vehicles"].append(vehicle_state)
        
        # Add hash for Merkle chain
        if frame == 0:
            state_snapshot["prev_hash"] = None
            state_snapshot["hash"] = "genesis_physics_" + format(
                hash(json.dumps(state_snapshot["vehicles"], sort_keys=True)) & 0xffffffff, '08x'
            )
        else:
            prev_hash = log_entries[-1]["hash"]
            state_snapshot["prev_hash"] = prev_hash
            combined = prev_hash + json.dumps(state_snapshot["vehicles"], sort_keys=True)
            state_snapshot["hash"] = format(hash(combined) & 0xffffffff, '08x')
        
        log_entries.append(state_snapshot)
        
        # Progress reporting (every 60 frames = 1 second)
        if frame % 60 == 0:
            print(f"  t={t:.1f}s (tick {frame})")
            for vehicle in updated_vehicles:
                draft_marker = "🟢 DRAFT" if vehicle.get("in_draft", False) else ""
                print(f"    {vehicle['id']}: {vehicle['velocity']:.2f} m/s, "
                      f"{vehicle['distance_along_track']:.1f}m {draft_marker}")
    
    return log_entries


def print_summary(log_entries):
    """Print summary statistics with physics details"""
    print("\n" + "="*70)
    print("  Simulation Complete")
    print("="*70)
    
    print(f"\nTotal Entries: {len(log_entries)}")
    print(f"Runtime: python_v1_physics")
    print(f"Duration: {len(log_entries) / 60:.1f} seconds @ 60Hz")
    
    final_state = log_entries[-1]["vehicles"]
    print(f"\nFinal State:")
    
    # Sort by distance
    sorted_vehicles = sorted(final_state, key=lambda v: v["distance_along_track"], reverse=True)
    
    for i, vehicle in enumerate(sorted_vehicles, 1):
        position_emoji = ["🥇", "🥈", "🥉"][min(i-1, 2)]
        print(f"  {position_emoji} {vehicle['id']}: lap={vehicle['lap']}, "
              f"{vehicle['distance_along_track']:.1f}m, "
              f"{vehicle['velocity']:.2f}m/s")
    
    # Drafting statistics
    total_ticks_in_draft = {v["id"]: 0 for v in final_state}
    for entry in log_entries:
        for vehicle in entry["vehicles"]:
            if vehicle.get("in_draft", False):
                total_ticks_in_draft[vehicle["id"]] += 1
    
    print(f"\nDrafting Statistics:")
    for vehicle_id, ticks in total_ticks_in_draft.items():
        percentage = (ticks / len(log_entries)) * 100
        print(f"  {vehicle_id}: {ticks} ticks in draft ({percentage:.1f}% of race)")
    
    print(f"\nGenesis hash: {log_entries[0]['hash']}")
    print(f"Terminal hash: {log_entries[-1]['hash']}")


if __name__ == "__main__":
    # Generate simulation with physics
    log_entries = generate_gt_racing_with_physics()
    
    # Save to file
    output_file = "sim_log_physics.jsonl"
    with open(output_file, 'w') as f:
        for entry in log_entries:
            f.write(json.dumps(entry) + '\n')
    
    print_summary(log_entries)
    
    print(f"\n✅ Saved to: {output_file}")
    print(f"   Size: {len(log_entries)} frames")
    print(f"\n📊 Load in replay_viewer.html to visualize!")
    print("="*70)
