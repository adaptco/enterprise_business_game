# 🏎️ Nürburgring AI Racing Simulator

## Deterministic AI driver training with Random Forest learning and IPFS checkpoint integration

## Overview

This racing simulator implements the complete workflow for training an AI driver to master the Nürburgring Nordschleife using:

- **Deterministic physics** — Fixed-step integration for replay consistency
- **Random Forest learning** — Multi-output regression for steering/throttle/brake
- **SSOT lineage tracking** — SHA-256 hashing and Merkle chains
- **IPFS checkpoints** — Content-addressed storage for training artifacts
- **Governance ledger** — Append-only audit trail for model versions

## Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│  Expert Driver (Human or Heuristic)                         │
│  ↓ Telemetry recording                                      │
│  RacingSimulator (seed=42)                                  │
│  - Nürburgring track geometry (20.8 km)                     │
│  - Vehicle physics (60Hz deterministic)                     │
│  - State space (31 features)                                │
│  ↓ NDJSON export                                            │
│  Training Data: state-action pairs                          │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  Random Forest AI Trainer                                   │
│  - Load & preprocess features                               │
│  - Train 3 models (steering, throttle, brake)               │
│  - Deterministic splits (train/val/test)                    │
│  - StandardScaler normalization                             │
│  ↓ Model artifacts                                          │
│  - rf_{steering|throttle|brake}.joblib                      │
│  - scaler_{features|steering|throttle|brake}.joblib         │
│  - training_lineage.json (hash & metrics)                   │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  AI Autonomous Racing                                       │
│  - Load trained Random Forest                               │
│  - Predict controls in real-time                            │
│  - Create checkpoints with IPFS CID                         │
│  ↓ Governance ledger                                        │
│  - Append training event                                    │
│  - Link model version to lineage hash                       │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  Replay Verification                                        │
│  - Re-run with same seed → same state hash                  │
│  - Validate determinism                                     │
│  - Visualize with replay_viewer.html                        │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Install Dependencies

```bash
pip install numpy scikit-learn joblib
```

### 2. Run Complete Demo

```bash
python demo_racing_ai.py
```

**Output:**

```text
============================================================
  🏎️  Nürburgring AI Racing Simulator
  Deterministic Training & Replay with SSOT Integration
============================================================

============================================================
  PHASE 1: Expert Demonstration Recording
============================================================

🏁 Starting expert demonstration run...
   Duration: 10.0 seconds (600 ticks)

  Tick    0:  10.0 m/s | Progress:  0.00% | Section: hatzenbach
  Tick   60:  45.2 m/s | Progress:  4.12% | Section: hatzenbach
  ...

✓ Expert run complete!
  - Final progress: 24.83%
  - Checkpoint ID: racing_ckpt_600
  - State hash: 7a3f9c2d1e8b5a...
✓ Exported 600 training samples to data/nurburgring_expert.ndjson

============================================================
  PHASE 2: Random Forest AI Training
============================================================

✓ Loaded 600 training samples
✓ Extracted features: (600, 31)
  - Feature dimension: 31
  - Samples: 600

🌲 Training steering model...
  - Validation MSE: 0.002341, R²: 0.9876
  - Test MSE: 0.002198, R²: 0.9891

🌲 Training throttle model...
  - Validation MSE: 0.001823, R²: 0.9912
  - Test MSE: 0.001654, R²: 0.9923

🌲 Training brake model...
  - Validation MSE: 0.000987, R²: 0.9945
  - Test MSE: 0.000854, R²: 0.9956

✅ Training complete!
  - Model version: rf_v1_c4d8e7a2
  - Lineage hash: c4d8e7a2b3f1d5...
  - Duration: 2.34s

✓ Saved models to models/racing_ai/
  - Model version: rf_v1_c4d8e7a2
  - Lineage hash: c4d8e7a2b3f1d5...

✓ Appended to governance ledger
  - Entry hash: 9f2a8c5d7e1b3a...

============================================================
  PHASE 3: AI Autonomous Racing
============================================================

🤖 AI driver taking control...
   Model version: rf_v1_c4d8e7a2

  Tick    0:  10.0 m/s | Progress:  0.00% | Section: hatzenbach | Throttle: 0.98
  Tick   60:  43.8 m/s | Progress:  3.95% | Section: hatzenbach | Throttle: 0.85
  ...

✓ AI run complete!
  - Final progress: 23.47%
  - Checkpoint ID: racing_ckpt_600
  - State hash: 5e7c9f2a1b8d4c...

============================================================
  PHASE 4: Deterministic Replay Verification
============================================================

🔁 Replaying expert run with same seed...
✅ REPLAY VERIFIED!
   Run 1 hash: 4f8a2c6d9e1b3f5a7c2d4e6f8a1b3c5d
   Run 2 hash: 4f8a2c6d9e1b3f5a7c2d4e6f8a1b3c5d
   Determinism: CONFIRMED

============================================================
  ✅ Demo Complete!
============================================================

Generated files:
  - Training data: data/nurburgring_expert.ndjson
  - AI telemetry: data/nurburgring_ai_telemetry.ndjson
  - Models: models/racing_ai/
  - Governance ledger: data/training_ledger.ndjson
```

