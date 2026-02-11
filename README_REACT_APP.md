# 🏢 Enterprise Business Game - Full Stack Application

**Deterministic business simulation with React frontend + FastAPI backend + IPFS checkpoints**

## ✅ System Status

Both servers are now running:
- **Backend API**: http://localhost:8001 (FastAPI + Uvicorn)
- **Frontend UI**: http://localhost:3000 (React + Vite + TypeScript)

## Quick Start

### One-Click Launch

```powershell
.\start.ps1
```

This will:
1. Start the backend API server (port 8001)
2. Install frontend dependencies (if needed)
3. Start the frontend dev server (port 3000)
4. Open the browser automatically

### Manual Start

**Terminal 1 - Backend:**
```powershell
python src/api.py
```

**Terminal 2 - Frontend:**
```powershell
cd frontend
npm run dev
```

## Features Implemented

### Backend (FastAPI)
✅ Company registration with industry sectors  
✅ Business operations (HIRE, PRODUCE, MARKET)  
✅ Game tick advancement  
✅ IPFS checkpoint creation & restoration  
✅ Merkle chain integrity verification  
✅ Full audit trail  
✅ CORS enabled for frontend  

### Frontend (React + TypeScript)
✅ Real-time game state display  
✅ Company registration form  
✅ Live company list with stats  
✅ Operation buttons (Hire, Produce, Market)  
✅ Tick advancement control  
✅ Premium dark-mode UI  
✅ API proxy configuration  

## API Endpoints

### Game Management
- `GET /game/state` - Current market state
- `POST /game/tick` - Advance simulation tick
- `GET /game/companies` - List all companies
- `GET /game/verify` - Verify chain integrity

### Company Operations
- `POST /company/register` - Register new company
- `GET /company/{id}/status` - Company details
- `GET /company/{id}/ledger` - Transaction history
- `POST /company/{id}/operation` - Execute operation

### Checkpoints
- `POST /checkpoint/create` - Create checkpoint (with IPFS)
- `GET /checkpoint/{cid}` - Fetch checkpoint
- `POST /checkpoint/restore/{cid}` - Restore from checkpoint
- `GET /checkpoint/history` - List all checkpoints

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  React Frontend (TypeScript)                            │
│  - Vite dev server (port 3000)                          │
│  - REST API calls to backend                            │
│  - Real-time state updates                              │
└──────────────────┬──────────────────────────────────────┘
                   │ HTTP + Proxy
                   ↓
┌─────────────────────────────────────────────────────────┐
│  FastAPI Backend (Python)                               │
│  - Uvicorn server (port 8001)                           │
│  - Game engine with deterministic RNG                   │
│  - IPFS bridge for checkpoints                          │
│  - Merkle chain ledgers                                 │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ↓
┌─────────────────────────────────────────────────────────┐
│  IPFS Node (optional)                                   │
│  - Content-addressed checkpoint storage                 │
│  - CIDv1 with DAG-CBOR codec                            │
└─────────────────────────────────────────────────────────┘
```

## Project Structure

```
enterprise_business_game/
├── src/
│   ├── game_engine.py           # Core simulation logic
│   ├── api.py                   # FastAPI REST endpoints
│   ├── ledger.py                # Merkle transaction ledger
│   └── ipfs_bridge.py           # IPFS checkpoint integration
├── frontend/
│   ├── src/
│   │   ├── App.tsx              # Main React component
│   │   ├── App.css              # Premium dark-mode styling
│   │   └── main.tsx             # React entry point
│   ├── vite.config.ts           # Vite + proxy config
│   ├── package.json             # Dependencies
│   └── index.html               # HTML entry
├── start.ps1                    # One-click startup script
└── README_REACT_APP.md          # This file
```

## Screenshots

### Initial State
![Initial Game State](game_interface_initial_1768495512279 png)
- Tick: 0, Companies: 0
- Clean registration form ready

### Company Registered
![Acme Corp Registered](company_registered_1768495577130.png)
- "Acme Corp" successfully created
- $100,000 capital, 0 employees initially
- Operation buttons active (Hire, Produce, Market)

### After Operations
![After Hiring & Tick](final_game_state_1768495603101.png)
- Tick advanced to 1
- 5 employees hired
- Capital adjusted for hiring costs + overhead

## Dependencies

### Backend
```
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pydantic>=2.4.0
```

### Frontend
```json
{
  "react": "^18.2.0",
  "react-dom": "^18.2.0",
  "vite": "^5.0.0",
  "typescript": "^5.3.0"
}
```

## Development

### Hot Reload
Both backend and frontend support hot reload:
- **Backend**: Uvicorn auto-reloads on file changes
- **Frontend**: Vite HMR (Hot Module Replacement)

### API Testing
```powershell
# Health check
curl http://localhost:8001/health

# Get game state
curl http://localhost:8001/game/state

# Register company
curl -X POST http://localhost:8001/company/register `
  -H "Content-Type: application/json" `
  -d '{\"company_name\":\"Test Corp\",\"founding_capital_usd\":100000,\"industry_sector\":\"TECH\",\"sovereign_signature\":\"sig123\"}'
```

### Browser DevTools
Open React DevTools for component inspection:
```
F12 → React tab
```

## Next Steps

### Planned Features
- [ ] WebSocket support for real-time updates
- [ ] Company rivalry/competition mechanics
- [ ] Market price visualization (charts)
- [ ] Checkpoint restore UI
- [ ] Multi-player support
- [ ] AI opponent companies

### Deployment
For production deployment, see `DEPLOYMENT.md`

## Troubleshooting

**Backend won't start:**
```powershell
# Check if port 8001 is in use
Get-NetTCPConnection -LocalPort 8001

# Kill process if needed
Stop-Process -Id <PID> -Force
```

**Frontend build errors:**
```powershell
cd frontend
rm -r node_modules
npm install
```

**CORS errors:**
Check that `vite.config.ts` has correct proxy setup:
```ts
proxy: {
  '/api': {
    target: 'http://localhost:8001',
    changeOrigin: true
  }
}
```

---

**Status:** ✅ Fully operational React SPA with FastAPI backend!  
**Demo video:** `register_company_demo_1768495546398.webp`
