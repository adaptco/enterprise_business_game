"""
Code Sight Integration Example - PINN Racing Simulator

Demonstrates how to instrument the PhyAtteN_R32 PINN model with
Code Sight for multimodal stability monitoring and runtime debugging.
"""

import sys
import os

# Add parent directory to path to import code_sight
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

import time
import numpy as np
from code_sight.core import sight_point, get_code_sight, Modality


# Mock PINN Model Components
class PhyAtteN_R32:
    """Physics-Informed Neural Network for R32 Digital Twin"""
    
    def __init__(self):
        self.lambda_physics = 0.85  # Physics residual weight
        self.latency_threshold_ms = 1.2
        
    @sight_point(
        name="pinn_forward_pass",
        modality=Modality.SIMULATION.value,
        metrics=["latency_ms", "physics_residual"],
        conditions={"threshold": 1.2}
    )
    def forward(self, state: np.ndarray, action: np.ndarray) -> np.ndarray:
        """PINN forward pass with physics constraints"""
        
        # Simulate PINN computation
        time.sleep(0.0008 + np.random.rand() * 0.0004)  # ~0.8-1.2ms
        
        # Physics residual computation (Pacejka tire model)
        physics_residual = self._compute_physics_residual(state, action)
        
        # State prediction
        next_state = self._predict_next_state(state, action)
        
        return next_state
    
    def _compute_physics_residual(self, state: np.ndarray, action: np.ndarray) -> float:
        """Compute physics-based loss (Pacejka tire slip angles)"""
        return 0.012 + np.random.rand() * 0.008
    
    def _predict_next_state(self, state: np.ndarray, action: np.ndarray) -> np.ndarray:
        """Predict next vehicle state"""
        return state + action * 0.1


class AlignmentValidator:
    """Validates digital twin alignment using Hausdorff distance"""
    
    @sight_point(
        name="hausdorff_validation",
        modality=Modality.VISION_PROCESSING.value,
        metrics=["hausdorff_distance_nm"],
        conditions={"threshold": 0.045}
    )
    def validate_fitment(self, scan_data: np.ndarray) -> bool:
        """Validate Pocket Bunny scan against digital twin"""
        
        # Simulate 3D scan comparison
        time.sleep(0.002)  # 2ms processing
        
        # Hausdorff distance computation
        hausdorff_drift = 0.015 + np.random.rand() * 0.030  # 0.015-0.045nm
        
        if hausdorff_drift > 0.045:
            print(f"[FAIL-CLOSED] Hausdorff drift {hausdorff_drift:.4f}nm exceeds 0.045nm limit!")
            return False
        
        return True


class SovereignEventValidator:
    """Validates idempotency and byte-consistency of state"""
    
    @sight_point(
        name="idempotency_check",
        modality=Modality.INFERENCE.value,
        metrics=["byte_consistent", "fpga_cycles"]
    )
    def validate_state_signature(self, state_bytes: bytes) -> bool:
        """Check state signature for idempotency violations"""
        
        # Simulate FPGA cycle counting
        fpga_cycles = 120000 + int(np.random.rand() * 5000)
        
        # Simulate byte-level consistency check (1 in 1000 chance of corruption)
        byte_consistent = np.random.rand() > 0.001
        
        if not byte_consistent:
            print("[FAIL-CLOSED] Idempotency violation detected! Chaos Emerald state locked.")
            return False
        
        return True


