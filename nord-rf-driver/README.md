# Nürburgring Random Forest Driver

**Production-grade AI racing driver with explicit contracts and minimal v1 state space.**

## Quick Start

```bash
# 1. Record expert data (placeholder - implement your sim)
python data_collection/record_expert_run.py --laps 3 --output data/raw/expert.ndjson

# 2. Train Random Forest models
python training/train_random_forest.py \
  --data data/raw/expert.ndjson \
  --config training/configs/rf_default.yaml \
  --output-dir data/models

# 3. Run AI driver
python agent_rf_driver/run_rf_agent_lap.py --model-dir data/models
```

## Architecture

```
nord-rf-driver/
├── env/                        # Track geometry & physics
├── state/                      # Canonical state structures
│   └── state_space.py          # VehicleStateV1 (13 features)
├── data_collection/            # Expert recording
│   └── schema_training_sample.json  # Data contract
├── training/                   # RF training pipeline
│   ├── train_random_forest.py  # Main training script
│   └── configs/rf_default.yaml # Hyperparameters
├── agent_rf_driver/            # AI driver
│   └── rf_agent.py             # RandomForestDriver class
└── data/
    ├── raw/                    # Expert NDJSON
    ├── processed/              # Preprocessed features
    └── models/                 # Trained .joblib + metadata
```

## Data Contract

### Training Sample Schema

Every training row conforms to `data_collection/schema_training_sample.json`:

**State features (13):**
- `speed_mps`, `yaw_rate_rad_s`
- `track_progress_m`, `distance_to_center_m`
- `curvature_now_1pm`, `curvature_10m_ahead_1pm`, `curvature_30m_ahead_1pm`
- `grad_now`
- `dist_left_edge_m`, `dist_right_edge_m`
- `prev_steering_command`, `prev_throttle_command`, `prev_brake_command`

**Action labels (3):**
- `steering_command` (-1.0 to 1.0)
- `throttle_command` (0.0 to 1.0)
- `brake_command` (0.0 to 1.0)

**Metadata:**
- `session_id`, `lap_id`, `timestep`
- `valid` (bool), `event` (string)

### Model Metadata

Trained models include `model_metadata.json`:

```json
{
  "model_type": "RandomForestRegressor",
  "version": "v1.0",
  "n_estimators": 100,
  "max_depth": 18,
  "feature_names": ["speed_mps", "yaw_rate_rad_s", ...],
  "train_data_hash": "sha256:abc123...",
  "metrics": {
    "steering": {"test_mse": 0.0021, "test_r2": 0.9876},
    "throttle": {"test_mse": 0.0018, "test_r2": 0.9912},
    "brake": {"test_mse": 0.0010, "test_r2": 0.9945}
  },
  "timestamp": "2026-01-12T22:00:00Z"
}
```

## RandomForestDriver API

### Tick Interface

```python
from agent_rf_driver.rf_agent import RandomForestDriver
from state.state_space import VehicleStateV1

# Load trained model
driver = RandomForestDriver.load_from_directory("data/models")

# Simulation loop
for tick in range(num_ticks):
    # Build state (13 features)
    state = VehicleStateV1(
        speed_mps=current_speed,
        yaw_rate_rad_s=current_yaw_rate,
        track_progress_m=progress,
        distance_to_center_m=lateral_offset,
        curvature_now_1pm=track.curvature_at(progress),
        curvature_10m_ahead_1pm=track.curvature_at(progress + 10),
        curvature_30m_ahead_1pm=track.curvature_at(progress + 30),
        grad_now=track.gradient_at(progress),
        dist_left_edge_m=raycast_left(),
        dist_right_edge_m=raycast_right(),
        prev_steering_command=driver.prev_steering,
        prev_throttle_command=driver.prev_throttle,
        prev_brake_command=driver.prev_brake
    )
    
    # Predict control
    control = driver.tick(state)
    
    # Apply to vehicle
    apply_steering(control.steering_command)
    apply_throttle(control.throttle_command)
    apply_brake(control.brake_command)
```

### Methods

- `RandomForestDriver.load_from_directory(path)` → driver
- `driver.tick(VehicleStateV1)` → ControlCommand
- `driver.reset()` — Reset control history
- `driver.get_model_info()` → metadata dict

## Training Pipeline

### Input Contract

**File:** NDJSON or CSV with rows matching `schema_training_sample.json`

