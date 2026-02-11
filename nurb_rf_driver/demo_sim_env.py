"""
Demonstration of Sim Env Contract v1.
Shows deterministic tick loop, feature extraction, and NDJSON logging.
"""

import sys
import os

# Ensure nurb_rf_driver package is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from nurb_rf_driver.env.sim_env import SimEnv
from nurb_rf_driver.state.feature_extractor import FeatureExtractor
from nurb_rf_driver.telemetry.ndjson_logger import NDJSONLogger, load_ndjson, verify_ndjson_determinism


def demo_deterministic_sim():
    """Demonstrate deterministic simulation with hash chain verification."""
    print("\n" + "="*60)
    print("  Sim Env Contract v1 - Deterministic Tick Loop Demo")
    print("="*60 + "\n")
    
    # Initialize simulation
    env = SimEnv(seed=42, run_id="demo_001", root_identity="Han")
    extractor = FeatureExtractor()
    
    print(f"✅ Initialized SimEnv")
    print(f"   - Seed: {env.seed}")
    print(f"   - Run ID: {env.run_id}")
    print(f"   - Root Identity: {env.root_identity}")
    print(f"   - Tick rate: {1/env.dt:.0f} Hz\n")
    
    # Reset to initial state
    state = env.reset()
    print(f"✅ Reset to initial state")
    print(f"   - Position: ({state.track_x_m:.2f}, {state.track_y_m:.2f}, {state.track_z_m:.2f})")
    print(f"   - Speed: {state.speed_mps:.2f} m/s\n")
    
    # Run 10 ticks with simple control
    print("🏁 Running 10 ticks with accelerating control...\n")
    
    for tick in range(10):
        # Simple control: accelerate and slight left steering
        steering = -0.1
        throttle = 0.5
        brake = 0.0
        
        # Step simulation
        state, metadata = env.step(steering, throttle, brake)
        
        # Extract features
        features = extractor.extract_features(state)
        
        # Print tick summary
        print(f"Tick {metadata['tick']:3d}:")
        print(f"  Speed: {state.speed_mps:6.2f} m/s | Position: ({state.track_x_m:8.2f}, {state.track_y_m:8.2f})")
        print(f"  Coord: {metadata['coord_int']} | Seed: {metadata['seed_u64'] & 0xFFFF:04x}")
        print(f"  Hash: {metadata['state_hash'][:16]}... | Chain: {metadata['chain_hash'][:16]}...")
    
    print(f"\n✅ Completed 10 ticks")
    print(f"   - Final speed: {state.speed_mps:.2f} m/s")
    print(f"   - Track progress: {state.track_progress*100:.2f}%")


def demo_ndjson_logging():
    """Demonstrate NDJSON logging with canonical ordering."""
    print("\n" + "="*60)
    print("  NDJSON Logging Demo - Stable Training Samples")
    print("="*60 + "\n")
    
    # Initialize
    env = SimEnv(seed=42, run_id="log_demo_001", root_identity="Han")
    extractor = FeatureExtractor()
    
    # Create output directory
    output_dir = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(output_dir, exist_ok=True)
    
    output_path = os.path.join(output_dir, "demo_run.ndjson")
    
    print(f"📝 Logging to: {output_path}\n")
    
    # Run simulation and log
    env.reset()
    
    with NDJSONLogger(output_path, lap_id="lap_001") as logger:
        for tick in range(20):
            # Simple expert control
            steering = -0.05
            throttle = 0.8
            brake = 0.0
            
            # Step
            state, metadata = env.step(steering, throttle, brake)
            
            # Log sample
            logger.log_from_sim_state(
                tick=metadata['tick'],
                timestamp_ms=metadata['timestamp_ms'],
                vehicle_state=state,
                metadata=metadata,
                feature_extractor=extractor,
                valid=True
            )
    
    print(f"\n✅ Logged 20 samples")
    
    # Load and verify
    from telemetry import load_ndjson
    samples = load_ndjson(output_path)
    
    print(f"✅ Loaded {len(samples)} samples")
    print(f"\nSample 0 keys: {list(samples[0].keys())}")
    print(f"Feature keys: {list(samples[0]['features'].keys())}")
    print(f"Target keys: {list(samples[0]['targets'].keys())}")


def demo_determinism_verification():
    """Verify determinism by running simulation twice."""
    print("\n" + "="*60)
    print("  Determinism Verification - Replay Test")
    print("="*60 + "\n")
    
    # Run 1
    env1 = SimEnv(seed=12345, run_id="replay_test", root_identity="Han")
    env1.reset()
    
    hashes1 = []
    for tick in range(50):
        _, metadata = env1.step(0.1, 0.5, 0.0)
        hashes1.append(metadata['chain_hash'])
    
    print(f"✅ Run 1 complete: {len(hashes1)} ticks")
    print(f"   Final chain hash: {hashes1[-1][:16]}...")
    
    # Run 2 (same seed)
    env2 = SimEnv(seed=12345, run_id="replay_test", root_identity="Han")
    env2.reset()
    
    hashes2 = []
    for tick in range(50):
        _, metadata = env2.step(0.1, 0.5, 0.0)
        hashes2.append(metadata['chain_hash'])
    
    print(f"✅ Run 2 complete: {len(hashes2)} ticks")
    print(f"   Final chain hash: {hashes2[-1][:16]}...")
    
    # Verify
    if hashes1 == hashes2:
        print(f"\n✅ DETERMINISM VERIFIED: Hash chains are identical!")
        print(f"   All {len(hashes1)} chain hashes match.")
    else:
        print(f"\n❌ DETERMINISM FAILED: Hash chains differ!")
        for i, (h1, h2) in enumerate(zip(hashes1, hashes2)):
            if h1 != h2:
                print(f"   First mismatch at tick {i}")
                print(f"   Run 1: {h1}")
                print(f"   Run 2: {h2}")
                break


def main():
    """Run all demonstrations."""
    demo_deterministic_sim()
    demo_ndjson_logging()
    demo_determinism_verification()
    
    print("\n" + "="*60)
    print("  ✅ All Demos Complete!")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
