"""
Evaluate RF Agent.
Runs the trained RF agent on the simulation environment and evaluates performance.
"""

import sys
import os
import time

# Ensure package path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from nurb_rf_driver.env.sim_env import SimEnv
from nurb_rf_driver.control.rf_pilot import RFPilot
from nurb_rf_driver.telemetry.ndjson_logger import NDJSONLogger

OUTPUT_LOG = os.path.join(os.path.dirname(__file__), "data", "rf_run_001.ndjson")
NUM_LAPS = 1
TICKS_PER_LAP_APPROX = 15000

def evaluate_rf_agent():
    print(f"🤖 Starting RF Agent Evaluation...")
    
    # Init Env
    env = SimEnv(seed=1337, run_id="rf_agent_001", root_identity="RF_Driver")
    state_obj, meta = env.reset()
    
    # Init Pilot
    try:
        pilot = RFPilot(env.track)
    except Exception as e:
        print(f"❌ Failed to load RFPilot: {e}")
        return
    
    # Init Logger
    logger = NDJSONLogger(OUTPUT_LOG, lap_id="rf_run_001")
    logger.open()
    
    # Metrics
    max_lat_error = 0.0
    total_ticks = 0
    start_time = time.time()
    
    try:
        while total_ticks <= TICKS_PER_LAP_APPROX:
            # Control via RF
            steering, throttle, brake = pilot.compute_control(
                current_speed_mps=state_obj.speed_mps,
                current_heading_rad=state_obj.heading_rad,
                track_x_m=state_obj.track_x_m,
                track_y_m=state_obj.track_y_m,
                current_dist_m=env.current_dist_m,
                vehicle_state_obj=state_obj
            )
            
            # Step Env
            next_state_obj, next_meta = env.step(steering, throttle, brake)
            
            # Track Performance
            lat_error = abs(next_state_obj.dist_to_centerline_m)
            max_lat_error = max(max_lat_error, lat_error)
            
            # Helper for logging (if we want to log RF runs)
            # We skip full logging for speed unless requested
            # But let's log to verify behavior
            # Feature extraction is done inside RF pilot, but we can't easily get it out without modifying pilot.
            # We'll skip detailed feature log for this eval script, just log validation sample?
            # Or use FeatureExtractor here too if we want log.
            
            state_obj = next_state_obj
            meta = next_meta
            total_ticks += 1
            
            if total_ticks % 1000 == 0:
                 print(f"   Tick {total_ticks}: {state_obj.speed_mps:.1f} m/s | LatErr: {lat_error:.2f}m")
                 
            # Crash Detection (track width ~10m => +/- 5m allowed? Sim uses 10m width?)
            # TrackModel says `width=10.0`. So +/- 5.0m from center.
            if lat_error > 5.0:
                print(f"❌ CRASH! Vehicle left track at tick {total_ticks} (Dist: {env.current_dist_m:.1f}m)")
                break
                
            if total_ticks >= 15000:
                print("✅ Completed target distance.")
                break
                
    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        logger.close()
        
    duration = time.time() - start_time
    print(f"🏁 Finished. {total_ticks} ticks in {duration:.1f}s.")
    print(f"   Max Lateral Error: {max_lat_error:.3f} m")
    
    if max_lat_error < 5.0:
        print("✅ PASSED: Agent stayed on track.")
    else:
        print("❌ FAILED: Agent crashed.")

if __name__ == "__main__":
    evaluate_rf_agent()
