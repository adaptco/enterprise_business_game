import asyncio
from mlops_unity_pipeline import (
    RLTrainingConfig,
    TrainingSchedule,
    TrainingScheduler,
    UnityAssetSpec,
    UnityMLOpsOrchestrator,
)


async def run_forever() -> None:
    orchestrator = UnityMLOpsOrchestrator()
    scheduler = TrainingScheduler(orchestrator)

    nightly_asset = UnityAssetSpec(
        asset_id="nightly-001",
        name="NavigationAgent",
        asset_type="behavior",
        description="Nightly retraining for navigation behavior",
    )

    nightly_config = RLTrainingConfig(
        algorithm="PPO",
        max_steps=1_000_000,
        num_envs=16,
        time_scale=20.0,
    )

    nightly_schedule = TrainingSchedule(
        schedule_id="nightly-navigation-training",
        cron_expression="0 2 * * *",
        asset_specs=[nightly_asset],
        rl_config=nightly_config,
        enabled=True,
    )

    scheduler.add_schedule(nightly_schedule)
    await scheduler.run_forever()


if __name__ == "__main__":
    asyncio.run(run_forever())
