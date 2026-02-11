"""
Simple test for GT Racing integration.
Tests Node bridge → GT Racing CLI communication.
"""

import sys
import os

# Fix path for imports
kernel_src = os.path.join(os.path.dirname(__file__), 'src')
sys.path.insert(0, kernel_src)

from node_bridge import NodeBridge


def test_gt_racing_bridge():
    """Test GT Racing CLI via Node bridge"""
    print("\n🏁 GT RACING INTEGRATION TEST")
    print("="*60)
    
    # Initialize bridge
    bridge = NodeBridge()
    
    # Check availability
    print("\n1. Checking Node.js availability...")
    if not bridge.check_availability():
        print("   ⚠️  Node.js or GT Racing CLI not available")
        print("   This is expected if Node.js isn't installed")
        return True
    
    print("   ✓ Node.js available")
    
    # Run simulation
    print("\n2. Running GT Racing simulation...")
    try:
        result = bridge.run_simulation(
            seed="TEST_GTA_42",
            ticks=50,
            remote_agents=False
        )
        print(f"   ✓ Simulation completed")
    except Exception as e:
        print(f"   ✗ Simulation failed: {e}")
        return False
    
    # Verify results
    print("\n3. Verifying results...")
    required_fields = ["ledger_valid", "ledger_head_hash", "ticks_simulated", "leaderboard"]
    
    for field in required_fields:
        if field not in result:
            print(f"   ✗ Missing field: {field}")
            return False
        print(f"   ✓ {field}: {result[field] if field != 'leaderboard' else f'{len(result[field])} entries'}")
    
    # Check hash determinism
    print("\n4. Testing determinism (same seed should produce same hash)...")
    result2 = bridge.run_simulation(
        seed="TEST_GTA_42",
        ticks=50,
        remote_agents=False
    )
    
    if result["ledger_head_hash"] == result2["ledger_head_hash"]:
        print(f"   ✓ Deterministic: {result['ledger_head_hash'][:24]}...")
    else:
        print(f"   ✗ Hashes don't match!")
        print(f"      Run 1: {result['ledger_head_hash']}")
        print(f"      Run 2: {result2['ledger_head_hash']}")
        return False
    
    print("\n" + "="*60)
    print("✅ GT RACING INTEGRATION TEST PASSED")
    print("="*60)
    return True


if __name__ == "__main__":
    success = test_gt_racing_bridge()
    sys.exit(0 if success else 1)
