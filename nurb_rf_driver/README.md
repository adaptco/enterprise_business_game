# Nürburgring RF Driver - Sim Env Contract v1

**Deterministic simulation environment for Random Forest driver training**

---

## 🎯 What This Is

Sim Env Contract v1 establishes the **foundational runtime** for the Nürburgring RF driver project:

- **Deterministic tick loop** with hash tensor chain for replay verification
- **Fixed-point integer coordinates** ("Back to the Future" time-indexed state machine)
- **Canonical v1 feature vector** (10 features) with stable ordering
- **NDJSON telemetry logging** for supervised learning datasets

This is the **minimal buildable spine** to collect expert data and train the first Random Forest model.

---

## 📂 Core Files

| File | Purpose |
|------|---------|
| `env/sim_env.py` | Deterministic simulation loop with VehicleState + CoordInt |
| `state/feature_extractor.py` | Extract canonical v1 10-feature vector |
| `telemetry/ndjson_logger.py` | Log training samples with stable key ordering |
| `state/feature_config.v1.json` | Feature metadata and normalization specs |
| `telemetry/schemas/training_sample.v1.schema.json` | NDJSON training sample schema |

---

## ⚡ Quick Start

### Run Demonstration

```bash
cd nurb_rf_driver
python demo_sim_env.py
```

**Demos**:
1. **Deterministic Tick Loop** - Shows hash chain verification
2. **NDJSON Logging** - Creates `data/demo_run.ndjson` with stable ordering
3. **Determinism Verification** - Replays simulation and verifies identical hashes

---

## 🔢 V1 Feature Vector (Canonical Order)

| Index | Feature | Unit | Description |
|-------|---------|------|-------------|
| 0 | `speed_mps` | m/s | Current vehicle speed |
| 1 | `yaw_rate_rps` | rad/s | Yaw rate |
| 2 | `steering_angle_norm` | [-1,1] | Steering angle |
| 3 | `track_progress` | [0,1] | Track completion ratio |
| 4 | `dist_to_centerline_m` | m | Lateral offset (negative = left) |
| 5 | `heading_error_rad` | rad | Heading vs track tangent |
| 6 | `curvature_now` | 1/m | Current track curvature |
| 7 | `curvature_ahead_10m` | 1/m | Curvature 10m ahead |
| 8 | `curvature_ahead_30m` | 1/m | Curvature 30m ahead |
| 9 | `curvature_ahead_60m` | 1/m | Curvature 60m ahead |

**Targets**: `steering_command`, `throttle_command`, `brake_command` (all normalized)

---

## 🧬 Hash Tensor Chain

Each tick produces a **deterministic hash chain**:

```
tick_0: state_hash_0 → chain_hash_0
tick_1: state_hash_1 + chain_hash_0 → chain_hash_1
tick_2: state_hash_2 + chain_hash_1 → chain_hash_2
...
```

**Verification**: Re-run with same seed → identical chain_hash sequence

---

## 📐 Integer Coordinate System

**Fixed-point quantization** for determinism:

- Position: `x_i = round(x_m * 1000)` (millimeters)
- Angles: `θ_i = round(θ_rad * 1_000_000)` (microradians)
- **Origin rule**: `[0,0,0] → [0,0,1]` (basis identity, Han as root)

**Seed generation**:
```
seed_u64 = SHA256("Han|run_id|tick|namespace")[0:8]
```

---

## 📝 NDJSON Format

**Training samples** logged as newline-delimited JSON:

```json
{"tick":1,"timestamp_ms":20,"lap_id":"lap_001","valid":true,"features":{"speed_mps":1.5,"yaw_rate_rps":0.025,...},"targets":{"steering_command":-0.1,"throttle_command":0.5,"brake_command":0.0},"meta":{"coord_int":[0,0,1],"seed_u64":12345,"state_hash":"3eb838...","chain_hash":"7c2a1b..."}}
```

**Key ordering is deterministic** - replay produces byte-for-byte identical logs.

---

## 🚀 Next Steps

### Immediate (Milestone 1 completion):
1. **Implement vehicle dynamics** - Replace placeholder physics with proper model
2. **Build Nordschleife track model** - JSON track definition with spline curves
3. **Add curvature extraction** - Lookahead queries (10m, 30m, 60m)

### Milestone 2 (Data Collection):
1. **Expert controller** - Record human/algorithm laps
2. **Collect training dataset** - 50+ laps as NDJSON
3. **Validate determinism** - Replay verification on full laps

### Milestone 3 (RF Training):
1. **Dataset I/O** - Load NDJSON into NumPy arrays
2. **Train RandomForestRegressor** - Scikit-learn pipeline
3. **Model registry** - Save/version trained models

---

## 🏛️ Architecture Principles

✅ **Deterministic**: Same seed → identical outputs  
✅ **Auditable**: Hash chain enables replay verification  
✅ **Minimal**: 10 features, no "telemetry hell"  
✅ **Buildable**: Runnable demo on day 1  
✅ **Grounded**: Root identity ("Han") anchors lineage  

---

## 📊 Example Output

```
Sim Env Contract v1 - Deterministic Tick Loop Demo
==========================================================

✅ Initialized SimEnv
   - Seed: 42
   - Run ID: demo_001
   - Root Identity: Han
   - Tick rate: 50 Hz

Tick   1:
  Speed:   1.50 m/s | Position: (     0.03,      0.02)
  Coord: (30, 20, 0) | Seed: a7f1
  Hash: 3eb838e5d4d256a4... | Chain: 7c2a1b5e4d3f6a8c...

✅ DETERMINISM VERIFIED: Hash chains are identical!
   All 50 chain hashes match.
```

---

## 📜 License

Built for the **Qube-Axiomatic-01** universe. Part of the Agent Q pedagogical framework.

**"Saintly honesty, hardware-attested."** 🏁
