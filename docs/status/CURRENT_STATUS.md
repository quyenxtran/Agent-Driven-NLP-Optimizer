# CURRENT_STATUS — AutoResearch-SMB

Date: 2026-04-14

## Short version

AutoResearch-SMB already contains a substantial **agent-orchestrated optimization system** for the SMB use case.

The repo already has:
- real SMB model and optimization code
- BO and agent orchestration code
- benchmark and baseline infrastructure
- tests, Slurm launchers, and artifact pipelines
- a cleaned documentation layout with archived stale status files

The project is **not mainly blocked by repo cleanup anymore**.

The live blocker is now:

**canonicalizing the benchmark story, research layer, and forward optimization roadmap**

## What is established

- SMB model and solver stack exist in `src/sembasmb/`
- Agent orchestration exists in `benchmarks/agent_*`
- BO and baseline infrastructure exist in `benchmarks/`
- multi-stage study code and documentation already exist
- `PLAN.md` now frames the project as cost-aware, mixed, expensive optimization
- the active TODO now reflects the new priorities

## What is still unresolved

- the repo still has competing Phase 3 strategy stories:
  - 3-strategy `A/B/C`
  - 4-strategy `heuristic / BO / Agent+LHS / Agent+Multi-BO`
- the Phase 2 artifact contract is not yet the canonical Phase 3 input contract
- the research/literature layer does not yet exist as a first-class deliverable
- benchmark claims are stronger than the current explicit artifact-to-claim traceability
- the publication-facing method story is not yet fully aligned with the current roadmap

## Current project direction

Per `PLAN.md`, the next milestone sequence is:

1. cleanup baseline — largely complete
2. real literature layer
3. canonical benchmark contract
4. cost-aware mixed-space BO baseline
5. BO→IPOPT hybrid
6. narrow agent policy for evaluation purpose and fidelity

## Most important next move

Lock the **canonical benchmark contract**:
- choose the Phase 3 strategy family
- unify method naming across docs and scripts
- define the candidate abstraction `(layout, controls, fidelity)`
- define the authoritative artifact chain from Phase 2 into Phase 3

Without that, the benchmark story and publication story stay partially provisional.

## Current benchmark evidence note

See:
- `docs/benchmarks/BENCHMARK_EVIDENCE_STATUS.md`

## Active execution checklist

See:
- `docs/status/TODO-2026-04-13-agent-optimizer.md`
- `PLAN.md`
