from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import random
import traceback
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional

from croniter import croniter


LOGGER = logging.getLogger("mlops_unity_pipeline")
if not LOGGER.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s",
        )
    )
    LOGGER.addHandler(handler)
LOGGER.setLevel(logging.INFO)


@dataclass(frozen=True)
class UnityAssetSpec:
    asset_id: str
    name: str
    asset_type: str
    description: str
    observation_space: Dict[str, Any] = field(default_factory=dict)
    action_space: Dict[str, Any] = field(default_factory=dict)
    generation_hints: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RLTrainingConfig:
    algorithm: str = "PPO"
    max_steps: int = 1_000_000
    num_envs: int = 8
    time_scale: float = 20.0
    seed: int = 42
    learning_rate: float = 3e-4
    batch_size: int = 1024
    offline_dataset_path: Optional[str] = None
    extra_args: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TrainingJob:
    job_id: str
    asset_spec: UnityAssetSpec
    rl_config: RLTrainingConfig
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TrainingSchedule:
    schedule_id: str
    cron_expression: str
    asset_specs: List[UnityAssetSpec]
    rl_config: RLTrainingConfig
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TrainingResult:
    job_id: str
    status: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    trained_model_path: Optional[str] = None
    error: Optional[Dict[str, Any]] = None
    config_hash: Optional[str] = None
    artifacts: Dict[str, Any] = field(default_factory=dict)


class UnityMLOpsOrchestrator:
    """Executes codegen -> build -> train -> register flow for Unity ML jobs."""

    def __init__(
        self,
        workspace_root: str | Path = ".",
        max_retries: int = 3,
        base_backoff_seconds: float = 1.0,
    ) -> None:
        self.workspace_root = Path(workspace_root)
        self.max_retries = max_retries
        self.base_backoff_seconds = base_backoff_seconds

    async def execute_training_job(self, job: TrainingJob) -> TrainingResult:
        started_at = datetime.now(timezone.utc)
        config_hash = self._deterministic_config_hash(job)
        self._log("training_job_started", job_id=job.job_id, config_hash=config_hash)
        result = TrainingResult(
            job_id=job.job_id,
            status="running",
            started_at=started_at,
            config_hash=config_hash,
        )

        try:
            generated = await self._with_retries(
                lambda: self._code_generation_hook(job),
                operation="code_generation",
                job_id=job.job_id,
            )
            build_output = await self._with_retries(
                lambda: self._unity_build_hook(job, generated),
                operation="unity_build",
                job_id=job.job_id,
            )
            trained_model_path = await self._with_retries(
                lambda: self._ml_agents_training_hook(job, build_output),
                operation="mlagents_training",
                job_id=job.job_id,
            )
            registration = await self._with_retries(
                lambda: self._model_registration_hook(job, trained_model_path),
                operation="model_registration",
                job_id=job.job_id,
            )
            result.status = "succeeded"
            result.trained_model_path = trained_model_path
            result.artifacts = {
                "generated": generated,
                "build_output": build_output,
                "registration": registration,
            }
            self._log(
                "training_job_succeeded",
                job_id=job.job_id,
                trained_model_path=trained_model_path,
            )
        except Exception as exc:  # noqa: BLE001
            result.status = "failed"
            result.error = {
                "type": type(exc).__name__,
                "message": str(exc),
                "traceback": traceback.format_exc(),
            }
            self._log("training_job_failed", job_id=job.job_id, error=result.error)
        finally:
            result.finished_at = datetime.now(timezone.utc)

        return result

    async def _code_generation_hook(self, job: TrainingJob) -> Dict[str, Any]:
        await asyncio.sleep(0)
        script_path = self.workspace_root / "unity_assets" / f"{job.asset_spec.name}.cs"
        return {
            "script_path": str(script_path),
            "generator": "llm_hook",
            "asset_id": job.asset_spec.asset_id,
        }

    async def _unity_build_hook(self, job: TrainingJob, generated: Dict[str, Any]) -> Dict[str, Any]:
        await asyncio.sleep(0)
        build_path = self.workspace_root / "builds" / job.job_id
        return {
            "build_path": str(build_path),
            "target": "linux-headless",
            "source_script": generated.get("script_path"),
        }

    async def _ml_agents_training_hook(self, job: TrainingJob, build_output: Dict[str, Any]) -> str:
        await asyncio.sleep(0)
        model_dir = self.workspace_root / "checkpoints" / job.job_id
        model_path = model_dir / f"{job.asset_spec.name}.onnx"
        return str(model_path)

    async def _model_registration_hook(self, job: TrainingJob, trained_model_path: str) -> Dict[str, Any]:
        await asyncio.sleep(0)
        return {
            "registry": "vertex-ai",
            "model_uri": trained_model_path,
            "version": f"{job.job_id}-{int(datetime.now(timezone.utc).timestamp())}",
        }

    async def _with_retries(
        self,
        op: Callable[[], Awaitable[Any]],
        *,
        operation: str,
        job_id: str,
    ) -> Any:
        for attempt in range(1, self.max_retries + 1):
            try:
                self._log("operation_attempt", job_id=job_id, operation=operation, attempt=attempt)
                return await op()
            except Exception as exc:  # noqa: BLE001
                is_last = attempt == self.max_retries
                self._log(
                    "operation_failure",
                    job_id=job_id,
                    operation=operation,
                    attempt=attempt,
                    error=str(exc),
                    final_attempt=is_last,
                )
                if is_last:
                    raise
                backoff = self.base_backoff_seconds * (2 ** (attempt - 1))
                jitter = random.uniform(0.0, backoff / 4)
                await asyncio.sleep(backoff + jitter)

        raise RuntimeError(f"Unexpected retry policy failure for operation={operation}")

    def _deterministic_config_hash(self, job: TrainingJob) -> str:
        payload = {
            "job": asdict(job),
            "workspace_root": str(self.workspace_root.resolve()),
        }
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def _log(self, event: str, **fields: Any) -> None:
        payload = {
            "event": event,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **fields,
        }
        LOGGER.info(json.dumps(payload, sort_keys=True, default=str))


