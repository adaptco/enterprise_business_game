# Skills Operating Guide

## Skill Trigger Policy (AGENTS.md-aligned)
- Invoke `skill-creator` when asked to create a new skill or update an existing skill that extends Codex capabilities with specialized knowledge, workflows, or integrations.
- Invoke `skill-installer` when asked to list installable skills, install a curated skill, or install a skill from a GitHub repository path.
- Apply only the minimal required skill set for the request; do not carry skills across turns unless they are re-requested.

## Minimal Invocation Checklist (Agent Execution)
- Identify whether the user explicitly named a skill or whether the request clearly matches a listed skill description.
- Open the relevant `SKILL.md` and read only the sections needed to execute the current request.
- Load only necessary references, assets, templates, or scripts; avoid bulk-loading directories.
- Reuse provided scripts/templates before writing large replacements.
- Keep context small: summarize long instructions and avoid unnecessary reference chaining.
- If a required skill file is missing or inaccessible, state the issue briefly and proceed with the best fallback workflow.

## For Skill Developers: Production Release Guide
### Required Artifacts
- Updated `skills.md` if trigger policies or other shared guidance are affected.
- Clean git diff scoped to requested changes.
- One commit with a clear, action-oriented commit message.
- Pull request title and body that summarize scope, checks, and operational impact.

### Required Checks Before Release
- Verify formatting and readability of headings, lists, and section structure.
- Verify trigger rules for `skill-creator` and `skill-installer` match AGENTS.md requirements.
- Verify checklist steps are executable by an agent (commands/actions, not abstract prose).
- Verify examples are short, concrete, and aligned with trigger policy.

### PR Expectations
- State what was changed and why.
- State what checks were run and the result.
- Exclude unrelated refactors or opportunistic edits.
- Keep PR content focused, reviewable, and operationally actionable.

## Examples
- **Create a new skill**: “Use `skill-creator` to create a skill that standardizes release-note generation from commit history.”
- **Install a curated skill**: “Use `skill-installer` to install the curated `skill-creator` skill into `$CODEX_HOME/skills`.”