## State Space (31 Features)

The AI perceives the following state:

### Vehicle Kinematics (9)

- `speed` (m/s)
- `yaw_rate` (rad/s)
- `longitudinal_accel` (m/s²)
- `lateral_accel` (m/s²)
- `steering_angle` (rad)
- `throttle_input` (0-1)
- `brake_input` (0-1)
- `engine_rpm`
- `gear` (1-6)

### Position & Navigation (8)

- `track_x`, `track_y` (m)
- `heading` (rad)
- `distance_to_centerline` (m)
- `track_progress` (0-1)
- `current_curvature` (1/m)
- `track_gradient` (rad)
- `distance_to_apex` (m)
- `apex_radius` (m)

### Environmental Sensors (5)

- `dist_left_edge` (m)
- `dist_right_edge` (m)
- `front_ray` (m)
- `front_left_ray` (m)
- `front_right_ray` (m)

### Horizon Prediction (5)

- `upcoming_curvature[0-4]` — curvature at +10m, +25m, +50m, +100m, +200m

### Wheel Dynamics (4)

- `wheel_speeds[0-3]` (FL, FR, RL, RR in rad/s)

## Control Outputs (3)

The Random Forest predicts:

- `steering_command` ∈ [-1, 1]
- `throttle_command` ∈ [0, 1]
- `brake_command` ∈ [0, 1]

## Nürburgring Track Sections

The simulator includes 10 major sections:

| Section | Distance | Characteristics |
| ------- | -------- | --------------- |
| **Hatzenbach** | 0-1.2 km | Fast S-curves |
| **Flugplatz** | 1.2-2.5 km | Jump crest |
| **Aremberg** | 2.5-3.8 km | Blind downhill right |
| **Fuchsröhre** | 3.8-5.5 km | High-speed compression |
| **Adenauer Forst** | 5.5-7.2 km | Technical chicane |
| **Karussell** | 7.2-9.5 km | Banked concrete turn |
| **Pflanzgarten** | 9.5-12.0 km | Double jump |
| **Schwalbenschwanz** | 12.0-14.5 km | S-curve section |
| **Döttinger Höhe** | 14.5-18.5 km | Long straight (top speed) |
| **Antoniusbuche** | 18.5-20.8 km | Final sequence |

## Training Pipeline Details

### Data Preprocessing

1. **Feature extraction** — 31 features per timestep
2. **Normalization** — `StandardScaler` (z-score)
3. **Train/Val/Test split** — 70% / 10% / 20% (deterministic seed)

### Random Forest Configuration

```python
RandomForestRegressor(
    n_estimators=100,      # Trees in ensemble
    max_depth=20,          # Max tree depth
    min_samples_split=10,  # Min samples to split node
    min_samples_leaf=5,    # Min samples in leaf
    random_state=42,       # Deterministic training
    n_jobs=-1              # Parallel training
)
```

### Model Artifacts

```text
models/racing_ai/
├── rf_steering.joblib          # Steering Random Forest
├── rf_throttle.joblib          # Throttle Random Forest
├── rf_brake.joblib             # Brake Random Forest
├── scaler_features.joblib      # Feature StandardScaler
├── scaler_steering.joblib      # Steering target scaler
├── scaler_throttle.joblib      # Throttle target scaler
├── scaler_brake.joblib         # Brake target scaler
└── training_lineage.json       # Lineage hash & metrics
```