class TrainingScheduler:
    def __init__(self, orchestrator: UnityMLOpsOrchestrator, poll_interval_seconds: float = 30.0) -> None:
        self.orchestrator = orchestrator
        self.poll_interval_seconds = poll_interval_seconds
        self._schedules: Dict[str, Dict[str, Any]] = {}

    def add_schedule(self, schedule: TrainingSchedule) -> None:
        if not croniter.is_valid(schedule.cron_expression):
            raise ValueError(f"Invalid cron expression: {schedule.cron_expression}")
        next_run = croniter(schedule.cron_expression, datetime.now(timezone.utc)).get_next(datetime)
        self._schedules[schedule.schedule_id] = {
            "schedule": schedule,
            "next_run": next_run,
        }
        LOGGER.info(
            json.dumps(
                {
                    "event": "schedule_added",
                    "schedule_id": schedule.schedule_id,
                    "next_run": next_run.isoformat(),
                },
                sort_keys=True,
            )
        )

    async def run_forever(self) -> None:
        while True:
            now = datetime.now(timezone.utc)
            tasks: List[asyncio.Task[Any]] = []

            for schedule_state in self._schedules.values():
                schedule: TrainingSchedule = schedule_state["schedule"]
                if not schedule.enabled:
                    continue

                if now >= schedule_state["next_run"]:
                    for asset in schedule.asset_specs:
                        job_id = f"{schedule.schedule_id}-{asset.asset_id}-{int(now.timestamp())}"
                        job = TrainingJob(
                            job_id=job_id,
                            asset_spec=asset,
                            rl_config=schedule.rl_config,
                            metadata={"schedule_id": schedule.schedule_id, **schedule.metadata},
                        )
                        tasks.append(asyncio.create_task(self.orchestrator.execute_training_job(job)))

                    schedule_state["next_run"] = croniter(
                        schedule.cron_expression,
                        now,
                    ).get_next(datetime)

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

            await asyncio.sleep(self.poll_interval_seconds)
