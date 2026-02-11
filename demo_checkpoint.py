"""
Demonstration of IPFS-backed checkpoint system.
Shows checkpoint creation, CID generation, and deterministic replay.
"""

import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from game_engine import GameEngine, IndustrySector, OperationType
try:
    from ipfs_bridge import IPFSBridge, IPFSConfig
    IPFS_AVAILABLE = True
except ImportError:
    print("⚠️  IPFS libraries not installed - demo will run without IPFS integration")
    print("   Run: pip install py-cid pycryptodome cbor2")
    IPFS_AVAILABLE = False
    IPFSBridge = None
    IPFSConfig = None


def print_section(title):
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def demo_basic_checkpoint():
    """Demo: Basic checkpoint without IPFS."""
    print_section("Demo 1: Basic Checkpoint (No IPFS)")
    
    game = GameEngine(seed=42)
    
    # Register a company
    company = game.register_company(
        company_name="Acme Corp",
        founding_capital_usd=100000.0,
        industry_sector=IndustrySector.TECH,
        sovereign_signature="a" * 64
    )
    
    print(f"✓ Registered company: {company.company_name} ({company.company_id})")
    
    # Execute some operations
    game.execute_operation(company.company_id, OperationType.HIRE, {"num_employees": 10})
    game.execute_operation(company.company_id, OperationType.PRODUCE, {"units": 100})
    game.tick()
    
    print(f"✓ Executed operations (tick {game.current_tick})")
    print(f"  - Employees: {company.resources.employees}")
    print(f"  - Inventory: {company.resources.inventory_units}")
    
    # Create checkpoint
    checkpoint = game.create_checkpoint()
    
    print(f"\n✓ Checkpoint created:")
    print(f"  - ID: {checkpoint['checkpoint_id']}")
    print(f"  - Tick: {checkpoint['tick']}")
    print(f"  - Hash: {checkpoint['canonical_sha256'][:16]}...")
    print(f"  - IPFS CID: {'Not available (no IPFS bridge)' if 'ipfs_cid' not in checkpoint else checkpoint['ipfs_cid']}")


def demo_ipfs_checkpoint():
    """Demo: Checkpoint with IPFS integration."""
    if not IPFS_AVAILABLE:
        print_section("Demo 2: IPFS Checkpoint (SKIPPED - IPFS not available)")
        print("⚠️  Install IPFS libraries to enable this demo")
        return
    
    print_section("Demo 2: IPFS-Backed Checkpoint")
    
    # Initialize with IPFS bridge
    try:
        ipfs_config = IPFSConfig(
            api_endpoint="http://127.0.0.1:5001",
            gateway_endpoint="http://127.0.0.1:8080"
        )
        ipfs_bridge = IPFSBridge(ipfs_config)
        
        # Check if IPFS daemon is running
        if not ipfs_bridge.is_available():
            print("⚠️  IPFS daemon not running on localhost:5001")
            print("   Start IPFS daemon: ipfs daemon")
            print("   Demo will continue without IPFS pinning\n")
            ipfs_bridge = None
    except Exception as e:
        print(f"⚠️  Could not connect to IPFS: {e}")
        print("   Demo will continue without IPFS pinning\n")
        ipfs_bridge = None
    
    game = GameEngine(seed=42, ipfs_bridge=ipfs_bridge)
    
    # Register companies
    company1 = game.register_company(
        company_name="Tech Innovators Inc",
        founding_capital_usd=150000.0,
        industry_sector=IndustrySector.TECH,
        sovereign_signature="b" * 64
    )
    
    company2 = game.register_company(
        company_name="Manufacturing Co",
        founding_capital_usd=120000.0,
        industry_sector=IndustrySector.MANUFACTURING,
        sovereign_signature="c" * 64
    )
    
    print(f"✓ Registered 2 companies")
    
    # Execute operations
    game.execute_operation(company1.company_id, OperationType.HIRE, {"num_employees": 15})
    game.execute_operation(company1.company_id, OperationType.PRODUCE, {"units": 150})
    game.execute_operation(company2.company_id, OperationType.HIRE, {"num_employees": 20})
    game.execute_operation(company2.company_id, OperationType.PRODUCE, {"units": 200})
    
    # Advance 3 ticks
    for _ in range(3):
        game.tick()
    
    print(f"✓ Simulated 3 ticks")
    print(f"  - Current tick: {game.current_tick}")
    print(f"  - Company 1 cash: ${company1.resources.cash_usd:,.2f}")
    print(f"  - Company 2 cash: ${company2.resources.cash_usd:,.2f}")
    
    # Create checkpoint
    checkpoint = game.create_checkpoint()
    
    print(f"\n✓ Checkpoint created:")
    print(f"  - ID: {checkpoint['checkpoint_id']}")
    print(f"  - Tick: {checkpoint['tick']}")
    print(f"  - Canonical Hash: {checkpoint['canonical_sha256'][:16]}...")
    print(f"  - Merkle Root: {checkpoint['merkle_root'][:16]}...")
    
    if 'ipfs_cid' in checkpoint:
        print(f"  - IPFS CID: {checkpoint['ipfs_cid']}")
        print(f"  - Multihash: {checkpoint['multihash'][:20]}...")
        print(f"  - Storage URI: {checkpoint['storage_uri']}")
        print(f"\n✅ Checkpoint is content-addressed and pinned to IPFS!")
    else:
        print(f"  - IPFS CID: Not available (IPFS daemon not running)")


