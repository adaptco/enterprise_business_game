# 🎯 Nord RF Driver — Quick Reference

## Contract Summary

### VehicleStateV1 (13 features)
```python
speed_mps, yaw_rate_rad_s,
track_progress_m, distance_to_center_m,
curvature_now_1pm, curvature_10m_ahead_1pm, curvature_30m_ahead_1pm,
grad_now,
dist_left_edge_m, dist_right_edge_m,
prev_steering_command, prev_throttle_command, prev_brake_command
```

### Training I/O

**Input:** `data/raw/expert.ndjson` (22 fields per row)  
**Output:** `data/models/*.joblib` + `model_metadata.json`  
**Config:** `training/configs/rf_default.yaml`

### RandomForestDriver API

```python
driver = RandomForestDriver.load_from_directory("data/models")
control = driver.tick(state_v1)  # Returns ControlCommand
```

## Commands

```bash
# Train
python training/train_random_forest.py \
  --data data/raw/expert.ndjson \
  --output-dir data/models

# Test driver
python agent_rf_driver/rf_agent.py  # Example usage
```

## File Map

```
✅ state/state_space.py              VehicleStateV1 dataclass
✅ data_collection/schema_*.json     Data contract (22 fields)
✅ training/train_random_forest.py   Full training pipeline
✅ training/configs/rf_default.yaml  Hyperparameters
✅ agent_rf_driver/rf_agent.py       RandomForestDriver.tick()
✅ README.md                          Complete docs
✅ requirements.txt                   Dependencies

🚧 env/vehicle_dynamics.py           TODO: Physics
🚧 env/track.py                      TODO: Nürburgring geometry
🚧 data_collection/expert_*.py       TODO: Record expert data
```

## Expansion Path

**v1:** 13 features → Competent laps  
**v2:** +4 wheel speeds → Better traction control  
**v3:** +5 curvature horizons → Smoother entry  
**v4:** +3 engine/torque → Gearshift optimization  

## Status

**Production-ready components:** ✅ State, schema, training, driver  
**Your task:** Implement `env/` and `data_collection/` (~300 LOC)  
**Ready to:** Train RF models and verify R² > 0.98  
