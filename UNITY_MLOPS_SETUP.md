# UNITY MLOps Setup Guide

This guide documents how to run `mlops_unity_pipeline.py` as a one-off training job and as a 24/7 scheduled service, with environment strategy, deployment patterns, monitoring, and model governance.

## 1) Prerequisites

### Unity and ML-Agents versions

- Unity Editor: **2022.3 LTS** (recommended for stable CI/headless builds).
- Unity ML-Agents package (`com.unity.ml-agents`): **2.3.x**.
- Python `mlagents` package: **match major/minor with Unity package** (for example 1.0.0 if your pipeline is pinned there).

### Python dependencies

Install in a dedicated virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install mlagents==1.0.0 pyyaml croniter
```

### GCP / Vertex AI requirements

- A GCP project with billing enabled.
- Vertex AI API enabled.
- Service account with at least:
  - `roles/aiplatform.user`
  - `roles/storage.objectAdmin` (or a tighter bucket-scoped role)
  - `roles/logging.logWriter`
- `gcloud` authenticated in your runtime:

```bash
gcloud auth application-default login
gcloud config set project <YOUR_PROJECT_ID>
```

- Artifact bucket for model files and metadata (for example `gs://<project>-mlops-unity-models`).

## 2) Environments

### local/dev

- Purpose: rapid iteration, smoke tests, and debugging pipeline logic.
- Typical runtime: local workstation with Unity installed.
- Recommended defaults:
  - small `max_steps`
  - 1-4 parallel envs
  - local TensorBoard logs under `./runs/`

### staging

- Purpose: release-candidate validation in cloud-like conditions.
- Typical runtime: dedicated VM/node pool with stable dependencies.
- Recommended defaults:
  - production-like container image
  - production-like cron/scheduler config
  - webhook alerts enabled to engineering channels

### production

- Purpose: continuous training and promotion-ready model output.
- Typical runtime: managed Kubernetes (GKE) or equivalent.
- Recommended defaults:
  - pinned image digest (not just tag)
  - strict resource requests/limits
  - durable storage + log shipping
  - promotion controls for model registry

## 3) Deployment Paths

### Docker image build and run

```bash
# Build
DOCKER_IMAGE=unity-mlops:latest
docker build -t "$DOCKER_IMAGE" .

# Run single training container
docker run --rm \
  -e GOOGLE_CLOUD_PROJECT=<YOUR_PROJECT_ID> \
  -e VERTEX_REGION=us-central1 \
  -e WEBHOOK_URL=<OPTIONAL_WEBHOOK> \
  -v "$PWD":/workspace \
  "$DOCKER_IMAGE" \
  python scripts/single_job_test.py
```

### Kubernetes cron or long-running scheduler deployment

- **CronJob pattern**: good for nightly or hourly retraining with deterministic windows.
- **Long-running Deployment pattern**: good for high-frequency queue/schedule execution (24/7 daemon loop).

Recommended mapping:

- `scripts/single_job_test.py` -> K8s `Job` or `CronJob`.
- `scripts/scheduler_24x7.py` -> K8s `Deployment` with `restartPolicy: Always`.

## 4) Monitoring and Operations

### TensorBoard log locations

- Local/dev: `./runs/<job_id>/`.
- Containerized: mounted path such as `/workspace/runs/<job_id>/`.
- Kubernetes: PVC-backed path such as `/mnt/training-logs/runs/<job_id>/`.

Run TensorBoard:

```bash
tensorboard --logdir ./runs --port 6006 --bind_all
```

### Webhook notifications

Use `WEBHOOK_URL` for lifecycle notifications:

- schedule started
- job started
- job completed
- job failed

Payload should include `job_id`, `asset_id`, `model_version`, and failure context.

### Failure recovery and restart behavior

- Single-job execution should fail fast and return non-zero exit code.
- Scheduler should catch per-job failures, emit webhook notification, and continue future schedules.
- In Kubernetes:
  - `Job`/`CronJob`: use `backoffLimit` (for example 2-3 retries).
  - long-running scheduler `Deployment`: use liveness/readiness probes and `restartPolicy: Always`.
- Persist checkpoints/model artifacts frequently so resumed runs do not restart from zero.

## 5) Model Governance

### Versioning format

Use immutable, sortable model versions:

- `unity-<asset_name>-<YYYYMMDD>-<git_sha>-v<run_number>`
- Example: `unity-navigationagent-20260222-a1b2c3d-v004`

### Registry promotion criteria

Promote staging -> production only when all criteria pass:

- reward/regret thresholds met against baseline
- no regression in safety or constraint metrics
- reproducibility check succeeds (same config + seed tolerance)
- evaluation report and changelog linked to registry metadata

### Rollback procedure

1. Identify last known-good production model version in Vertex AI registry.
2. Re-point serving/deployment alias (or traffic split) to that version.
3. Freeze further promotion until root cause analysis is complete.
4. Open incident record with failed version, metrics, and corrective action.

## 6) Copy-paste Scripts

Create these helper scripts in `scripts/` so they can be run directly or from containers/jobs.

### Single job test script

```python
# scripts/single_job_test.py
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
```

Run:

```bash
python scripts/single_job_test.py
```

### 24/7 scheduler script

```python
# scripts/scheduler_24x7.py
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
```

Run:

```bash
python scripts/scheduler_24x7.py
```
