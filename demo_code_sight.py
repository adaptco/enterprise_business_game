
import time
import sys
import os

# Add current directory to path so we can import code_sight
sys.path.append(os.getcwd())

from code_sight.core import get_code_sight, sight_point, ActionType

def run_verification():
    print(">> Starting Code Sight Core Verification")
    print("=" * 40)
    
    engine = get_code_sight()
    
    # 1. Test Metric Injection
    print("\n[1] Testing Metric Injection...")
    engine.inject_metric(
        target="verify_core",
        metric_name="test_metric",
        alert_threshold=10.0
    )
    
    sight_pt = engine.sight_points.get("metric_verify_core_test_metric")
    if sight_pt:
        print("[OK] Metric sight point registered")
    else:
        print("[FAIL] Failed to register metric sight point")
        return False
        
    # 2. Test Decorator Instrumentation
    print("\n[2] Testing Decorator Instrumentation...")
    
    @sight_point(name="test_function", modality="verification", metrics=["latency_ms"])
    def my_test_func(x):
        time.sleep(0.01)
        return x * 2
        
    result = my_test_func(21)
    if result == 42:
        print("[OK] Decorated function execution successful")
    else:
        print(f"[FAIL] Decorated function execution failed: {result}")
        return False
        
    # 3. Verify Observation Ledger
    print("\n[3] Verifying Observation Ledger...")
    observations = engine.ledger.get_observations(sight_point="test_function")
    
    if len(observations) > 0:
        print(f"[OK] Found {len(observations)} observations")
        obs = observations[0]
        print(f"   - Latency: {obs.metrics.get('latency_ms', 0):.2f}ms")
        print(f"   - Modality: {obs.modality}")
    else:
        print("[FAIL] No observations found for test function")
        return False
        
    # 4. Verify Merkle Chain
    print("\n[4] Verifying Merkle Chain Integrity...")
    if engine.ledger.verify_chain():
        print("[OK] Merkle chain is valid")
    else:
        print("[FAIL] Merkle chain verification failed")
        return False
        
    print("\n" + "=" * 40)
    print("VERIFICATION COMPLETE: ALL SYSTEMS GO")
    return True

if __name__ == "__main__":
    success = run_verification()
    sys.exit(0 if success else 1)
