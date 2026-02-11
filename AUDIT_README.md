# Deterministic Replay Audit - CI Integration

## Quick Start

```bash
# Audit Enterprise Business Game checkpoints
python audit_determinism.py --system enterprise_game

# Audit GT Racing '26 replay court
python audit_determinism.py --system gt_racing --replay-file replay.ndjson

# Audit both systems
python audit_determinism.py --both

# Run with replay verification
python audit_determinism.py --both --verify-replay
```

## What It Verifies

### 1. **CID Integrity** (Enterprise Game)

- ✓ Each checkpoint file name matches SHA-256 hash of content
- ✓ Canonical JSON computation (sorted keys, integers only)
- ✓ No float drift in state snapshots

### 2. **Merkle Chain Linkage** (Both Systems)

- ✓ Each entry's `previousHash` points to correct parent
- ✓ No gaps or breaks in chain
- ✓ Genesis entry has `null` previous hash

### 3. **Hash Recomputation** (GT Racing)

- ✓ Ledger entry hashes match computed values
- ✓ Canonical hash function produces identical results
- ✓ State snapshots are tamper-evident

### 4. **Deterministic Replay** (Optional)

- ✓ Same seed produces identical game state
- ✓ Checkpoint restoration matches original tick
- ✓ RNG fork consistency

## CI/CD Integration

### GitHub Actions

```yaml
name: Determinism Audit

on: [push, pull_request]

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Run audit script
        run: python audit_determinism.py --both
```

### Pre-commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

echo "🔐 Running determinism audit..."
python audit_determinism.py --system enterprise_game

if [ $? -ne 0 ]; then
    echo "❌ Determinism audit failed! Aborting commit."
    exit 1
fi

echo "✅ Determinism verified"
```

## Output Example

```text
🔐 DETERMINISTIC REPLAY AUDIT
============================================================

============================================================
ENTERPRISE BUSINESS GAME - CHECKPOINT VERIFICATION
============================================================
✓ Checkpoints found (3 files)
✓ CID integrity: ckpt_21d28fe22f...
✓ CID integrity: ckpt_a4b5c6d7e8...
✓ CID integrity: ckpt_f9g0h1i2j3...
✓ Chain linkage: tick 1
✓ Chain linkage: tick 11
✓ Chain linkage: tick 21

============================================================
GT RACING '26 - REPLAY COURT VERIFICATION
============================================================
✓ Replay entries loaded (248 entries)
✓ Entry 0 previous hash
✓ Entry 0 hash (a1b2c3d4e5f6...)
✓ Entry 1 previous hash
✓ Entry 1 hash (g7h8i9j0k1l2...)
...

============================================================
AUDIT SUMMARY
============================================================
Passed: 257
Failed: 0

✅ All checks passed
```

## Failure Example

```text
❌ AUDIT SUMMARY
============================================================
Passed: 12
Failed: 2

Failed checks:
  ✗ CID integrity: ckpt_21d28fe22f...: Computed: ckpt_deadbeef1234...
  ✗ Entry 42 hash: Computed: a1b2c3..., claimed: z9y8x7...

Exit code: 1
```

## Advanced Usage

### Custom Checkpoint Directory

```bash
python audit_determinism.py \
  --system enterprise_game \
  --checkpoints-dir ./custom_checkpoints/
```

### Verify Specific Replay File

```bash
python audit_determinism.py \
  --system gt_racing \
  --replay-file ./race_session_2026_01_10.ndjson
```

### Full Audit with Replay

```bash
python audit_determinism.py \
  --both \
  --verify-replay \
  --checkpoints-dir ./data/checkpoints_test
```

## Canonical Hash Specification

The audit script uses **JCS (JSON Canonicalization Scheme) subset**:

```python
def canonical_hash(obj: Dict[str, Any]) -> str:
    # 1. Keys sorted lexicographically
    # 2. Integers only (floats cause ValueError)
    # 3. UTF-8 encoding
    # 4. Minimal JSON escaping
    # 5. SHA-256 digest
```

**Guarantees:**

- ✅ Cross-platform identical hashes
- ✅ No floating-point drift
- ✅ Deterministic serialization
- ✅ Tamper-evident

## Testing

```bash
# Create test checkpoints
python test_checkpoint_simple.py

# Run audit
python audit_determinism.py --system enterprise_game

# Expected output: All checks passed
```

## Troubleshooting

### "CID integrity failed"

- **Cause:** Checkpoint file modified after creation
- **Fix:** Regenerate checkpoint or verify no manual edits

### "Chain linkage failed"

- **Cause:** Missing checkpoint or wrong order
- **Fix:** Ensure all checkpoints from genesis onward exist

### "Non-integer number in canonical hash"

- **Cause:** Float value in state snapshot
- **Fix:** Convert to integer (e.g., `int(x * 100)` for 2 decimal places)

## Integration with Existing Systems

### Enterprise Business Game

```python
# After creating checkpoint
from audit_determinism import canonical_hash

cid = f"ckpt_{canonical_hash(payload)[:32]}"
assert store.verify_checkpoint(checkpoint)
```

### GT Racing '26

```typescript
// After appending ledger entry
const hash = canonHashHex(toHash);
assert(verifyLedger(ledger));
```

---

**Exit Codes:**

- `0` — All checks passed
- `1` — One or more checks failed

**Use in CI:** Fail builds on exit code `1` to enforce determinism contract.
