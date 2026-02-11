# Quick Start Guide — Full System Setup

## Current Status

✅ **Node.js v22.18.0** — Installed and ready  
⚠️ **IPFS** — Not installed  
🔄 **SSOT API** — Starting...

---

## 1. IPFS Installation (Optional)

IPFS enables content-addressed checkpoint storage. **Not required for core functionality.**

### Windows Installation

```powershell
# Download IPFS Desktop (easiest)
# Visit: https://docs.ipfs.tech/install/ipfs-desktop/

# Or install via command line (requires scoop)
scoop install ipfs

# Initialize IPFS
ipfs init

# Start daemon in background
Start-Process -NoNewWindow ipfs daemon
```

### Verify Installation

```bash
ipfs --version
# Expected: ipfs version 0.x.x

ipfs id
# Should show your peer ID
```

### Configure for Game

```bash
# Add checkpoint directory to IPFS
ipfs add -r ./data/checkpoints_test

# Example output:
# added Qm... ckpt_6e3ff16bfeef3c77ca92ef8f31de6b88.json
```

---

## 2. SSOT API Setup

Already available at `../ssot-integration/`

### Start SSOT API

```bash
# Terminal 1: Start SSOT API
cd C:\Users\eqhsp\.gemini\antigravity\scratch\ssot-integration\src
python ssot_api_ingest.py

# Output: Running on http://localhost:8000
```

### Verify SSOT API

```bash
# Terminal 2: Test health endpoint
curl http://localhost:8000/health

# Expected: {"status":"healthy","service":"ssot-api","chain_height":0}
```

---

## 3. GT Racing TypeScript Runtime

Node.js is already installed (v22.18.0). Ready to run GT Racing!

### Setup GT Racing Project

```bash
# Create new TypeScript project
cd C:\Users\eqhsp\.gemini\antigravity\scratch
mkdir gt-racing-26
cd gt-racing-26

# Initialize npm project
npm init -y

# Install dependencies
npm install vite @types/node
npm install --save-dev vitest @vitejs/plugin-react

# Create vite.config.ts
```

### Minimal GT Racing Shell

Create `src/main.ts`:

```typescript
import { GameLoop } from './app/GameLoop';

const game = new GameLoop();
game.reset({ seed: 'GT_RACING_26', enableRemoteAgents: false });
game.start();

console.log('🏎️ GT Racing '26 started');
```

### Run

```bash
npm run dev
# Opens browser at http://localhost:5173
```

---

## Full Integration Test

Once all services are running:

### Terminal 1: SSOT API

```bash
cd C:\Users\eqhsp\.gemini\antigravity\scratch\ssot-integration\src
python ssot_api_ingest.py
```

### Terminal 2: Enterprise Business Game

```bash
cd C:\Users\eqhsp\.gemini\antigravity\scratch\enterprise_business_game
python src/master_agent_checkpointed.py
```

### Terminal 3: (Optional) IPFS Daemon

```bash
ipfs daemon
```

### Verify Integration

```bash
# Check SSOT capsules
curl http://localhost:8000/lineage/latest

# Check game API
curl http://localhost:8001/health

# Check checkpoints
ls data/checkpoints_test/
```

---

## Troubleshooting

### IPFS Not Found

**Solution:** Install IPFS Desktop from <https://docs.ipfs.tech/install/ipfs-desktop/>

### SSOT API Port Conflict

**Solution:** Edit `ssot_api_ingest.py`, change port from 8000 to 8080

### Node.js Version Issues

**Solution:** Already at v22.18.0 — should work fine

### Game Won't Start

**Solution:** All services are optional! Game works standalone with:

```bash
python demo.py
```

---

## Services Summary

| Service             | Port | Status        | Required     |
| ------------------- | ---- | ------------- | ------------ |
| Enterprise Game API | 8001 | Ready         | ✅ Core      |
| SSOT API            | 8000 | Starting      | ⚠️ Optional  |
| IPFS Daemon         | 5001 | Not installed | ⚠️ Optional  |
| GT Racing           | 5173 | Not setup     | ⚠️ Optional  |

**Core functionality works without optional services!**

---

## Next Steps

1. ✅ **Node.js installed** — Ready for TypeScript
2. ⚠️ **IPFS** — Install if you want distributed checkpoints
3. 🔄 **SSOT API** — Currently starting

**Recommended:**

- Keep SSOT API running for full audit trail
- Install IPFS only if deploying to production
- GT Racing setup is separate project (optional)
