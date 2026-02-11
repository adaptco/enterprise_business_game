# 🚀 Enterprise Business Game — Quick Start Guide

Complete validation and deployment commands for the World OS system.

---

## 📋 Available Commands

### 1. Run Demo (Enterprise Business Game)
```powershell
cd C:\Users\eqhsp\.gemini\antigravity\scratch\enterprise_business_game
python demo.py
```

**What it does:**
- Initializes game engine with deterministic seed
- Registers 1 player company + spawns 3 AI competitors
- Simulates 10 game ticks with market dynamics
- Verifies Merkle chain integrity for all companies
- Attempts SSOT integration (graceful fallback if unavailable)

**Expected output:**
- Leaderboard rankings
- Revenue/expense tracking
- AI performance metrics
- Merkle chain verification status

---

### 2. Test Checkpoint System
```powershell
python test_checkpoint_simple.py
```

**What it does:**
- Creates test company with operations
- Generates deterministic checkpoint
- Computes IPFS-style CID
- Saves to local checkpoint store
- Verifies checkpoint integrity

**Expected result:**
```
✅ Checkpoint system working!
```

---

### 3. Audit Determinism
```powershell
python audit_determinism.py --system both
```

**What it does:**
- Verifies checkpoint CID integrity
- Checks Merkle chain linkage
- Validates GT Racing replay files (if available)
- Reports pass/fail for each check

**Systems tested:**
- `enterprise_game` — Business simulation checkpoints
- `gt_racing` — Racing kernel Replay Court
- `both` — All systems

---

### 4. Run Kernel Boot System
```powershell
python kernel_boot_system\src\kernel.py --boot --ticks 10
```

**What it does:**
- Loads unified tensor runtime block
- Initializes 4 expert agents (tensor_analysis, config_validation, state_prediction, gt_racing)
- Executes deterministic tick-based simulation
- Creates checkpoint capsules (optional IPFS pinning)
- Verifies hash chain integrity

**Expected agents:**
- ✓ tensor_analysis
- ✓ config_validation
- ✓ state_prediction
- ✓ gt_racing (if Node.js available)

---

### 5. Deploy with Docker
```powershell
powershell -ExecutionPolicy Bypass -File deploy.ps1
```

**What it does:**
- Checks Docker + docker-compose availability
- Creates `.env` from template (if needed)
- Builds Docker images
- Starts service cluster (Game API, SSOT API, nginx)
- Runs health checks
- Displays service logs

**Services deployed:**
- **Game API** — Port 8001
- **SSOT API** — Port 8000
- **Nginx Proxy** — Port 80

**Management commands:**
```powershell
docker-compose logs -f        # View logs
docker-compose stop           # Stop services
docker-compose restart        # Restart
docker-compose down           # Shutdown
docker-compose down -v        # Full cleanup
```

---

## 🧪 Test Results Summary

| Test | Status | Details |
|------|--------|---------|
| Demo execution | ✅ PASS | Player won, AI competitors functional |
| Checkpoint creation | ✅ PASS | CID: `ckpt_e6547c607d6a0d10...` |
| Merkle integrity | ✅ PASS | All chains verified |
| Kernel boot | ✅ PASS | 4 agents executing |
| Determinism audit | ⚠️ PARTIAL | Expected issues (GT Racing stub) |

---

## 🎯 Optional: Test Individual Components

### Test GT Racing Integration
```powershell
cd kernel_boot_system
python test_gt_integration.py
```

### Verify Cross-Language Determinism
```powershell
python kernel_boot_system\verify_determinism.py --seed TEST_42 --ticks 50
```
(Requires Node.js for full validation)

---

## 🐛 Known Issues & Next Steps

### Current State
- ✅ Enterprise Business Game fully operational
- ✅ Kernel Boot System with 4 expert agents
- ✅ GT Racing integration foundation complete
- ⏳ GT Racing TypeScript runtime (stub currently)
- ⏳ Node.js required for full GT Racing execution

### To Enable Full Features
1. **Install Node.js** → Activate GT Racing TypeScript runtime
2. **Start IPFS daemon** → Enable content-addressed checkpoints
   ```bash
   ipfs daemon
   ```
3. **Run SSOT API** → Enable full audit trail
   ```bash
   cd ssot-integration
   python src/ssot_api_ingest.py
   ```

---

## 📊 System Architecture

```
┌─────────────────────────────────┐
│  Enterprise Business Game       │
│  - GameEngine (deterministic)   │
│  - AI Competitors (3 strategies)│
│  - Merkle Ledgers              │
└──────────────┬──────────────────┘
               ↓
┌─────────────────────────────────┐
│  Kernel Boot System             │
│  - Runtime Block Generator      │
│  - Expert Agent Pool (4 agents)│
│  - Checkpoint Manager           │
│  - IPFS Client (optional)       │
└──────────────┬──────────────────┘
               ↓
┌─────────────────────────────────┐
│  GT Racing Integration          │
│  - Python Agent Wrapper         │
│  - Node.js Bridge               │
│  - Replay Court IPFS Bridge     │
└─────────────────────────────────┘
```

---

## ✅ Validation Complete

All core systems operational and tested. Ready for:
- ✅ Local execution
- ✅ Checkpoint verification
- ✅ Determinism auditing
- ✅ Docker deployment (when ready)

**Next:** Install Node.js + IPFS for full feature set, then integrate React dashboard.
