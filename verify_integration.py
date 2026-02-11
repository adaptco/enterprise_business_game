
import sys
import os
import time

print("DEBUG: Script started", flush=True)

# Verify we can find siblings
current_dir = os.getcwd()
scratch_dir = os.path.dirname(current_dir)
sim_dir = os.path.join(scratch_dir, "nurburgring_ai_simulator")

print(f"Adding to path: {sim_dir}")
sys.path.append(sim_dir)

# Import Code Sight
from code_sight.core import get_code_sight

# Import VehiclePhysics (which should now have Code Sight instrumented)
try:
    from vehicle_physics import VehiclePhysics
    from vehicle_state import VehicleState, ControlAction
    print("[OK] Imported VehiclePhysics")
except ImportError as e:
    print(f"[FAIL] Could not import VehiclePhysics: {e}")
    sys.exit(1)

# Mock Track
class MockTrack:
    def find_closest_distance(self, x, y): return 0.0
    def _compute_waypoint_distances(self): return [0, 1000]
    def get_position_at_distance(self, d): return (0, 0, 0)
    def get_curvature_at_distance(self, d): return 0.0
    def get_gradient_at_distance(self, d): return 0.0
    def get_upcoming_curvature_horizon(self, d): return [0, 0, 0, 0, 0]
    def get_track_boundaries(self, d): return ((-5, 0), (5, 0))

def verify_integration():
    print("\n>> Verifying System Integration")
    print("=" * 40)
    
    engine = get_code_sight()
    start_obs_count = len(engine.ledger.observations)
    
    # Instantiate Physics
    physics = VehiclePhysics(MockTrack())
    state = VehicleState()
    action = ControlAction(0, 0.5, 0)
    
    # Run step
    print("Running physics step...")
    physics.step(state, action, 0.1)
    
    # Check Code Sight
    end_obs_count = len(engine.ledger.observations)
    
    if end_obs_count > start_obs_count:
        print(f"[OK] Observations increased by {end_obs_count - start_obs_count}")
        last_obs = engine.ledger.observations[-1]
        print(f"   - Sight Point: {last_obs.sight_point_name}")
        print(f"   - Metrics: {last_obs.metrics}")
        
        if last_obs.sight_point_name == "vehicle_physics_step":
            print("[PASS] Correct sight point triggered")
        else:
            print(f"[FAIL] Unexpected sight point: {last_obs.sight_point_name}")
            return False
    else:
        print("[FAIL] No new observations recorded")
        return False
        
    print("=" * 40)
    return True

if __name__ == "__main__":
    if verify_integration():
        print("Integration Verification SUCCESS")
        sys.exit(0)
    else:
        print("Integration Verification FAILED")
        sys.exit(1)
