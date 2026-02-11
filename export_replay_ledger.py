"""
Simple Replay Court Export — Generate sample NDJSON for visualization.
"""

import json
import sys
import hashlib
from datetime import datetime, timezone


def generate_sample_ledger(output_file: str = "sample_replay_ledger.ndjson"):
    """Generate sample checkpoint ledger for demo"""
    print("🔄 Generating sample replay ledger...")
    
    entries = []
    prev_hash = None
    
    for tick in range(10):
        # Create entry
        entry = {
            "tick": tick,
            "agentId": "SYSTEM" if tick % 2 == 0 else f"AI_Agent_{tick % 3}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "stateSnapshot": {
                "value": tick * 10,
                "status": "ACTIVE"
            },
            "districtTrace": ["KERNEL", "EXEC", "CHECKPOINT"],
            "previousHash": prev_hash
        }
        
        # Compute hash
        hash_input = json.dumps({
            "tick": entry["tick"],
            "agentId": entry["agentId"],
            "stateSnapshot": entry["stateSnapshot"],
            "previousHash": entry["previousHash"]
        }, sort_keys=True, separators=(',', ':'))
        
        entry_hash = hashlib.sha256(hash_input.encode()).hexdigest()
        entry["hash"] = entry_hash
        entry["id"] = entry_hash[:12]
        
        entries.append(entry)
        prev_hash = entry_hash
    
    # Write NDJSON
    with open(output_file, 'w') as f:
        for entry in entries:
            f.write(json.dumps(entry) + '\n')
    
    print(f"✓ Generated {len(entries)} entries to {output_file}")
    return output_file


def export_game_ledger_simple(output_file: str = "game_replay_ledger.ndjson"):
    """Export game ledger with simplified imports"""
    print("🔄 Exporting game ledger...")
    
    try:
        sys.path.insert(0, 'src')
        from game_engine import GameEngine
        
        # Run game
        engine = GameEngine(seed=42)
        player_id = engine.register_company("Test Corp", "TECH", is_ai=False)
        
        # Execute operations
        for tick in range(5):
            if tick % 2 == 0:
                engine.execute_operation(player_id, "HIRE", {"num_employees": 1})
            engine.execute_operation(player_id, "PRODUCE", {"units": 10})
            engine.tick()
        
        # Export ledger
        company = engine.companies[player_id]
        ledger_data = company.ledger.export_ledger()
        
        entries = []
        for tx in ledger_data['transactions']:
            entry = {
                "tick": tx.get('tick', 0),
                "id": tx.get('id', '')[:12],
                "agentId": "Player",
                "hash": tx.get('hash', ''),
                "previousHash": tx.get('prev_hash'),
                "timestamp": tx.get('timestamp', datetime.now(timezone.utc).isoformat()),
                "transaction": {
                    "type": tx.get('type'),
                    "amount": tx.get('amount', 0),
                    "description": tx.get('description', '')
                }
            }
            entries.append(entry)
        
        # Write NDJSON
        with open(output_file, 'w') as f:
            for entry in entries:
                f.write(json.dumps(entry) + '\n')
        
        print(f"✓ Exported {len(entries)} game ledger entries to {output_file}")
        return output_file
    
    except Exception as e:
        print(f"⚠️  Could not export game ledger: {e}")
        return None


def main():
    print("\n📦 REPLAY COURT EXPORT TOOL")
    print("="*60)
    
    # Generate sample ledger
    sample_file = generate_sample_ledger()
    
    # Try to export game ledger
    game_file = export_game_ledger_simple()
    
    print("\n" + "="*60)
    print("✅ Export complete!")
    print("="*60)
    print(f"\nTo visualize:")
    print(f"  1. Open replay_viewer.html in browser")
    print(f"  2. Load file: {sample_file}")
    if game_file:
        print(f"     or file: {game_file}")
    print(f"  3. Use playback controls to step through ledger")
    print("\n")


if __name__ == "__main__":
    main()
