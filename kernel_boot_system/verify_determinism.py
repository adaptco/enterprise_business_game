"""
Cross-Language Determinism Verification Script
Verifies that Python kernel + TypeScript GT Racing produce identical results.
"""

import sys
import os

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from runtime_block_generator import RuntimeBlockGenerator, ManifoldType
from gt_racing_agent import GTRacingAgent
from node_bridge import NodeBridge


def verify_cross_language_determinism(seed: str, ticks: int):
    """
    Verify that Python orchestrator + TypeScript GT Racing produce same hash.
    
    Args:
        seed: Deterministic seed
        ticks: Number of simulation ticks
    """
    print(f"\n🔐 CROSS-LANGUAGE DETERMINISM VERIFICATION")
    print("="*60)
    print(f"Seed: {seed}")
    print(f"Ticks: {ticks}\n")
    
    # === Path 1: Python Orchestrator → GT Racing Agent ===
    print("Path 1: Python Kernel → GT Racing Agent")
    print("-" * 60)
    
    # Generate runtime block with seed
    generator = RuntimeBlockGenerator(embedding_space="test.v1")
    runtime_block = generator.generate_from_local(
        config={
            "seed": seed,
            "simulation": {"ticks": ticks}
        },
        manifold_type=ManifoldType.EUCLIDEAN,
        metadata={"seed": seed}
    )
    
    print(f"✓ Runtime block created: {runtime_block['block_id'][:8]}...")
    
    # Execute via GT Racing Agent
    agent = GTRacingAgent(ipfs_client=None)  # No IPFS for test
    result = agent.process(tick=0, runtime_block=runtime_block)
    
    if result.get("status") == "FAILED":
        print(f"✗ GT Racing agent failed: {result.get('error')}")
        return False
    
    python_hash = result["output"]["replay_court_hash"]
    print(f"✓ Python path hash: {python_hash[:16]}...")
    
    # === Path 2: Direct TypeScript Execution ===
    print("\nPath 2: Direct TypeScript GT Racing CLI")
    print("-" * 60)
    
    # Execute GT Racing CLI directly
    bridge = NodeBridge()
    
    if not bridge.check_availability():
        print("⚠️  Node.js or GT Racing CLI not available")
        print("   Skipping direct TypeScript verification")
        return True  # Pass with warning
    
    try:
        ts_result = bridge.run_simulation(seed=seed, ticks=ticks)
        ts_hash = ts_result["ledger_head_hash"]
        print(f"✓ TypeScript path hash: {ts_hash[:16]}...")
    except Exception as e:
        print(f"✗ TypeScript execution failed: {e}")
        return False
    
    # === Verification ===
    print("\n" + "="*60)
    print("VERIFICATION RESULT")
    print("="*60)
    
    if python_hash == ts_hash:
        print(f"✅ DETERMINISM VERIFIED")
        print(f"   Both paths produced identical hash: {python_hash[:24]}...")
        return True
    else:
        print(f"❌ HASH MISMATCH")
        print(f"   Python:     {python_hash}")
        print(f"   TypeScript: {ts_hash}")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Verify cross-language determinism")
    parser.add_argument("--seed", default="TEST_SEED_42", help="Deterministic seed")
    parser.add_argument("--ticks", type=int, default=100, help="Simulation ticks")
    
    args = parser.parse_args()
    
    success = verify_cross_language_determinism(args.seed, args.ticks)
    
    sys.exit(0 if success else 1)
