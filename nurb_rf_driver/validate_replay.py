"""
Validate Replay Determinism.
Loads a training log (NDJSON) and replays it in SimEnv to verify exact state reproduction.
"""

import sys
import os
import json
import math

# Ensure package path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from nurb_rf_driver.env.sim_env import SimEnv
from nurb_rf_driver.telemetry.ndjson_logger import load_ndjson
from nurb_rf_driver.state.feature_extractor import FeatureExtractor

INPUT_LOG = os.path.join(os.path.dirname(__file__), "data", "expert_run_001.ndjson")
SEED = 1337      # Must match generation
RUN_ID = "expert_001" 
IDENTITY = "Stig"

def validate_replay():
    print(f"🕵️ Validating Replay: {INPUT_LOG}")
    
    # Load samples
    print("   Loading NDJSON...")
    samples = load_ndjson(INPUT_LOG)
    print(f"   Loaded {len(samples)} samples.")
    
    if not samples:
        print("❌ No samples found.")
        return
        
    # Init Env
    env = SimEnv(seed=SEED, run_id=RUN_ID, root_identity=IDENTITY)
    state_obj, meta = env.reset()
    
    extractor = FeatureExtractor()
    
    mismatches = 0
    
    print("   Replaying...")
    
    # iterate samples
    # Sample i contains features(i) and targets(i) [action]
    # We check if env state matches features(i), then apply targets(i) to get to i+1
    
    for i, sample in enumerate(samples):
        # 1. Verify State (Features)
        # Extract features from current env state
        current_features_list = extractor.extract_features(state_obj)
        current_features = dict(zip(extractor.feature_order, current_features_list))
        
        logged_features = sample["features"]
        
        # Check specific key features (exact match expected if deterministic?)
        # Floating point might differ slightly if JSON truncation occurred.
        # NDJSONLogger typically uses standard json dump.
        # If we want exact hash check, we check metadata['state_hash'].
        
        logged_hash = sample["meta"]["state_hash"]
        current_hash = meta["state_hash"]
        
        if logged_hash != current_hash:
            print(f"❌ Hash Mismatch at tick {i}!")
            print(f"   Logged:  {logged_hash}")
            print(f"   Current: {current_hash}")
            mismatches += 1
            if mismatches > 5:
                break
        
        # 2. Apply Action
        targets = sample["targets"]
        steering = targets["steering_command"]
        throttle = targets["throttle_command"]
        brake = targets["brake_command"]
        
        next_state_obj, next_meta = env.step(steering, throttle, brake)
        
        state_obj = next_state_obj
        meta = next_meta
        
    if mismatches == 0:
        print("✅ REPLAY SUCCESS: All hashes matched!")
    else:
        print(f"❌ REPLAY FAILED: {mismatches} mismatches.")

if __name__ == "__main__":
    validate_replay()