def run_first_light_sequence():
    """
    Execute the First Light telemetry sequence with full Code Sight instrumentation.
    """
    
    print("""
    ============================================================
                FIRST LIGHT TELEMETRY SEQUENCE
              PhyAtteN_R32 PINN Calibration Console
    ============================================================
    
    Configuration:
    - State-Estimation Latency Target: < 1.2ms
    - Hausdorff Distance Limit: < 0.045nm
    - Physics Residual Weight (lambda): 0.85
    - Idempotency: Byte-level Sovereign Event Schema
    
    Initiating primary sweep...
    """)
    
    # Initialize components
    pinn = PhyAtteN_R32()
    validator = AlignmentValidator()
    idempotency = SovereignEventValidator()
    
    # Get Code Sight engine
    sight = get_code_sight()
    
    # Run simulation loop
    state =np.random.rand(8)  # 8-dimensional state vector
    
    for tick in range(100):
        # PINN inference
        action = np.random.rand(8) * 0.1  # 8D control input matching state dimension
        next_state = pinn.forward(state, action)
        
        # Alignment validation (every 10 ticks)
        if tick % 10 == 0:
            scan_data = np.random.rand(100, 3)  # Mock 3D scan
            alignment_ok = validator.validate_fitment(scan_data)
        
        # Idempotency check (every 5 ticks)
        if tick % 5 == 0:
            state_bytes = state.tobytes()
            idempotent = idempotency.validate_state_signature(state_bytes)
        
        state = next_state
        
        # Simulate 100Hz control loop
        time.sleep(0.01)
        
        if tick % 20 == 0:
            print(f"[Tick {tick:03d}] State: {state[:3]} | Observations: {len(sight.ledger.observations)}")
    
    print("\n[OK] First Light sequence complete!")
    print(f"\nObservability Summary:")
    print(f"  Total Observations: {len(sight.ledger.observations)}")
    print(f"  Merkle Chain Valid: {sight.ledger.verify_chain()}")
    print(f"  Active Sight Points: {len(sight.sight_points)}")
    
    # Print sample observations by modality
    print(f"\n[OBSERVATIONS BY MODALITY]")
    for modality in [Modality.SIMULATION, Modality.VISION_PROCESSING, Modality.INFERENCE]:
        obs = sight.ledger.get_observations(modality=modality.value, limit=1000)
        if obs:
            avg_latency = np.mean([o.metrics.get('latency_ms', 0) for o in obs])
            print(f"  {modality.value}: {len(obs)} observations (avg latency: {avg_latency:.3f}ms)")
    
    # Display recent observations
    print(f"\n[RECENT OBSERVATIONS]")
    recent = sight.ledger.get_observations(limit=5)
    for obs in recent:
        print(f"  [{obs.sight_point_name}] {obs.metrics}")


def run_multimodal_stress_test():
    """
    Stress test to validate Code Sight overhead stays under 0.1ms budget.
    """
    
    print("\n[STRESS TEST] Running Multimodal Stress Test...\n")
    
    @sight_point(
        name="stress_test_computation",
        modality=Modality.CODE_EXECUTION.value,
        metrics=["execution_time"]
    )
    def heavy_computation(n: int) -> float:
        """Simulated heavy computation"""
        result = 0.0
        for i in range(n):
            result += np.sin(i) * np.cos(i)
        return result
    
    # Measure overhead
    iterations = 1000
    
    # Baseline without instrumentation
    baseline_start = time.perf_counter()
    for _ in range(iterations):
        result = sum(np.sin(i) * np.cos(i) for i in range(100))
    baseline_time = (time.perf_counter() - baseline_start) / iterations
    
    # With Code Sight instrumentation
    instrumented_start = time.perf_counter()
    for _ in range(iterations):
        result = heavy_computation(100)
    instrumented_time = (time.perf_counter() - instrumented_start) / iterations
    
    overhead_ms = (instrumented_time - baseline_time) * 1000
    
    print(f"Baseline execution time: {baseline_time * 1000:.4f}ms")
    print(f"Instrumented execution time: {instrumented_time * 1000:.4f}ms")
    print(f"Code Sight overhead: {overhead_ms:.4f}ms")
    
    if overhead_ms < 0.1:
        print(f"[OK] PASS: Overhead within 0.1ms budget")
    else:
        print(f"✗ FAIL: Overhead exceeds 0.1ms budget")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Code Sight Integration Demo")
    parser.add_argument("--mode", choices=["first_light", "stress_test", "both"], 
                       default="first_light",
                       help="Execution mode")
    
    args = parser.parse_args()
    
    if args.mode in ["first_light", "both"]:
        run_first_light_sequence()
    
    if args.mode in ["stress_test", "both"]:
        run_multimodal_stress_test()
    
    print("\n[TIP] Start the WebSocket server to visualize observations:")
    print("   python code_sight/server.py")
