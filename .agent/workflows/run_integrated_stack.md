---
description: Run the fully integrated PINN Arbitration and Code Sight Observability stack
---

# Unified Digital Twin Stack

This workflow launches the complete "Integration Magic" stack:

1. **Code Sight Server**: Observability backend (port 8080)
2. **Racing App**: Frontend dashboard (port 5173)

## 1. Start the Code Sight Server

Open a terminal and run:

```powershell
python code_sight/server.py
```

You should see:
> 🚀 Code Sight Server running on ws://localhost:8080 (ASCII banner)

## 2. Start the Racing App

Open a second terminal:

```powershell
cd racing-app
npm run dev
```

## 3. Verify Integration

1. Open the app in your browser (usually `http://localhost:5173`).
2. Navigate to the **"Simulator"** tab.
3. Click **"Start Expert Run"** (or similar) to activate the simulation.
4. Switch to the **"Observability"** tab.
5. Verification:
    - You should see the **"Chain Valid"** indicator in green.
    - **Active Sight Points** should populate with `PhyAtteN_R32.*`.
    - The **Observation Stream** should show live metrics:
        - `state_estimation_ms`
        - `residual_loss`
        - `hausdorff_nm`

## 4. Trigger Violation

1. Go back to **Simulator** -> **PINN Arbitration Layer**.
2. Click **"🔒 Inject Idempotency Violation"**.
3. Quickly switch to the **"Observability"** tab.
4. You should see a `VIOLATION_TRIGGERED` event log in the stream.

## Troubleshooting

- **Connection Failed?** Ensure the Python server is running on port 8080.
- **No Metrics?** Ensure the simulator is "Running".
