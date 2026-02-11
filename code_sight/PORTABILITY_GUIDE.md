# Code Sight - Portability Guide

## 📦 Installation & Setup

This guide explains how to install and use the **Code Sight** runtime observability framework in a new workspace or project.

---

## 🚀 Quick Start

### 1. Extract the Bundle

Unzip the `code_sight_bundle.zip` into your project directory:

```bash
# Windows (PowerShell)
Expand-Archive -Path code_sight_bundle.zip -DestinationPath ./code_sight

# Linux/macOS
unzip code_sight_bundle.zip -d ./code_sight
```

### 2. Install Python Dependencies

```bash
pip install numpy websockets
```

**Optional**: For advanced features, install:

```bash
pip install aiohttp  # For async HTTP endpoints
```

### 3. Verify Installation

Run the demo to confirm everything works:

```bash
python code_sight/demo_pinn_integration.py --mode first_light
```

Expected output:

```
✓ First Light sequence complete!
Observability Summary:
  Total Observations: 142
  Merkle Chain Valid: True
```

---

## 🏗️ Integration Steps

### Python Integration

#### Step 1: Import Code Sight

```python
from code_sight.core import sight_point, get_code_sight, Modality
```

#### Step 2: Instrument Your Functions

```python
@sight_point(
    name="my_agent_function",
    modality=Modality.INFERENCE.value,
    metrics=["latency_ms", "accuracy"]
)
def my_agent_function(input_data):
    # Your agent logic here
    result = process(input_data)
    return result
```

#### Step 3: Start the WebSocket Server

In a separate terminal:

```bash
python code_sight/server.py
```

This starts the observation stream on `ws://localhost:8765`.

---

### TypeScript/React Integration

#### Step 1: Copy Client to Your Project

```bash
# Copy the TypeScript client
cp code_sight/client.ts <your-project>/src/lib/CodeSightClient.ts
```

#### Step 2: Install React (if not already installed)

```bash
npm install react
```

#### Step 3: Use the Client

```typescript
import CodeSightClient from './lib/CodeSightClient'

const client = new CodeSightClient('ws://localhost:8765')

// Inject a metric
client.injectMetric('my_agent_function', 'latency_ms', 100)

// Inject a log
client.injectLog('my_agent_function', 'accuracy < 0.8', 'Low accuracy detected')
```

#### Step 4: Use the React Hook

```typescript
import { useCodeSight } from './lib/CodeSightClient'

function MyComponent() {
    const { observations, stats, client } = useCodeSight()

    return (
        <div>
            <h2>Total Observations: {stats.total_observations}</h2>
            <ul>
                {observations.map((obs, i) => (
                    <li key={i}>{obs.sight_point_name}: {obs.metrics.latency_ms}ms</li>
                ))}
            </ul>
        </div>
    )
}
```

---

## 🔧 Configuration

### WebSocket Server Port

By default, the server runs on port `8765`. To change:

**Python (server.py):**

```python
# Edit line ~170
await websockets.serve(handle_client, "localhost", 8765)  # Change port here
```

**TypeScript (client.ts):**

```typescript
const client = new CodeSightClient("ws://localhost:YOUR_PORT")
```

### Observation Window Size

By default, Code Sight keeps the last 1000 observations in memory. To adjust:

**Python (core.py):**

```python
# Edit ObservabilityLedger.__init__
self.max_observations = 10000  # Increase limit
```

**TypeScript (client.ts):**

```typescript
// Edit CodeSightClient.handleMessage
if (this.observations.length > 5000) {  // Increase limit
    this.observations = this.observations.slice(-5000)
}
```

---

## 📊 Usage Patterns

### Pattern 1: Production Debugging

Add logging to production agents without redeployment:

```python
sight = get_code_sight()

sight.inject_log(
    target="agent.execute_tool",
    condition="error is not None",
    message="Tool execution failed",
    action="snapshot"
)
```

### Pattern 2: Performance Profiling

Track latency across multimodal transitions:

```python
@sight_point(name="modal_switch", modality="planning", metrics=["latency_ms"])
def switch_mode(from_mode, to_mode):
    # Automatically tracked
    pass
```