def demo_deterministic_replay():
    """Demo: Deterministic replay from checkpoint."""
    if not IPFS_AVAILABLE:
        print_section("Demo 3: Deterministic Replay (SKIPPED)")
        return
    
    print_section("Demo 3: Deterministic Replay & Verification")
    
    # Try to connect to IPFS
    try:
        ipfs_bridge = IPFSBridge(IPFSConfig())
        if not ipfs_bridge.is_available():
            ipfs_bridge = None
    except:
        ipfs_bridge = None
    
    # Create initial game
    game = GameEngine(seed=42, ipfs_bridge=ipfs_bridge)
    
    # Register company
    company = game.register_company(
        company_name="Replay Test Corp",
        founding_capital_usd=100000.0,
        industry_sector=IndustrySector.SERVICES,
        sovereign_signature="d" * 64
    )
    
    # Execute operations and advance to tick 5
    for tick in range(5):
        game.execute_operation(company.company_id, OperationType.HIRE, {"num_employees": 2})
        game.execute_operation(company.company_id, OperationType.PRODUCE, {"units": 20})
        game.tick()
    
    print(f"✓ Initial run to tick {game.current_tick}")
    
    # Create checkpoint at tick 5
    checkpoint_tick_5 = game.create_checkpoint()
    tick_5_hash = checkpoint_tick_5['canonical_sha256']
    
    print(f"  - Checkpoint hash: {tick_5_hash[:16]}...")
    
    # Continue to tick 10
    for tick in range(5):
        game.execute_operation(company.company_id, OperationType.MARKET, {"units": 10})
        game.tick()
    
    final_state_hash = company.compute_state_hash()
    final_cash = company.resources.cash_usd
    
    print(f"  - Final state (tick 10): hash={final_state_hash[:16]}..., cash=${final_cash:,.2f}")
    
    # Simulate replay: create NEW game and load checkpoint
    print(f"\n✓ Replaying from checkpoint...")
    
    if ipfs_bridge and 'ipfs_cid' in checkpoint_tick_5:
        # Replay from IPFS CID
        game2 = GameEngine(seed=999, ipfs_bridge=ipfs_bridge)  # Different seed intentionally
        
        try:
            game2.load_checkpoint(checkpoint_tick_5['ipfs_cid'])
            print(f"  - Restored from IPFS CID: {checkpoint_tick_5['ipfs_cid']}")
        except Exception as e:
            print(f"  - IPFS restore failed: {e}")
            print(f"  - Using local checkpoint instead")
            # Fallback: manually restore from checkpoint dict
            game2 = GameEngine(seed=42)
            # Would need to implement local checkpoint restore
    else:
        print(f"  - IPFS not available, simulating local replay")
        game2 = GameEngine(seed=42)
        # Manually advance to tick 5 with same operations
        company2 = game2.register_company(
            company_name="Replay Test Corp",
            founding_capital_usd=100000.0,
            industry_sector=IndustrySector.SERVICES,
            sovereign_signature="d" * 64
        )
        for tick in range(5):
            game2.execute_operation(company2.company_id, OperationType.HIRE, {"num_employees": 2})
            game2.execute_operation(company2.company_id, OperationType.PRODUCE, {"units": 20})
            game2.tick()
        
        replayed_hash = game2.companies[list(game2.companies.keys())[0]].compute_state_hash()
        
        # Continue to tick 10
        for tick in range(5):
            game2.execute_operation(company2.company_id, OperationType.MARKET, {"units": 10})
            game2.tick()
        
        replayed_final_hash = company2.compute_state_hash()
        replayed_final_cash = company2.resources.cash_usd
        
        print(f"  - Replayed state (tick 10): hash={replayed_final_hash[:16]}..., cash=${replayed_final_cash:,.2f}")
        
        # Verify determinism
        if replayed_final_hash == final_state_hash:
            print(f"\n✅ REPLAY VERIFIED: State hashes match!")
            print(f"   Original: {final_state_hash}")
            print(f"   Replayed: {replayed_final_hash}")
        else:
            print(f"\n❌ REPLAY FAILED: State hashes differ")
            print(f"   This should not happen with deterministic game engine!")


def main():
    """Run all demonstrations."""
    print("\n" + "=" * 60)
    print("  IPFS-Backed Checkpoint System Demonstration")
    print("=" * 60)
    
    demo_basic_checkpoint()
    demo_ipfs_checkpoint()
    demo_deterministic_replay()
    
    print("\n" + "=" * 60)
    print("  ✅ Demonstration Complete!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
