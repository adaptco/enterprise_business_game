# 🏙️ Enterprise Business Game Simulation

A self-running, self-tuning, self-healing enterprise business simulation with shell companies, AI competitors, deterministic market dynamics, and audit-grade Merkle lineage.

## Features

✅ **Shell Company Registration** — Sovereign identity with cryptographic signatures  
✅ **Idempotent Ledger** — Hash-chained transactions with double-entry accounting  
✅ **Deterministic Market Simulation** — Reproducible economic conditions  
✅ **AI Competitors** — Rule-based agents with strategy profiles (aggressive, conservative, balanced)  
✅ **SSOT Integration** — Sovereign state capsules for tamper-evident audit trails  
✅ **Merkle Chain Integrity** — Verifiabl lineage for all transactions and state  
✅ **FastAPI Backend** — REST endpoints for game management  
✅ ![Vault Integrity](https://img.shields.io/badge/Vault%20Integrity-passing-success)  

---

## Quick Start

### Local Demo

```bash
pip install -r requirements.txt
python demo.py
```

This will:

- Register a player company with initial capital
- Spawn 3 AI competitors (different strategies)
- Simulate 10 ticks of market activity
- Display leaderboard and financial results
- Verify Merkle chain integrity

### 🐳 Docker Deployment (Production)

**Deploy as self-running field hub:**

```bash
# Copy environment template
cp .env.example .env

# Deploy all services
chmod +x deploy.sh
./deploy.sh
```

**Services started:**

- Game API (port 8001)
- SSOT API (port 8000)
- Master Agent (autonomous orchestrator)
- Nginx reverse proxy (port 80)

See [DEPLOYMENT.md](DEPLOYMENT.md) for full guide.

---

## Architecture

### Core Components

```text
enterprise_business_game/
├── schemas/                      # JSON schemas (JCS canonical)
│   ├── company_registration.v1.schema.json
│   ├── business_operation.v1.schema.json
│   ├── market_state.v1.schema.json
│   ├── financial_transaction.v1.schema.json
│   └── company_state.v1.schema.json
│
├── src/
│   ├── ledger.py                 # Idempotent Merkle-chained ledger
│   ├── game_engine.py            # Deterministic tick progression
│   ├── api.py                    # FastAPI service
│   ├── ssot_bridge.py            # SSOT integration client
│   └── ai_agents/
│       ├── rule_based_agent.py   # AI decision trees
│       └── agent_orchestrator.py # AI competitor management
│
├── demo.py                       # Full game demonstration
└── requirements.txt
```

### Business Operations

| Operation   | Description             | Resource Impact                |
| ----------- | ----------------------- | ------------------------------ |
| **HIRE**    | Hire employees          | -Cash, +Employees              |
| **PRODUCE** | Manufacture goods       | -Cash (materials), +Inventory  |
| **MARKET**  | Sell to market          | -Inventory, +Cash, +Revenue    |
| **R_AND_D** | Research & Development  | -Cash, +Brand Value            |
| **FIRE**    | Lay off employees       | +Cash (savings), -Employees    |

### AI Strategies

- **Aggressive Growth** — High risk, rapid expansion, maximize market share
- **Conservative** — Low risk, sustainable growth, prioritize cash flow
- **Balanced** — Moderate risk/reward, adaptable to market conditions

---

## API Endpoints

Start the API server:

```bash
cd src
python api.py  # Runs on http://localhost:8001
```

### Company Management

```http
POST /company/register
GET /company/{company_id}/status
GET /company/{company_id}/ledger
POST /company/{company_id}/operation
```

### Game Management

```http
POST /game/tick                  # Advance simulation
GET /game/state                  # Get market state
GET /game/verify                 # Verify Merkle chains
GET /game/companies              # List all companies
```

---

## SSOT Integration

To enable audit trail persistence:

1. Start the SSOT API:

   ```bash
   cd C:\Users\eqhsp\.gemini\antigravity\scratch\ssot-integration\src
   python ssot_api_ingest.py  # Runs on http://localhost:8000
   ```

2. Run the game — it will automatically emit sovereign state capsules every 3 ticks

3. Verify lineage:

   ```bash
   curl http://localhost:8000/lineage/latest
   ```

---

## Determinism Contract Compliance

This implementation follows **[Determinism Contract v1](../ssot-integration/determinism.contract.v1.md)**:

✅ **Ordered Hashing** — All JSON serialization uses `sort_keys=True`  
✅ **Error Envelopes** — Standardized error responses  
✅ **Decision Traces** — Every operation logged with audit trail  
✅ **Invariant Failure Modes** — Predictable error handling  

---

## Merkle Chain Verification

Every company maintains a hash-chained transaction ledger:

```text
Genesis → Txn1 → Txn2 → Txn3 → ...
   ↓        ↓      ↓      ↓
 Hash1   Hash2  Hash3  Hash4
```

Verify integrity:

```python
from game_engine import GameEngine

game = GameEngine()
# ... register companies, execute operations ...

results = game.verify_all_chains()
# Returns: {"company_id": True/False, ...}
```

---

## Example Usage

```python
from game_engine import GameEngine, IndustrySector, OperationType
from ai_agents import AgentOrchestrator

# Initialize game
game = GameEngine(seed=42)

# Register company
company = game.register_company(
    company_name="Acme Corp",
    founding_capital_usd=100000.0,
    industry_sector=IndustrySector.TECH,
    sovereign_signature="a" * 64
)

# Execute operations
game.execute_operation(
    company.company_id,
    OperationType.HIRE,
    {"num_employees": 5}
)

game.execute_operation(
    company.company_id,
    OperationType.PRODUCE,
    {"units": 50}
)

# Advance tick (pays salaries, updates market)
game.tick()

# Get leaderboard
market_state = game.get_market_state()
print(market_state['company_rankings'])
```

---

## Roadmap

### Phase 6 (Future Work)

- [ ] **Master Agent** — Self-tuning cyberspace control plane
- [ ] **React Dashboard** — Real-time visualization UI
- [ ] **Reinforcement Learning** — Upgrade AI agents to self-learning policies
- [ ] **Multiplayer Mode** — WebSocket support for live competition
- [ ] **Blockchain Export** — Deploy Merkle chains to Ethereum/Polygon

---

## License

MIT License — Built for educational and research purposes.

---

## Credits

Designed as a **toymodel at runtime** for:

- Shell company sovereignty
- Deterministic market simulation
- AI-driven competition
- Audit-grade lineage tracking

Part of the **Qube-Axiomatic-01** universe.

🏁 **Ready to compete?**
