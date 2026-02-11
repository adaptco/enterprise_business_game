
# Code Sight Observability Framework

Code Sight is a real-time observability engine designed for AI agents and complex simulation systems. It provides a "sight glass" into the internal state of your models, enabling live monitoring of metrics, logs, and decision-making processes.

## Features

- **Decorator-based Instrumentation**: Easily trace functions and methods with `@sight_point`.
- **Merkle-Chained Ledger**: Immutable, verifiable log of all observations for auditability.
- **Real-time WebSocket Streaming**: Live data feed to the dashboard.
- **Multimodal Support**: Helper methods for logging text, images (base64), and tensors.
- **Zero-Config**: Auto-discovery of Code Sight server.

## Installation

The `code_sight` package is located in `enterprise_business_game/code_sight`. Ensure this directory is in your `PYTHONPATH`.

## Usage

### 1. Instrumenting Python Code

Import the `sight_point` decorator and apply it to your functions:

```python
from code_sight.core import sight_point

@sight_point(
    name="planning_step",
    modality="planning",
    metrics=["latency_ms", "token_count"]
)
def plan_route(destination):
    # Your logic here...
    return route
```

### 2. Manual Logging

Get the engine instance to log arbitrary events:

```python
from code_sight.core import get_code_sight

engine = get_code_sight()
engine.log_log(
    target="navigation_module",
    message="Recalculating due to obstacle",
    level="WARNING"
)
```

### 3. Starting the Server

Run the server to collect and broadcast observations:

```bash
python -m code_sight.server
```

Server runs on `ws://localhost:8765`.

### 4. Dashboard

The Dashboard is integrated into the Racing App (`racing-app`).
Start the frontend:

```bash
cd racing-app
npm run dev
```

Navigate to the "Observability" tab to view the live stream.

## Architecture

- **SightEngine**: Singleton core that manages the ledger and broadcasts.
- **ledger**: A Merkle chain of `Observation` objects.
- **WebSocketServer**: Handles client connections and distributes data.

## Integration Examples

See `demo_code_sight.py` for a standalone verification script.
See `enterprise_business_game/verify_integration.py` for end-to-end system verification.
