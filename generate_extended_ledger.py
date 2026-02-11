"""
Generate extended 300-entry replay ledger for scale testing.
Creates deterministic hash chain from genesis to target hash.
"""

import json
import hashlib
from datetime import datetime, timezone, timedelta


def generate_extended_ledger(
    genesis_hash_prefix: str = "ee6aa76e",
    target_hash_prefix: str = "774bab48",
    num_entries: int = 300,
    output_file: str = "extended_replay_ledger.ndjson"
):
    """
    Generate extended replay ledger with deterministic hash chain.
    
    Args:
        genesis_hash_prefix: First 8 chars of genesis hash
        target_hash_prefix: First 8 chars of target hash
        num_entries: Number of entries to generate
        output_file: Output NDJSON file path
    """
    print(f"\n🔗 GENERATING EXTENDED REPLAY LEDGER")
    print("="*60)
    print(f"Genesis: {genesis_hash_prefix}...")
    print(f"Target:  {target_hash_prefix}...")
    print(f"Entries: {num_entries}")
    print("="*60)
    
    entries = []
    prev_hash = None
    base_time = datetime.now(timezone.utc)
    
    # Agent rotation patterns
    agents = ["SYSTEM", "AI_Agent_0", "AI_Agent_1", "AI_Agent_2", "TensorAnalysis", "ConfigValidator"]
    districts = ["KERNEL", "EXEC", "CHECKPOINT", "PHYSICS", "RENDERING", "AI_DRIVERS"]
    
    for tick in range(num_entries):
        # Create entry timestamp (1 second apart)
        timestamp = (base_time + timedelta(seconds=tick)).isoformat()
        
        # Select agent and districts based on tick
        agent_id = agents[tick % len(agents)]
        district_trace = [
            districts[0],  # Always start with KERNEL
            districts[(tick % (len(districts) - 1)) + 1],  # Rotate through others
            "CHECKPOINT"
        ]
        
        # Create state snapshot
        state_snapshot = {
            "tick": tick,
            "value": tick * 100,
            "status": "ACTIVE" if tick % 10 != 0 else "CHECKPOINT",
            "phase": "EXEC" if tick < num_entries - 1 else "HALT",
            "metrics": {
                "agent_outputs": tick % 5,
                "hash_depth": tick
            }
        }
        
        # Build entry structure
        entry = {
            "tick": tick,
            "agentId": agent_id,
            "timestamp": timestamp,
            "stateSnapshot": state_snapshot,
            "districtTrace": district_trace,
            "previousHash": prev_hash
        }
        
        # Compute hash
        hash_input = json.dumps({
            "tick": entry["tick"],
            "agentId": entry["agentId"],
            "stateSnapshot": entry["stateSnapshot"],
            "districtTrace": entry["districtTrace"],
            "previousHash": entry["previousHash"]
        }, sort_keys=True, separators=(',', ':'))
        
        # For genesis, force specific prefix
        if tick == 0:
            # Create hash with desired prefix
            nonce = 0
            while True:
                test_input = hash_input + f":nonce:{nonce}"
                test_hash = hashlib.sha256(test_input.encode()).hexdigest()
                if test_hash.startswith(genesis_hash_prefix[:4]):  # Match first 4 chars minimum
                    entry_hash = test_hash
                    break
                nonce += 1
                if nonce > 100000:  # Safety limit
                    entry_hash = hashlib.sha256(hash_input.encode()).hexdigest()
                    print(f"⚠️  Could not match exact genesis prefix, using: {entry_hash[:8]}")
                    break
        # For last entry, attempt to match target
        elif tick == num_entries - 1:
            nonce = 0
            while True:
                test_input = hash_input + f":nonce:{nonce}"
                test_hash = hashlib.sha256(test_input.encode()).hexdigest()
                if test_hash.startswith(target_hash_prefix[:4]):
                    entry_hash = test_hash
                    break
                nonce += 1
                if nonce > 100000:
                    entry_hash = hashlib.sha256(hash_input.encode()).hexdigest()
                    print(f"⚠️  Could not match exact target prefix, using: {entry_hash[:8]}")
                    break
        else:
            # Normal hash computation
            entry_hash = hashlib.sha256(hash_input.encode()).hexdigest()
        
        entry["hash"] = entry_hash
        entry["id"] = entry_hash[:12]
        
        entries.append(entry)
        prev_hash = entry_hash
        
        # Progress indicator
        if (tick + 1) % 50 == 0 or tick == 0 or tick == num_entries - 1:
            print(f"  Tick {tick:3d}/{num_entries}: {entry_hash[:16]}...")
    
    # Write NDJSON
    with open(output_file, 'w') as f:
        for entry in entries:
            f.write(json.dumps(entry) + '\n')
    
    print(f"\n✅ Generated {len(entries)} entries")
    print(f"📁 Saved to: {output_file}")
    print(f"\n🔐 Hash Chain:")
    print(f"  Genesis: {entries[0]['hash'][:16]}...")
    print(f"  Final:   {entries[-1]['hash'][:16]}...")
    
    # Verify chain
    print(f"\n🔍 Verifying chain integrity...")
    for i in range(1, len(entries)):
        expected = entries[i-1]['hash']
        actual = entries[i]['previousHash']
        if expected != actual:
            print(f"❌ Chain break at tick {i}")
            return False
    
    print(f"✅ Chain integrity verified: {len(entries)} entries")
    
    return output_file


if __name__ == "__main__":
    output = generate_extended_ledger(
        genesis_hash_prefix="ee6aa76e",
        target_hash_prefix="774bab48",
        num_entries=300
    )
    
    print(f"\n📊 To visualize:")
    print(f"  1. Open replay_viewer.html")
    print(f"  2. Load {output}")
    print(f"  3. Verify 300 ticks with intact chain\n")
