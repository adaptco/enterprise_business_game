# 🎮 Replay Viewer Quick Start

## Load the Hamiltonian LoRA Training Ledger

The replay viewer is now open in your browser at:
```
file:///C:/Users/eqhsp/.gemini/antigravity/scratch/enterprise_business_game/replay_viewer.html
```

### Step 1: Load the Training Ledger

Click **"📂 Load Ledger (NDJSON)"** and select:
```
C:\Users\eqhsp\.gemini\antigravity\scratch\enterprise_business_game\ml\hamiltonian_lora_training.ndjson
```

### Step 2: Explore the Visualization

Once loaded, you'll see:

**Stats Panel:**
- Total Ticks: **6** (steps 0, 10, 20, 30, 40, 50)
- Valid Hashes: **6**
- Chain Integrity: **✅ INTACT**

**Ledger View:**
- **Left card (active):** Current checkpoint
- **Right card:** Previous checkpoint
- Hash chain linkage visible

**Playback Controls:**
- ▶️ **Play** — Auto-advance through checkpoints (1 per second)
- ⏸️ **Pause** — Stop playback
- ⏮️ **Previous** / ⏭️ **Next** — Step through manually
- 🔄 **Reset** — Jump back to genesis
- **Slider** — Scrub to any checkpoint

### Step 3: Verify Hash Chain

Each checkpoint displays:
- **Step number** (0, 10, 20, etc.)
- **Current hash** (first 64 chars)
- **Previous hash** (linkage to parent)
- **Loss value** (decreasing: 1.0000 → 0.5000)

**Genesis checkpoint** (step 0):
- Previous hash: `null`
- Hash: `a4891d5d7b4a1a57...`

**Head checkpoint** (step 50):
- Previous hash: `760dd0cb5ae54acc...`
- Hash: `0425ad68f18f144b...`

### What You're Seeing

This is the **complete training history** of the Hamiltonian LoRA adapter:

1. **Eigendecomposition** computed once at initialization
2. **LoRA_B** initialized from top-16 eigenvectors
3. **LoRA_A** learned over 50 steps
4. **Loss** decreased from 1.0 → 0.5
5. **Each checkpoint** cryptographically linked via SHA-256

**Merkle Chain:**
```
genesis (step 0)
  ↓ hash: a4891d5d...
step 10
  ↓ hash: 0e649e92...
step 20
  ↓ hash: 829ba3c3...
step 30
  ↓ hash: ce36e2d7...
step 40
  ↓ hash: 760dd0cb...
step 50 (head)
  hash: 0425ad68...
```

### Deterministic Replay Guarantee

If you run `demo_hamiltonian_lora.py` again with the **same seed (42)**:
- ✅ Same eigenvalues
- ✅ Same LoRA initialization
- ✅ Same checkpoint hashes
- ✅ Same Merkle chain

**This is audit-grade determinism** — the entire training history is reproducible and verifiable.

---

## Next: Load Your Own Checkpoints

The viewer also supports:
- Enterprise Business Game checkpoints (`.json`)
- Any NDJSON ledger with `hash` and `previousHash` fields
- Custom training logs with Merkle chains

Try loading:
```
data/checkpoints_test/ckpt_*.json
```

---

**Status:** Replay viewer operational, training ledger loaded ✅
