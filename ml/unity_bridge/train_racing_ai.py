"""
Racing AI Training Launcher with Unity ML-Agents Integration.

This script launches PPO training with physics validation side channel.

Usage:
    python -m ml.unity_bridge.train_racing_ai --config ml/configs/ppo_car.yaml --run-id racing-v1

Or with mlagents-learn directly:
    mlagents-learn ml/configs/ppo_car.yaml --run-id=racing-v1 --num-envs=16
"""

import argparse
import logging
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def check_mlagents_installed() -> bool:
    """Check if mlagents package is available."""
    try:
        from mlagents_envs.environment import UnityEnvironment
        from mlagents.trainers.trainer_controller import TrainerController
        return True
    except ImportError:
        return False


def launch_training(
    config_path: str,
    run_id: str,
    env_path: str=None,
    num_envs: int=16,
    resume: bool=False,
    force: bool=False
):
    """
    Launch ML-Agents training with physics validation.
    
    Args:
        config_path: Path to PPO config YAML
        run_id: Training run identifier
        env_path: Path to Unity build (None = editor)
        num_envs: Number of parallel environments
        resume: Resume from checkpoint
        force: Overwrite existing run
    """
    if not check_mlagents_installed():
        logger.error("mlagents package not installed. Install with:")
        logger.error("  pip install mlagents==1.0.0")
        return
    
    from mlagents_envs.environment import UnityEnvironment
    from mlagents_envs.side_channel.engine_configuration_channel import EngineConfigurationChannel
    from .physics_validation_channel import get_physics_channel
    
    logger.info(f"🏎️  Racing AI Training Launcher")
    logger.info(f"   Config: {config_path}")
    logger.info(f"   Run ID: {run_id}")
    logger.info(f"   Envs: {num_envs}")
    
    # Create side channels
    physics_channel = get_physics_channel(audit_log=f"results/{run_id}/physics_audit.log")
    engine_channel = EngineConfigurationChannel()
    
    # Configure environment
    env_kwargs = {
        "file_name": env_path,
        "worker_id": 0,
        "base_port": 5005,
        "side_channels": [physics_channel, engine_channel],
        "no_graphics": env_path is not None  # Headless for builds
    }
    
    logger.info("🔌 Connecting to Unity environment...")
    
    try:
        env = UnityEnvironment(**env_kwargs)
        
        # Set engine configuration for training
        engine_channel.set_configuration_parameters(
            width=640,
            height=480,
            quality_level=1,
            time_scale=20.0,  # 20x speed for training
            target_frame_rate=-1,
            capture_frame_rate=60
        )
        
        logger.info("✅ Unity environment connected")
        logger.info(f"   Behavior specs: {list(env.behavior_specs.keys())}")
        
        # Print physics channel status
        stats = physics_channel.get_stats()
        logger.info(f"📊 Physics channel active: {stats}")
        
        # Note: For full training, use mlagents-learn CLI
        logger.info("")
        logger.info("To start full PPO training, run:")
        logger.info(f"  mlagents-learn {config_path} --run-id={run_id} --num-envs={num_envs}")
        
        # Simple test loop
        logger.info("")
        logger.info("Running test episode...")
        
        env.reset()
        
        for step in range(100):
            # Get behavior name
            behavior_name = list(env.behavior_specs.keys())[0]
            decision_steps, terminal_steps = env.get_steps(behavior_name)
            
            if len(decision_steps) > 0:
                # Random actions for test
                import numpy as np
                action_spec = env.behavior_specs[behavior_name].action_spec
                n_agents = len(decision_steps)
                actions = np.random.uniform(-1, 1, (n_agents, action_spec.continuous_size))
                env.set_actions(behavior_name, actions)
            
            env.step()
            
            if step % 25 == 0:
                stats = physics_channel.get_stats()
                logger.info(f"   Step {step}: {stats['messages_processed']} physics validated")
        
        logger.info("✅ Test episode complete")
        
        env.close()
        
    except Exception as e:
        logger.error(f"❌ Failed to connect to Unity: {e}")
        logger.info("")
        logger.info("Make sure Unity Editor is running with ML-Agents scene loaded,")
        logger.info("or provide --env-path to a Unity build.")
        raise


def main():
    parser = argparse.ArgumentParser(description="Racing AI Training Launcher")
    parser.add_argument("--config", default="ml/configs/ppo_car.yaml", help="PPO config path")
    parser.add_argument("--run-id", default="racing-v1", help="Training run ID")
    parser.add_argument("--env-path", default=None, help="Path to Unity build (None = editor)")
    parser.add_argument("--num-envs", type=int, default=16, help="Parallel environments")
    parser.add_argument("--resume", action="store_true", help="Resume from checkpoint")
    parser.add_argument("--force", action="store_true", help="Overwrite existing run")
    
    args = parser.parse_args()
    
    launch_training(
        config_path=args.config,
        run_id=args.run_id,
        env_path=args.env_path,
        num_envs=args.num_envs,
        resume=args.resume,
        force=args.force
    )


if __name__ == "__main__":
    main()
