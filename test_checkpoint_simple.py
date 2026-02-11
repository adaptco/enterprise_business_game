"""
Simple Checkpoint System Test
Tests the new checkpoint.py module independently.
"""

import sys
sys.path.append('./src')

from game_engine import GameEngine, IndustrySector, OperationType
from checkpoint import (
    LocalCheckpointStore,
    create_checkpoint,
    compute_checkpoint_cid
)


print("="*60)
print("  🔐 Checkpoint System Test")
print("="*60)

# Create game
print("\n1. Creating game...")
game = GameEngine(seed=42)

# Register company
print("2. Registering company...")
company = game.register_company(
    company_name="Test Corp",
    founding_capital_usd=100000.0,
    industry_sector=IndustrySector.TECH,
    sovereign_signature="a" * 64
)
print(f"   ✓ Company: {company.company_name}")

# Execute operations
print("\n3. Executing operations...")
game.execute_operation(company.company_id, OperationType.HIRE, {"num_employees": 3})
game.execute_operation(company.company_id, OperationType.PRODUCE, {"units": 30})
game.tick()
print(f"   ✓ Tick {game.current_tick}")
print(f"   ✓ Employees: {company.resources.employees}")
print(f"   ✓ Inventory: {company.resources.inventory_units}")

# Create checkpoint
print("\n4. Creating checkpoint...")
try:
    checkpoint = create_checkpoint(game, prev_cid=None)
    print(f"   ✓ Checkpoint created")
    print(f"   ✓ Tick: {checkpoint['tick']}")
    print(f"   ✓ Companies: {len(checkpoint['state_vector']['companies'])}")
    
    # Compute CID
    cid = compute_checkpoint_cid(checkpoint)
    print(f"\n5. Computed CID:")
    print(f"   {cid}")
    
    # Save to store
    store = LocalCheckpointStore('./data/checkpoints_test')
    saved_cid = store.save_checkpoint(checkpoint)
    print(f"\n6. Saved to store:")
    print(f"   ✓ CID: {saved_cid}")
    
    # Verify
    if store.verify_checkpoint(checkpoint):
        print("\n✅ Checkpoint system working!")
    else:
        print("\n❌ Verification failed")
        
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