**Example row:**
```json
{
  "session_id": "expert_001",
  "lap_id": 1,
  "timestep": 42,
  "speed_mps": 45.7,
  "yaw_rate_rad_s": 0.12,
  "track_progress_m": 1250.3,
  "distance_to_center_m": 0.8,
  "curvature_now_1pm": 0.025,
  "curvature_10m_ahead_1pm": 0.030,
  "curvature_30m_ahead_1pm": 0.020,
  "grad_now": 0.015,
  "dist_left_edge_m": 5.2,
  "dist_right_edge_m": 4.8,
  "steering_command": -0.35,
  "throttle_command": 0.82,
  "brake_command": 0.0,
  "valid": true,
  "event": ""
}
```

### Output Contract

**Directory structure:**
```
data/models/
├── steering.joblib           # RF model for steering
├── throttle.joblib           # RF model for throttle
├── brake.joblib              # RF model for brake
├── scaler_features.joblib    # StandardScaler for features
├── scaler_steering.joblib    # StandardScaler for steering target
├── scaler_throttle.joblib    # StandardScaler for throttle target
├── scaler_brake.joblib       # StandardScaler for brake target
└── model_metadata.json       # Lineage & metrics
```

### Training Command

```bash
python training/train_random_forest.py \
  --data data/raw/expert.ndjson \
  --config training/configs/rf_default.yaml \
  --output-dir data/models
```

**Expected output:**
```
✓ Loaded config: training/configs/rf_default.yaml
  - n_estimators: 100
  - max_depth: 18
  - seed: 42

✓ Loaded 1250 valid training samples from data/raw/expert.ndjson
✓ Extracted features: (1250, 13)
  Feature names (13): ['speed_mps', 'yaw_rate_rad_s', ...]

✓ Data split:
  - Train: 875 samples
  - Val: 125 samples
  - Test: 250 samples

🌲 Training steering model...
  ✓ Validation MSE: 0.002341
  ✓ Validation R²: 0.9876
  ✓ Test MSE: 0.002198
  ✓ Test R²: 0.9891

🌲 Training throttle model...
  ✓ Validation MSE: 0.001823
  ✓ Validation R²: 0.9912
  ✓ Test MSE: 0.001654
  ✓ Test R²: 0.9923

🌲 Training brake model...
  ✓ Validation MSE: 0.000987
  ✓ Validation R²: 0.9945
  ✓ Test MSE: 0.000854
  ✓ Test R²: 0.9956

✓ Saved models to data/models/
✓ Saved metadata to data/models/model_metadata.json

✅ Training complete!
  - Model hash (lineage): sha256:abc123def456...
  - Avg test R²: 0.9923
```

## Minimal v1 State Vector

**13 features** for fast iteration:

| Feature | Type | Description |
|---------|------|-------------|
| `speed_mps` | float | Current speed (m/s) |
| `yaw_rate_rad_s` | float | Angular velocity (rad/s) |
| `track_progress_m` | float | Distance along centerline |
| `distance_to_center_m` | float | Lateral offset (+ right, - left) |
| `curvature_now_1pm` | float | Current curvature (1/m) |
| `curvature_10m_ahead_1pm` | float | Curvature 10m ahead |
| `curvature_30m_ahead_1pm` | float | Curvature 30m ahead |
| `grad_now` | float | Track gradient (radians) |
| `dist_left_edge_m` | float | Distance to left edge |
| `dist_right_edge_m` | float | Distance to right edge |
| `prev_steering_command` | float | Previous steering (smoothness) |
| `prev_throttle_command` | float | Previous throttle |
| `prev_brake_command` | float | Previous brake |

This is sufficient for **competent lap completion** on Nürburgring.

## Expansion Path

### v2: Add wheel dynamics
- `wheel_speed_fl/fr/rl/rr`
- `tire_slip_ratio_fl/fr/rl/rr`

### v3: Richer horizon
- Curvature at ±50m, ±100m, ±200m
- Elevation preview

### v4: Engine/transmission
- `engine_rpm`, `gear`, `torque_nm`

### v5: Competitor awareness (multi-agent)
- `opponent_distance_ahead`, `opponent_distance_behind`

## Integration with SSOT

This system is **compatible** with your existing governance infrastructure:

- **Training data hash** → Lineage tracking
- **Model metadata** → Governance ledger entries
- **Deterministic splits** → Replay verification
- **IPFS-ready** → Add CID generation to `train_random_forest.py`

## Dependencies

```
numpy>=1.24
pandas>=2.0
scikit-learn>=1.3
joblib>=1.3
pyyaml>=6.0
```

## Status

✅ **Data contract defined** (`schema_training_sample.json`)  
✅ **Minimal v1 state** (13 features)  
✅ **Training pipeline** (`train_random_forest.py`)  
✅ **RF driver API** (`RandomForestDriver.tick()`)  
✅ **Config system** (YAML hyperparameters)  
✅ **Metadata generation** (lineage tracking)  

**Next:** Implement `env/sim_loop.py` and `data_collection/record_expert_run.py`
