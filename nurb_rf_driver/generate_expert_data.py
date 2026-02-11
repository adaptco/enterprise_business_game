"""
Generate Expert Data.
Runs the simulation with the Expert Pilot and logs training samples.
"""

import os
import sys
import time

# Ensure package path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from nurb_rf_driver.env.sim_env import SimEnv
from nurb_rf_driver.control.expert_pilot import ExpertPilot
from nurb_rf_driver.telemetry.ndjson_logger import NDJSONLogger
from nurb_rf_driver.state.feature_extractor import FeatureExtractor

OUTPUT_LOG = os.path.join(os.path.dirname(__file__), "data", "expert_run_001.ndjson")
NUM_LAPS = 1 # V1: 1 lap to validation
TICKS_PER_LAP_APPROX = 15000 # ~5 mins at 50Hz = 15000 ticks (20km track / 66m/s avg)

def generate_expert_run():
    print(f"🏎️ Starting Expert Data Generation...")
    
    # Init Env
    env = SimEnv(seed=1337, run_id="expert_001", root_identity="Stig")
    state_obj, meta = env.reset()
    
    # Init Pilot
    pilot = ExpertPilot(env.track)
    
    # Init Extractor
    extractor = FeatureExtractor()
    
    # Init Logger
    logger = NDJSONLogger(OUTPUT_LOG, lap_id="expert_run_001")
    logger.open()
    
    # Loop
    total_ticks = 0
    lap_count = 0
    start_time = time.time()
    
    try:
        while lap_count < NUM_LAPS:
            # Control
            
            steering, throttle, brake = pilot.compute_control(
                current_speed_mps=state_obj.speed_mps,
                current_heading_rad=state_obj.heading_rad,
                track_x_m=state_obj.track_x_m,
                track_y_m=state_obj.track_y_m,
                current_dist_m=env.current_dist_m
            )
            
            # Step Env
            next_state_obj, next_meta = env.step(steering, throttle, brake)
            
            # Extract features for logging (Canonical V1)
            # Need features from PREVIOUS state (state_obj)
            feature_list = extractor.extract_features(state_obj)
            features = dict(zip(extractor.feature_order, feature_list))
            
            # Construct Training Sample
            sample = {
                "tick": env.tick - 1, # Action was taken at prev tick
                "timestamp_ms": (env.tick - 1) * 20,
                "lap_id": lap_count,
                "valid": True,
                "features": features, # Features from BEFORE action
                "targets": {
                    "steering_command": steering,
                    "throttle_command": throttle,
                    "brake_command": brake
                },
                "meta": meta # Metadata from prev state? 
                # Actually, standard RL: Obs(t), Action(t), Reward(t+1), NextObs(t+1)
                # Training sample maps Obs(t) -> Action(t).
                # Metadata should match Obs(t).
                # But 'step' returns metadata for t+1?
                # SimEnv.step returns metadata for the state it just transitioned TO.
                # So `meta` from reset() corresponds to `state_obj` (tick 0).
                # `next_meta` corresponds to `next_state_obj` (tick 1).
                # So we use `meta`.
            }
            
            # Log to file
            logger.log_sample(
                tick=sample["tick"],
                timestamp_ms=sample["timestamp_ms"],
                features=sample["features"],
                targets=sample["targets"],
                valid=sample["valid"],
                meta=sample["meta"]
            )
            
            state_obj = next_state_obj
            meta = next_meta
            total_ticks += 1
            
            if total_ticks % 1000 == 0:
                print(f"   Tick {total_ticks}: {state_obj.speed_mps:.1f} m/s | Prog: {state_obj.track_progress*100:.1f}%")
                
            if state_obj.track_progress > 0.99:
                 pass
            
            # Break if timeout/done
            if total_ticks > TICKS_PER_LAP_APPROX:
                break
                
    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        logger.close()
        
    duration = time.time() - start_time
    print(f"🏁 Finished. {total_ticks} ticks in {duration:.1f}s.")
    print(f"💾 Data saved to: {OUTPUT_LOG}")

if __name__ == "__main__":
    generate_expert_run()
