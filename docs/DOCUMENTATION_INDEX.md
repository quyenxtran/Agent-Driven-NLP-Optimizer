# Documentation Index

Date: 2026-04-13

This file tells you which documents to trust first.

## Tier 1 — Primary source-of-truth docs

Read these first.

### `PLAN.md`
Current reconciled execution plan and workflow status.
This should be treated as the **single primary live plan** unless explicitly superseded and reconciled.

### `CURRENT_STATUS.md`
Short repo-local summary of where the project stands.

### `TODO-2026-04-13-agent-optimizer.md`
Current project TODO/status list tied to the actual repo state.

### `docs/ARCHITECTURE_AND_STATUS.md`
High-level architecture map, framing guidance, and source-of-truth pointers.

## Tier 2 — Active technical/reference docs

Use these for implementation, methods, and active study interpretation.

### Core project docs
- `README.md`
- `MANUSCRIPT_METHODOLOGY.md`
- `SCIENTIFIC_PROTOCOL.md`
- `PHASE3_PUBLICATION_PLAN.md`
- `PHASE3_IMPLEMENTATION_STATUS.md`
- `IMPLEMENTATION_ROADMAP.md`

### Agent / study notes
- `AGENT_ORCHESTRATED_BO.md`
- `AGENT_IN_BO_LOOP.md`
- `AGENT_BO_CALCULATOR.md`
- `BENCHMARK_COMPARISON.md`
- `OPTIMIZATION_STATUS.md`

## Tier 3 — Historical / archival docs

These can still be useful, but they are not the active source of truth.

### Explicitly archival
- `LIVE_STATUS.md`
- `PHASE2_STATUS.md`
- `PHASE2_FINAL_CONFIG.md`
- `PHASE2_OPTIONS_GUIDE.md`
- `PHASE2_SCALING_STRATEGY.md`
- `PHASE2_FEASIBILITY_ISSUE.md`

These files mainly preserve prior plans, prior runs, or debugging history.

## How to use this index

If you are trying to answer:

### “What is the project doing right now?”
Read:
1. `PLAN.md`
2. `CURRENT_STATUS.md`

### “How is the system structured?”
Read:
1. `docs/ARCHITECTURE_AND_STATUS.md`
2. `README.md`
3. `benchmarks/agent_runner.py`
4. `benchmarks/agent_policy.py`

### “What should we work on next?”
Read:
1. `TODO-2026-04-13-agent-optimizer.md`
2. `PLAN.md`

### “What old document is safe to ignore unless needed?”
Check whether it is listed under Tier 3 above.

## Guiding rule

When documents conflict:
- prefer **`PLAN.md` first** for planning truth
- prefer **Tier 1** over Tier 2
- prefer **Tier 2** over Tier 3
- prefer current code and current artifacts over stale prose
