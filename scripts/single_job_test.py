import asyncio
from mlops_unity_pipeline import (
    RLTrainingConfig,
    TrainingJob,
    UnityAssetSpec,
    UnityMLOpsOrchestrator,
)


async def main() -> None:
    orchestrator = UnityMLOpsOrchestrator()

    asset = UnityAssetSpec(
        asset_id="test-001",
        name="SimpleAgent",
        asset_type="behavior",
        description="Reach target position",
    )

    config = RLTrainingConfig(
        algorithm="PPO",
        max_steps=100_000,
    )

    job = TrainingJob(
        job_id="single-job-test",
        asset_spec=asset,
        rl_config=config,
    )

    result = await orchestrator.execute_training_job(job)
    print(f"Training complete: {result.trained_model_path}")


if __name__ == "__main__":
    asyncio.run(main())