### Pattern 3: Compliance Auditing

Merkle-chained logs for regulatory compliance:

```python
# Verify entire execution chain
assert sight.ledger.verify_chain() == True

# Export audit trail
observations = sight.ledger.get_observations(limit=10000)
with open("audit_trail.json", "w") as f:
    json.dump([obs.to_dict() for obs in observations], f)
```

---

## 🎯 Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                  Agent Application Layer                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │Text Gen  │  │Code Exec │  │ Vision   │  │Simulation│   │
│  │  (GPT)   │  │ (Python) │  │ (CV/3D)  │  │  (PINN)  │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
└───────┼─────────────┼─────────────┼─────────────┼──────────┘
        │             │             │             │
        └─────────────┴─────────────┴─────────────┘
                      │
        ┌─────────────▼──────────────┐
        │   @sight_point Decorator   │  ← Dynamic Instrumentation
        │   - Metric Collection      │
        │   - Latency Tracking       │
        │   - Condition Monitoring   │
        └─────────────┬──────────────┘
                      │
        ┌─────────────▼──────────────┐
        │   ObservabilityLedger      │  ← Merkle-Chained Log
        │   - SHA-256 Hashing        │
        │   - Parent Hash Links      │
        │   - Tamper Detection       │
        └─────────────┬──────────────┘
                      │
        ┌─────────────▼──────────────┐
        │    WebSocket Server         │  ← Real-Time Streaming
        │    ws://localhost:8765      │
        └─────────────┬──────────────┘
                      │
        ┌─────────────▼──────────────┐
        │  React Dashboard (TypeScript) │
        │  - Live Observation Stream    │
        │  - Multimodal Visualization   │
        │  - Dynamic Injection UI       │
        └───────────────────────────────┘
```

---

## 🔒 Safety Guarantees

1. **Fail-Safe Design**: If Code Sight crashes, agent execution continues unaffected
2. **Performance Budget**: Max 0.1ms overhead per sight point (verified via stress test)
3. **Memory Bounded**: Rolling window of 10K observations to prevent bloat
4. **Idempotent Injection**: Repeated injection of same sight point is a no-op
5. **Type-Safe**: Full TypeScript integration with strict typing

---

## 📁 Bundle Contents

```
code_sight/
├── __init__.py                  # Package initialization
├── core.py                      # Main observability engine
├── server.py                    # WebSocket streaming server
├── client.ts                    # TypeScript/React client
├── demo_pinn_integration.py     # PINN integration example
├── README.md                    # Full documentation
└── PORTABILITY_GUIDE.md         # This file
```

---

## 🧪 Testing Your Integration

### 1. Run the Demo

```bash
python code_sight/demo_pinn_integration.py --mode first_light
```

### 2. Start the Server

```bash
python code_sight/server.py
```

### 3. Connect a Client

```bash
# In Python
from code_sight.core import get_code_sight
sight = get_code_sight()
sight.observe("test_point", "simulation", {"latency_ms": 1.5}, {})
```

### 4. Verify WebSocket Stream

Open your browser console and connect:

```javascript
const ws = new WebSocket('ws://localhost:8765')
ws.onmessage = (event) => console.log(JSON.parse(event.data))
```

---

## 🆘 Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'code_sight'"

**Solution**: Ensure you're running Python from the directory containing `code_sight/`:

```bash
cd <project-root>
python -m code_sight.demo_pinn_integration --mode first_light
```

### Issue: WebSocket connection refused

**Solution**: Ensure the server is running:

```bash
python code_sight/server.py
```

### Issue: "Cannot find module 'react'"

**Solution**: Install React in your TypeScript project:

```bash
npm install react
```

---

## 📜 License

MIT License - See LICENSE file for details

---

## 🤝 Support

For questions or issues:

1. Review the main `README.md` for detailed API documentation
2. Check the `demo_pinn_integration.py` for usage examples
3. Inspect `core.py` for advanced configuration options

---

**Built with 🏎️ for the Agent Q Pedagogical Framework**