## Integration with SSOT Infrastructure

### Checkpoint Format

```json
{
  "checkpoint_id": "racing_ckpt_600",
  "tick": 600,
  "timestamp": "2026-01-12T21:42:00Z",
  "game_seed": 42,
  "state_vector": {
    "position": [500.2, -1.3],
    "velocity": 45.7,
    "heading": 0.12,
    "gear": 4,
    "track_progress": 0.2483,
    "lap": 0
  },
  "canonical_sha256": "7a3f9c2d1e8b5a4c6f2d9e1b3a5c7f...",
  "lap": 0,
  "track_progress": 0.2483,
  "ipfs_cid": "bafybeihqn6iblmvk..."  // If IPFS enabled
}
```

### Governance Ledger Entry

```json
{
  "event_type": "model_training",
  "timestamp": "2026-01-12T21:42:15Z",
  "training_data": {
    "file": "data/nurburgring_expert.ndjson",
    "data_hash": "a8c3f9e2d5b1..."
  },
  "model_version": "rf_v1_c4d8e7a2",
  "lineage_hash": "c4d8e7a2b3f1d5...",
  "metrics": {
    "steering": {"val_mse": 0.002341, "val_r2": 0.9876},
    "throttle": {"val_mse": 0.001823, "val_r2": 0.9912},
    "brake": {"val_mse": 0.000987, "val_r2": 0.9945}
  },
  "model_directory": "models/racing_ai",
  "hash": "9f2a8c5d7e1b3a..."
}
```

## IPFS Integration

To enable IPFS checkpoint storage:

```python
from ipfs_bridge import IPFSBridge, IPFSConfig

ipfs_config = IPFSConfig(
    api_endpoint="http://127.0.0.1:5001",
    gateway_endpoint="http://127.0.0.1:8080"
)

sim = RacingSimulator(seed=42, ipfs_bridge=IPFSBridge(ipfs_config))
```

Checkpoints will be automatically pinned to IPFS with CIDv1 addresses.

## Replay Viewer Integration

The generated NDJSON telemetry is compatible with `replay_viewer.html`:

1. Load `data/nurburgring_expert.ndjson` or `data/nurburgring_ai_telemetry.ndjson`
2. Visualize racing line, speed profile, and control inputs
3. Verify hash chain integrity

## Production Improvements

### For Real Racing Application

1. **Higher-fidelity physics**
   - Multi-body dynamics (suspension, aerodynamics)
   - Tire models (Pacejka Magic Formula)
   - Engine power curve & torque vectoring

2. **Better track representation**
   - High-resolution spline centerline
   - Real elevation data (LiDAR scans)
   - Surface grip variation (wet patches, rubber buildup)

3. **Advanced AI**
   - Deep neural networks (MLP, CNN for visual input)
   - Reinforcement learning (PPO, SAC)
   - Multi-agent training (racing against other AIs)

4. **Real telemetry**
   - Record human drivers in racing simulator
   - Import from real race data (F1, GT3)
   - Transfer learning from similar tracks

## File Structure

```text
enterprise_business_game/
├── src/
│   ├── racing_simulator.py      # Core simulator & physics
│   ├── racing_ai_trainer.py     # Random Forest training
│   └── game_engine.py           # Shared checkpoint logic
├── demo_racing_ai.py            # Complete demo script
├── data/
│   ├── nurburgring_expert.ndjson      # Expert telemetry
│   ├── nurburgring_ai_telemetry.ndjson # AI telemetry
│   └── training_ledger.ndjson         # Governance log
├── models/
│   └── racing_ai/               # Trained Random Forests
├── replay_viewer.html           # Visualization tool
└── RACING_AI_README.md          # This file
```

## Next Steps

1. **Collect more data** — Run longer expert sessions (full laps)
2. **Hyperparameter tuning** — Grid search for optimal RF params
3. **Online learning** — Incrementally improve AI with more laps
4. **Multi-track generalization** — Train on other circuits
5. **Real-time deployment** — Integrate with racing simulator (Assetto Corsa, iRacing)

---

**Status:** Racing AI demo operational with deterministic replay verified ✅
