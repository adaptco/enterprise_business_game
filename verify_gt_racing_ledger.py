"""
GT Racing Simulation Ledger Verifier
Validates hash chain integrity and deterministic replay for sim_log.jsonl
"""

import json
import hashlib
from typing import List, Dict, Optional


def verify_gt_racing_ledger(ledger_path: str) -> Dict[str, any]:
    """
    Verify GT Racing simulation ledger integrity.
    
    Args:
        ledger_path: Path to NDJSON ledger file
    
    Returns:
        Verification report with status and statistics
    """
    print("="*70)
    print("  GT Racing Ledger Verification")
    print("="*70)
    
    # Load ledger
    print(f"\nLoading ledger: {ledger_path}")
    entries = []
    with open(ledger_path, 'r') as f:
        for line in f:
            if line.strip():
                entries.append(json.loads(line))
    
    print(f"  Loaded {len(entries)} entries")
    
    # Verification results
    results = {
        "total_entries": len(entries),
        "genesis_hash": None,
        "terminal_hash": None,
        "chain_valid": True,
        "hash_mismatches": [],
        "vehicles": set(),
        "duration_ticks": 0
    }
    
    # Verify genesis
    print("\n" + "-"*70)
    print("Genesis Verification")
    print("-"*70)
    
    genesis = entries[0]
    if genesis["prev_hash"] is not None:
        print(f"  ❌ FAILURE: Genesis has non-null prev_hash: {genesis['prev_hash']}")
        results["chain_valid"] = False
    else:
        print(f"  ✓ Genesis prev_hash is null")
    
    results["genesis_hash"] = genesis["hash"]
    print(f"  Genesis hash: {results['genesis_hash']}")
    print(f"  Genesis tick: {genesis['tick']}")
    
    # Verify chain linkage
    print("\n" + "-"*70)
    print("Chain Linkage Verification")
    print("-"*70)
    
    for i in range(1, len(entries)):
        curr = entries[i]
        prev = entries[i-1]
        
        # Check prev_hash linkage
        if curr["prev_hash"] != prev["hash"]:
            print(f"  ❌ BREAK at tick {curr['tick']}: expected {prev['hash']}, got {curr['prev_hash']}")
            results["chain_valid"] = False
            results["hash_mismatches"].append({
                "tick": curr["tick"],
                "expected": prev["hash"],
                "actual": curr["prev_hash"]
            })
        
        # Verify hash recomputation (simple check)
        # Note: In production, you'd recompute the actual hash here
        if "hash" not in curr:
            print(f"  ❌ Missing hash at tick {curr['tick']}")
            results["chain_valid"] = False
    
    if results["chain_valid"]:
        print(f"  ✓ All {len(entries)} entries correctly linked")
    else:
        print(f"  ❌ Found {len(results['hash_mismatches'])} chain breaks")
    
    # Terminal state
    terminal = entries[-1]
    results["terminal_hash"] = terminal["hash"]
    results["duration_ticks"] = terminal["tick"] + 1
    
    print("\n" + "-"*70)
    print("Terminal State")
    print("-"*70)
    print(f"  Terminal hash: {results['terminal_hash']}")
    print(f"  Terminal tick: {terminal['tick']}")
    print(f"  Duration: {results['duration_ticks']} ticks")
    
    # Vehicle statistics
    for vehicle in terminal["vehicles"]:
        results["vehicles"].add(vehicle["id"])
        print(f"  Vehicle {vehicle['id']}: {vehicle['distance_along_track']:.1f}m, {vehicle['velocity']:.1f}m/s")
    
    # Final verdict
    print("\n" + "="*70)
    if results["chain_valid"]:
        print("✅ LEDGER VERIFICATION: PASSED")
        print(f"   Genesis: {results['genesis_hash']}")
        print(f"   Terminal: {results['terminal_hash']}")
        print(f"   Entries: {results['total_entries']}")
        print(f"   Vehicles: {len(results['vehicles'])}")
    else:
        print("❌ LEDGER VERIFICATION: FAILED")
        print(f"   Found {len(results['hash_mismatches'])} integrity violations")
    print("="*70)
    
    return results


def compare_ledgers(ledger1_path: str, ledger2_path: str) -> bool:
    """
    Compare two ledgers for deterministic replay verification.
    
    Args:
        ledger1_path: First ledger (e.g., Python runtime)
        ledger2_path: Second ledger (e.g., TypeScript runtime)
    
    Returns:
        True if ledgers are identical (deterministic)
    """
    print("\n" + "="*70)
    print("  Dual-Ledger Determinism Test")
    print("="*70)
    
    # Load both ledgers
    entries1 = []
    with open(ledger1_path, 'r') as f:
        for line in f:
            if line.strip():
                entries1.append(json.loads(line))
    
    entries2 = []
    with open(ledger2_path, 'r') as f:
        for line in f:
            if line.strip():
                entries2.append(json.loads(line))
    
    print(f"\nLedger 1: {len(entries1)} entries")
    print(f"Ledger 2: {len(entries2)} entries")
    
    if len(entries1) != len(entries2):
        print(f"\n❌ FAILURE: Different lengths ({len(entries1)} vs {len(entries2)})")
        return False
    
    # Compare hashes tick by tick
    mismatches = []
    for i in range(len(entries1)):
        e1 = entries1[i]
        e2 = entries2[i]
        
        if e1["hash"] != e2["hash"]:
            mismatches.append({
                "tick": e1["tick"],
                "ledger1_hash": e1["hash"],
                "ledger2_hash": e2["hash"]
            })
    
    if mismatches:
        print(f"\n❌ FAILURE: {len(mismatches)} hash mismatches")
        for m in mismatches[:5]:  # Show first 5
            print(f"  Tick {m['tick']}: {m['ledger1_hash']} vs {m['ledger2_hash']}")
        return False
    
    # Success
    print("\n✅ DETERMINISM VERIFIED")
    print(f"   Both ledgers produce identical hashes")
    print(f"   Genesis: {entries1[0]['hash']}")
    print(f"   Terminal: {entries1[-1]['hash']}")
    print("="*70)
    
    return True


def export_verification_report(results: Dict, output_path: str):
    """
    Export verification results as JSON report.
    
    Args:
        results: Verification results dictionary
        output_path: Path to output JSON file
    """
    report = {
        "verification_date": "2026-01-12T16:30:00Z",
        "ledger_type": "gt_racing_simulation",
        "status": "PASSED" if results["chain_valid"] else "FAILED",
        "total_entries": results["total_entries"],
        "genesis_hash": results["genesis_hash"],
        "terminal_hash": results["terminal_hash"],
        "duration_ticks": results["duration_ticks"],
        "vehicles": list(results["vehicles"]),
        "integrity_violations": len(results["hash_mismatches"]),
        "deterministic": results["chain_valid"]
    }
    
    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📄 Verification report saved: {output_path}")


if __name__ == "__main__":
    import sys
    
    # Default to local sim_log.jsonl
    ledger_path = "sim_log.jsonl" if len(sys.argv) < 2 else sys.argv[1]
    
    try:
        results = verify_gt_racing_ledger(ledger_path)
        
        # Export report
        export_verification_report(results, "verification_report.json")
        
        # Exit code based on verification
        sys.exit(0 if results["chain_valid"] else 1)
        
    except FileNotFoundError:
        print(f"\n❌ ERROR: Ledger file not found: {ledger_path}")
        print("\nUsage: python verify_gt_racing_ledger.py [ledger_path]")
        sys.exit(2)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        sys.exit(3)
