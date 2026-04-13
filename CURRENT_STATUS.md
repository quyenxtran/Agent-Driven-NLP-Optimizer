# CURRENT_STATUS — AutoResearch-SMB

Date: 2026-04-13

## Short version

AutoResearch-SMB already contains a substantial **agent-orchestrated optimization system** for the SMB use case.

The repo includes:
- real SMB model and optimization code
- agent policy/orchestration logic
- benchmark and baseline infrastructure
- multi-stage study code and documentation
- tests, Slurm launchers, and artifact pipelines

## Important clarification

A previous TODO file was initially written from work done in a different workspace. That was misleading for this repo.

The current TODO has now been rewritten to reflect the **actual state of AutoResearch-SMB**.

## What appears established

- SMB optimization code exists in `src/sembasmb/`
- Agent orchestration exists in `benchmarks/agent_*`
- Baseline and study infrastructure exists in `benchmarks/phase*` and related files
- Documentation for methodology/protocol/phase plans is extensive

## What still needs careful reconciliation

- which docs are current vs archived
- which benchmark results are complete and publication-ready
- whether the framing is consistently stated as **agent-orchestrated optimization** rather than “LLM replaces optimizer”

## Recommended next move

Create one single source of truth for:
1. current experimental status
2. benchmark completion state
3. manuscript framing
4. next concrete execution tasks

See:
- `TODO-2026-04-13-agent-optimizer.md`
