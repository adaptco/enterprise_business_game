# Unity ML-Agents Integration Guide

Production-ready integration for Racing AI with Physics Validation.

## Architecture

```text
┌─────────────────────────────────────────────────────────────────┐
│                        PYTHON (Trainer)                         │
├─────────────────────────────────────────────────────────────────┤
│  RacingSimulator  →  PhysicsValidationChannel  →  PPO Trainer  │
│                              ↕                                   │
│                     gRPC / SideChannel                          │
│                              ↕                                   │
├─────────────────────────────────────────────────────────────────┤
│  CarAgent.cs  →  PhysicsValidationSideChannel  →  Unity Physics │
├─────────────────────────────────────────────────────────────────┤
│                        UNITY (Environment)                       │
└─────────────────────────────────────────────────────────────────┘
```

## Files Created

| File                                                   | Description                      |
|--------------------------------------------------------|----------------------------------|
| `ml/unity_bridge/physics_validation_channel.py`        | SideChannel for physics validation |
| `ml/unity_bridge/train_racing_ai.py`                   | Training launcher                |
| `ml/configs/ppo_car.yaml`                              | PPO hyperparameters              |
| `unity_assets/Scripts/CarAgent.cs`                     | ML-Agents agent                  |
| `unity_assets/Scripts/PhysicsValidationSideChannel.cs` | C# side channel                  |

## Tensor Observation Schema (12 floats)

| Index | Field | Range | Source |
| --- | --- | --- | --- |
| 0-2 | velocity_xyz | [-80,80]/80 | rb.velocity |
| 3-5 | angular_vel_xyz | [-5,5]/5 | rb.angularVelocity |
| 6 | grip_mu | [0.3,2.0]/2.0 | **validated** |
| 7 | lat_accel | [-15,15]/15 | **validated** |
| 8 | slip_front | [-0.5,0.5] | **validated** |
| 9 | slip_rear | [-0.5,0.5] | **validated** |
| 10 | throttle_history | [-1,1] | prev_action[0] |
| 11 | steer_history | [-1,1] | prev_action[1] |

## Quick Start

### 1. Install Dependencies

```bash
# Python
pip install mlagents==1.0.0 mlagents-envs==1.0.0 numpy

# Unity
# Open Package Manager → Add package from git URL:
# com.unity.ml-agents@release_21
```

### 2. Setup Unity Scene

1. Create empty GameObject, attach `CarAgent.cs`
2. Add `Behavior Parameters` component:
   - Behavior Name: `CarAgent`
   - Vector Observation Space: 12
   - Actions: Continuous, Size 2
3. Create car with `Rigidbody` and 4 `WheelCollider`s
4. Assign wheels to `CarAgent` inspector

### 3. Launch Training

**Terminal 1** (Python trainer):

```bash
mlagents-learn ml/configs/ppo_car.yaml --run-id=racing-v1 --num-envs=16
```

**Unity**: Press Play → Training begins automatically

### 4. Monitor Progress

```bash
tensorboard --logdir results
```

## Physics Validation Flow

1. **Unity** sends raw physics (16 floats) via SideChannel
2. **Python** validates using RCVD constraints:
   - Clip slip angles to [-0.5, 0.5]
   - Clip lateral accel to [-15, 15]
   - Apply grip penalty for excessive slip
3. **Python** returns validated tensor (4 floats)
4. **Unity** uses validated data in observations

## Training Tips

- **Start with 4 envs**, scale to 16+ once stable
- **Monitor `physics_audit.log`** for constraint violations
- **Checkpoint every 100k steps** with `--checkpoint-interval`
- **Use curriculum**: Start with straight track, add corners

## Expected Results

| Metric          | After 1M Steps | After 10M Steps |
|-----------------|----------------|-----------------|
| Lap Time        | ~4:00          | ~2:45           |
| Violations/Lap  | ~50            | <5              |
| Stability       | 70%            | 95%             |
