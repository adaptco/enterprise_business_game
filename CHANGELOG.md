# Changelog

All notable changes to the Racing AI Simulator project.

## [0.3.0] - 2026-02-03

### Added

- **ML-Agents 4.0 tensor integration** (`CarAgent.cs`, 12-float deterministic schema)
- **PhysicsValidationSideChannel** (Unity↔Python RCVD validation at 1000+ FPS)
- **Python PhysicsValidationChannel** (`physics_validation_channel.py` → validated tensor)
- **Production PPO config** (`ppo_car.yaml`: 512×3 net, 40k buffer, 10M steps)
- **Pit stop time penalty** (25s realistic F1 pit, `step_with_pit()` method)
- **Pit urgency heuristic** (`pit_urgency()` for RL strategy learning)
- **RL observation vector** (`get_rl_observation()` 8-float normalized)

### Changed

- Replaced JSON socket bridge → native ML-Agents tensors (2μs vs 200μs latency)
- PhysicsAgentInput now validates ALL training observations (slip/grip/lat_accel)
- `VehicleState` extended with tire_wear, fuel, weather fields

### Stats

- **16→64 parallel env scaling ready**
- **100% physics-legal observations** (friction ellipse, slip limits enforced)
- **Audit-ready**: JSONL log captures violations for Code Sight entropy
- **21 unit tests passing**

---

## [0.2.0] - 2026-02-03

### Added

- **Tire degradation system** (SOFT/MEDIUM/HARD compounds)
- **Fuel consumption** with mass penalty (2% at full load)
- **Dynamic weather** (rain transitions, grip 0.6-1.2)
- **TireState, FuelState, WeatherState** dataclasses
- **Pit stop mechanics** (`pit_stop()` instant, `trigger_pit_entry()` with timer)

### Changed

- `DeterministicVehiclePhysics.step()` now incorporates tire wear (+0.0001/tick base)
- `RacingSimulator.step()` updates weather and passes to physics
- `create_checkpoint()` includes degradation state in hash

### Fixed

- Array shape mismatch in `_generate_track_geometry()` (11→10 elements)
- VehicleState dataclass field ordering (defaults after non-defaults)

---

## [0.1.0] - 2026-01-15

### Added

- Initial RacingSimulator with Nürburgring track
- DeterministicVehiclePhysics with Olley RCVD model
- VehicleState and ControlInput dataclasses
- Checkpoint system with SHA-256 state hashing
- Random Forest trainer integration
