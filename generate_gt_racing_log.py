"""
GT Racing Simulation Log Generator
Creates a visualization-ready sim_log.jsonl from race data.
"""

import json
import math
from datetime import datetime, timezone


def generate_gt_racing_sim_log():
    """
    Generate a 5-second GT Racing simulation at 60Hz (300 frames).
    2 vehicles on circular track.
    """
    
    TOTAL_FRAMES = 300
    FPS = 60
    DT = 1.0 / FPS
    TRACK_RADIUS = 50.0  # meters
    
    # Vehicle parameters
    vehicles = {
        "car_1": {
            "velocity": 25.9,  # m/s (final velocity from user data)
            "start_angle": 0.0,
            "color": "#00ff9d"
        },
        "car_2": {
            "velocity": 22.6,  # m/s (final velocity from user data)
            "start_angle": -0.1,  # slightly behind
            "color": "#00d4ff"
        }
    }
    
    log_entries = []
    
    for frame in range(TOTAL_FRAMES):
        t = frame * DT
        
        state_snapshot = {
            "event_type": "STATE_SNAPSHOT",
            "tick": frame,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "runtime": "python_v1",
            "vehicles": []
        }
        
        for vehicle_id, params in vehicles.items():
            # Circular motion
            angular_velocity = params["velocity"] / TRACK_RADIUS
            angle = params["start_angle"] + angular_velocity * t
            
            x = TRACK_RADIUS * math.cos(angle)
            y = TRACK_RADIUS * math.sin(angle)
            
            # Distance along track
            distance_traveled = params["velocity"] * t
            lap = int(distance_traveled / (2 * math.pi * TRACK_RADIUS))
            distance_along_track = distance_traveled % (2 * math.pi * TRACK_RADIUS)
            
            vehicle_state = {
                "id": vehicle_id,
                "x": round(x, 2),
                "y": round(y, 2),
                "heading": round(angle + math.pi/2, 4),  # perpendicular to radius
                "velocity": round(params["velocity"], 2),
                "lap": lap,
                "distance_along_track": round(distance_along_track, 2)
            }
            
            state_snapshot["vehicles"].append(vehicle_state)
        
        # Add hash for Merkle chain (simulate)
        if frame == 0:
            state_snapshot["prev_hash"] = None
            state_snapshot["hash"] = "genesis_" + format(hash(json.dumps(state_snapshot["vehicles"], sort_keys=True)) & 0xffffffff, '08x')
        else:
            prev_hash = log_entries[-1]["hash"]
            state_snapshot["prev_hash"] = prev_hash
            combined = prev_hash + json.dumps(state_snapshot["vehicles"], sort_keys=True)
            state_snapshot["hash"] = format(hash(combined) & 0xffffffff, '08x')
        
        log_entries.append(state_snapshot)
    
    return log_entries


def print_summary(log_entries):
    """Print summary statistics"""
    print("="*60)
    print("  GT Racing Simulation Log Generated")
    print("="*60)
    print(f"\nTotal Entries: {len(log_entries)}")
    print(f"Event Types: {log_entries[0]['event_type']}")
    print(f"Runtime: {log_entries[0]['runtime']}")
    print(f"Duration: {len(log_entries) / 60:.1f} seconds @ 60Hz")
    
    final_state = log_entries[-1]["vehicles"]
    print(f"Vehicles: {len(final_state)} ({', '.join(v['id'] for v in final_state)})")
    
    print("\nFinal State:")
    for vehicle in final_state:
        print(f"  - {vehicle['id']}: lap={vehicle['lap']}, "
              f"{vehicle['distance_along_track']:.1f}m, "
              f"{vehicle['velocity']:.1f}m/s")
    
    print(f"\nGenesis hash: {log_entries[0]['hash']}")
    print(f"Head hash: {log_entries[-1]['hash']}")
    print(f"Chain: {log_entries[0]['hash'][:8]}... → {log_entries[-1]['hash'][:8]}")
    

if __name__ == "__main__":
    print("Generating GT Racing simulation log...\n")
    
    log_entries = generate_gt_racing_sim_log()
    
    # Save to file
    output_file = "sim_log.jsonl"
    with open(output_file, 'w') as f:
        for entry in log_entries:
            f.write(json.dumps(entry) + '\n')
    
    print_summary(log_entries)
    
    print(f"\n✅ Saved to: {output_file}")
    print(f"   Size: {len(log_entries)} frames")
    print(f"\n📊 Load in replayviewer.html to visualize the race!")
    print("="*60)
