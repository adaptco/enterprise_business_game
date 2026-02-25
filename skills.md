# skills.md

This file complements `AGENTS.md` and defines skill activation + production-release behavior for this repository.

## Active skills

### 1) `deployment_monitor`
Use when a request includes deployment verification, release health, post-deploy status tracking, rollout checks, or environment blockers.

**Workflow**
1. Confirm deployment context (project, branch, environment, release target).
2. Run/build/deploy status checks and capture terminal evidence.
3. Validate data dependencies (BigQuery datasets/tables/locations, auth, region).
4. Emit a status verdict:
   - `Verified` (all checks pass)
   - `Blocked` (with precise blocker + remediation)
5. Provide a release-safe checklist before merge/push.

**BigQuery location guardrail**
If query fails with `Dataset ... was not found in location ...`, verify dataset region first, then execute query in the dataset region.

### 2) `code_review`
Use when changes are implemented and need an automated review phase before release.

**Workflow**
1. Review touched files for correctness and integration consistency.
2. Confirm error handling and fail-closed behavior.
3. Verify logging/telemetry for deployment observability.
4. Ensure formatting/lint/tests pass or report explicit environment limitations.
5. Produce actionable findings and block release if critical issues remain.

## Integration sequence

When both skills are requested:
1. Run `code_review` first (quality gate).
2. Run `deployment_monitor` second (runtime/release gate).
3. Mark final status as `Deployed & Verified` only when both gates pass.

## Production release checklist

1. Stage and commit:
   - `git add .`
   - `git commit -m "feat: implement self-correction and deployment monitoring"`
2. Push for rollout:
   - `git push`
3. Verify runtime data plane:
   - Confirm BigQuery dataset location in project explorer.
   - Re-run query in matching location.
4. Confirm monitoring signal:
   - Deployment checks green.
   - Metrics ingestion healthy.
   - Status updated to `Verified`.

## Output contract

Every deployment summary must include:
- Current gate (`code_review`, `deployment_monitor`)
- Result (`pass`, `blocked`)
- Evidence (exact command/log snippet)
- Next action with owner
