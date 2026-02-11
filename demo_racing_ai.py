"""
Nürburgring AI Racing Demo
Complete workflow: Expert recording → Training → AI racing → Replay verification
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from racing_simulator import RacingSimulator, ControlInput, TrackSection
from racing_ai_trainer import (
    TrainingDataLoader,
    DeterministicRandomForest,
    create_training_ledger_entry
)
import numpy as np
import json


def expert_driver_heuristic(state_dict) -> ControlInput:
    """
    Simple heuristic "expert" driver for demonstration.
    In production, this would be replaced by human telemetry.
    """
    curvature = state_dict['current_curvature']
    speed = state_dict['speed']
    upcoming_curves = state_dict['upcoming_curvature']
    section = state_dict['current_section']
    
    # Target speed based on curvature
    if abs(curvature) < 0.01:
        # Straight
        target_speed = 80.0  # m/s (~288 km/h)
    elif abs(curvature) < 0.03:
        # Fast corner
        target_speed = 50.0  # m/s (~180 km/h)
    else:
        # Tight corner
        target_speed = 30.0  # m/s (~108 km/h)
    
    # Look ahead for braking
    max_upcoming = max([abs(c) for c in upcoming_curves])
    if max_upcoming > 0.04:
        target_speed = min(target_speed, 25.0)
    
    # Steering (proportional to curvature)
    steering = -curvature * 15.0  # Gain factor
    steering = np.clip(steering, -1.0, 1.0)
    
    # Throttle/brake control
    speed_error = target_speed - speed
    
    if speed_error > 5.0:
        throttle = 1.0
        brake = 0.0
    elif speed_error < -5.0:
        throttle = 0.0
        brake = min(abs(speed_error) / 20.0, 1.0)
    else:
        throttle = max(0.0, speed_error / 10.0)
        brake = 0.0
    
    return ControlInput(
        steering_command=float(steering),
        throttle_command=float(throttle),
        brake_command=float(brake)
    )


def demo_expert_recording():
    """Phase 1: Record expert demonstrations."""
    print("\n" + "="*60)
    print("  PHASE 1: Expert Demonstration Recording")
    print("="*60 + "\n")
    
    sim = RacingSimulator(seed=42)
    
    # Run for 10 seconds (600 ticks at 60Hz)
    num_ticks = 600
    
    print(f"🏁 Starting expert demonstration run...")
    print(f"   Duration: {num_ticks / 60:.1f} seconds ({num_ticks} ticks)\n")
    
    for tick in range(num_ticks):
        # Get current state
        track_data = sim.track.get_track_data(sim.track_progress)
        current_state = sim.get_current_state(track_data)
        state_dict = current_state.__dict__
        
        # Expert decides action
        control = expert_driver_heuristic(state_dict)
        
        # Step simulation
        new_state = sim.step(control)
        
        # Progress feedback
        if tick % 60 == 0:
            section_name = new_state.current_section.value
            print(f"  Tick {tick:4d}: {new_state.speed:5.1f} m/s | "
                  f"Progress: {new_state.track_progress*100:5.2f}% | "
                  f"Section: {section_name}")
    
    # Create checkpoint
    checkpoint = sim.create_checkpoint()
    print(f"\n✓ Expert run complete!")
    print(f"  - Final progress: {sim.track_progress*100:.2f}%")
    print(f"  - Checkpoint ID: {checkpoint['checkpoint_id']}")
    print(f"  - State hash: {checkpoint['canonical_sha256'][:16]}...")
    
    # Export training data
    training_file = sim.export_training_data("data/nurburgring_expert.ndjson")
    
    return training_file, checkpoint


def demo_train_ai(training_file: str):
    """Phase 2: Train Random Forest AI."""
    print("\n" + "="*60)
    print("  PHASE 2: Random Forest AI Training")
    print("="*60 + "\n")
    
    # Load data
    loader = TrainingDataLoader(training_file)
    loader.load()
    
    # Extract features
    X, y_dict = loader.extract_features()
    
    # Train Random Forest
    rf_ai = DeterministicRandomForest(
        seed=42,
        n_estimators=50,  # Reduced for demo speed
        max_depth=15
    )
    
    training_report = rf_ai.train(X, y_dict, test_size=0.2, validation_size=0.1)
    
    print(f"\n✅ Training complete!")
    print(f"  - Model version: {training_report['model_version']}")
    print(f"  - Lineage hash: {training_report['lineage_hash'][:16]}...")
    print(f"  - Duration: {training_report['training_duration']:.2f}s")
    
    # Save models
    rf_ai.save_models("models/racing_ai")
    
    # Create governance ledger entry
    ledger_entry = create_training_ledger_entry(
        training_file,
        training_report,
        "models/racing_ai"
    )
    
    # Append to ledger
    with open("data/training_ledger.ndjson", 'a') as f:
        f.write(json.dumps(ledger_entry) + '\n')
    
    print(f"\n✓ Appended to governance ledger")
    print(f"  - Entry hash: {ledger_entry['hash'][:16]}...")
    
    return rf_ai


def demo_ai_racing(rf_ai: DeterministicRandomForest):
    """Phase 3: AI autonomous racing."""
    print("\n" + "="*60)
    print("  PHASE 3: AI Autonomous Racing")
    print("="*60 + "\n")
    
    # Create new simulator (different seed to test generalization)
    sim = RacingSimulator(seed=99)
    
    print(f"🤖 AI driver taking control...")
    print(f"   Model version: {rf_ai.training_lineage['model_version']}\n")
    
    num_ticks = 600
    
    for tick in range(num_ticks):
        # Get current state
        track_data = sim.track.get_track_data(sim.track_progress)
        current_state = sim.get_current_state(track_data)
        state_dict = current_state.__dict__
        
        # AI predicts action
        predictions = rf_ai.predict(state_dict)
        
        control = ControlInput(
            steering_command=predictions['steering'],
            throttle_command=predictions['throttle'],
            brake_command=predictions['brake']
        )
        
        # Step simulation
        new_state = sim.step(control)
        
        # Progress feedback
        if tick % 60 == 0:
            section_name = new_state.current_section.value
            print(f"  Tick {tick:4d}: {new_state.speed:5.1f} m/s | "
                  f"Progress: {new_state.track_progress*100:5.2f}% | "
                  f"Section: {section_name} | "
                  f"Throttle: {control.throttle_command:.2f}")
    
    # Create checkpoint
    checkpoint = sim.create_checkpoint()
    print(f"\n✓ AI run complete!")
    print(f"  - Final progress: {sim.track_progress*100:.2f}%")
    print(f"  - Checkpoint ID: {checkpoint['checkpoint_id']}")
    print(f"  - State hash: {checkpoint['canonical_sha256'][:16]}...")
    
    # Export AI telemetry
    ai_telemetry_file = sim.export_training_data("data/nurburgring_ai_telemetry.ndjson")
    
    return ai_telemetry_file, checkpoint


def demo_replay_verification():
    """Phase 4: Verify deterministic replay."""
    print("\n" + "="*60)
    print("  PHASE 4: Deterministic Replay Verification")
    print("="*60 + "\n")
    
    print("🔁 Replaying expert run with same seed...")
    
    # Run 1: Original
    sim1 = RacingSimulator(seed=42)
    for tick in range(100):
        track_data = sim1.track.get_track_data(sim1.track_progress)
        state = sim1.get_current_state(track_data)
        control = expert_driver_heuristic(state.__dict__)
        sim1.step(control)
    
    checkpoint1 = sim1.create_checkpoint()
    hash1 = checkpoint1['canonical_sha256']
    
    # Run 2: Replay
    sim2 = RacingSimulator(seed=42)
    for tick in range(100):
        track_data = sim2.track.get_track_data(sim2.track_progress)
        state = sim2.get_current_state(track_data)
        control = expert_driver_heuristic(state.__dict__)
        sim2.step(control)
    
    checkpoint2 = sim2.create_checkpoint()
    hash2 = checkpoint2['canonical_sha256']
    
    # Verify
    if hash1 == hash2:
        print(f"✅ REPLAY VERIFIED!")
        print(f"   Run 1 hash: {hash1}")
        print(f"   Run 2 hash: {hash2}")
        print(f"   Determinism: CONFIRMED")
    else:
        print(f"❌ REPLAY FAILED!")
        print(f"   Run 1 hash: {hash1}")
        print(f"   Run 2 hash: {hash2}")
        print(f"   Determinism: BROKEN")


def main():
    """Run complete demo workflow."""
    print("\n" + "="*60)
    print("  🏎️  Nürburgring AI Racing Simulator")
    print("  Deterministic Training & Replay with SSOT Integration")
    print("="*60)
    
    # Ensure data directory exists
    Path("data").mkdir(exist_ok=True)
    
    # Phase 1: Expert recording
    training_file, expert_checkpoint = demo_expert_recording()
    
    # Phase 2: Train AI
    rf_ai = demo_train_ai(training_file)
    
    # Phase 3: AI racing
    ai_telemetry, ai_checkpoint = demo_ai_racing(rf_ai)
    
    # Phase 4: Replay verification
    demo_replay_verification()
    
    print("\n" + "="*60)
    print("  ✅ Demo Complete!")
    print("="*60)
    print(f"\nGenerated files:")
    print(f"  - Training data: {training_file}")
    print(f"  - AI telemetry: {ai_telemetry}")
    print(f"  - Models: models/racing_ai/")
    print(f"  - Governance ledger: data/training_ledger.ndjson")
    print(f"\nNext steps:")
    print(f"  1. Visualize with replay viewer: replay_viewer.html")
    print(f"  2. Train longer: Increase num_ticks for more data")
    print(f"  3. Integrate IPFS: Add ipfs_bridge to RacingSimulator")
    print(f"  4. Deploy AI: Load model and run autonomous laps\n")


if __name__ == "__main__":
    main()
