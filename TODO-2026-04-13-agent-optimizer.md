# TODO — AutoResearch-SMB Agent-Orchestrated Optimization Status

Date: 2026-04-13
Repo: `AutoResearch-SMB`

## Purpose

This TODO/status file is reconciled against the **actual contents of the AutoResearch-SMB repository**.
It replaces the earlier generic checklist that was copied in from a different workspace and therefore overstated what had been completed **inside this repo**.

## Core framing

The project is best described as an **agentic orchestration layer around optimization tools**, not as an LLM replacing numerical optimization.

Strong framing sentence:

> The agent does not replace numerical optimization; it allocates optimization effort and experimental budget more intelligently across rounds.

That framing is already broadly consistent with this repo’s current design.

---

## What is already present in AutoResearch-SMB

### 1. Research framing and project docs
- [x] README describing agent-driven optimization and SMB use case
- [x] agentic optimization framing already present
- [x] autonomous scientific search motivation already present
- [x] phase/study documentation already extensive
- [x] manuscript/protocol-oriented docs already present

Relevant files include:
- `README.md`
- `AGENT_ORCHESTRATED_BO.md`
- `AGENT_IN_BO_LOOP.md`
- `BENCHMARK_COMPARISON.md`
- `MANUSCRIPT_METHODOLOGY.md`
- `SCIENTIFIC_PROTOCOL.md`
- `PHASE3_PUBLICATION_PLAN.md`
- `STUDY_EXEC_SUMMARY.md`

### 2. Core optimization code
- [x] SMB model implementation exists
- [x] IPOPT-based optimization path exists
- [x] solver/config/model/metrics modules exist
- [x] benchmark driver exists

Relevant files include:
- `src/sembasmb/model.py`
- `src/sembasmb/optimization.py`
- `src/sembasmb/solver.py`
- `src/sembasmb/config.py`
- `src/sembasmb/metrics.py`
- `benchmarks/run_stage.py`

### 3. Agent orchestration system
- [x] agent policy logic exists
- [x] multi-agent runner exists
- [x] SQLite-backed evidence/history exists
- [x] scientist proposer/reviewer/executive workflow exists
- [x] execution gating and screening policy exist
- [x] low-fidelity / finalization gate logic exists
- [x] logging and artifact writing exist

Relevant files include:
- `benchmarks/agent_policy.py`
- `benchmarks/agent_runner.py`
- `benchmarks/agent_db.py`
- `benchmarks/agent_evidence.py`
- `benchmarks/agent_scientists.py`
- `benchmarks/agent_llm_client.py`
- `benchmarks/agent_results.py`

### 4. Baselines and evaluation infrastructure
- [x] BO baseline code exists
- [x] LHS baseline code exists
- [x] multiple phase 3 strategy implementations exist
- [x] strategy comparison orchestration exists
- [x] high-fidelity validation orchestration exists

Relevant files include:
- `benchmarks/bo_gp_baseline.py`
- `benchmarks/bo_gp_runner.py`
- `benchmarks/lhs_only_runner.py`
- `benchmarks/phase3_strategy_a_baseline.py`
- `benchmarks/phase3_strategy_b_bo_gp.py`
- `benchmarks/phase3_strategy_c_agent_lhs.py`
- `benchmarks/phase3_strategy4_agent_bo.py`
- `benchmarks/evaluate_phase3_strategies.py`

### 5. Tests and reproducibility support
- [x] tests directory exists
- [x] repo already contains multiple test files
- [x] slurm launchers and pipeline scripts exist
- [x] artifact/log structure exists

---

## What still needs to be done or clarified

### A. Tighten the paper/repo framing
- [ ] Update top-level framing consistently to say **agent-orchestrated optimization**
- [ ] Make sure docs do not overclaim “LLM as optimizer” when the implementation is really orchestration + solver tooling
- [ ] Consolidate overlapping docs so the current story is easier to follow
- [ ] Add one concise architecture diagram/doc that points to the actual code paths in `benchmarks/` and `src/sembasmb/`

### B. Reconcile project status documents
- [ ] Identify the current source-of-truth status file(s)
- [ ] Archive outdated planning/status docs that conflict with current workflow
- [ ] Add a single short current-status summary that explains:
  - [ ] what is working
  - [ ] what is experimentally validated
  - [ ] what remains blocked

### C. Benchmark execution and evidence
- [ ] Confirm which baseline comparisons have been fully run with real data
- [ ] Confirm which reported conclusions are based on completed runs vs partial runs
- [ ] Run or rerun missing baselines/ablations if needed
- [ ] Produce one clean benchmark summary artifact for publication use

### D. Agent policy quality and evaluation
- [ ] Review `benchmarks/agent_policy.py` against the desired framing:
  - [ ] solver choice
  - [ ] fidelity choice
  - [ ] exploration vs exploitation
  - [ ] failure interpretation
  - [ ] handoff logic
- [ ] Document where each of those decisions currently lives in code
- [ ] Add tests for the highest-risk policy branches if coverage is thin

### E. LLM and orchestration claims
- [ ] Document exactly what the LLM is responsible for vs what deterministic code handles
- [ ] Make the executive/reviewer/proposer roles publication-ready and concise
- [ ] State limits clearly:
  - [ ] no proof of global optimality
  - [ ] IPOPT remains local
  - [ ] agent allocates search effort rather than replacing solver math

### F. References and writing assets
- [ ] Clean and complete BibTeX references
- [ ] Add a paper-ready related-work section or note
- [ ] Distill the strongest contribution statement into abstract/introduction language

---

## Honest status summary

### Definitely done in this repo
- agent-based orchestration framework exists
- real SMB optimization code exists
- benchmark/baseline infrastructure exists
- multi-stage workflow exists
- substantial documentation exists

### Not yet verified from this quick inspection
- whether every claimed benchmark result has been fully completed and is current
- whether all status docs agree with the latest code and artifacts
- whether the top-level framing is fully consistent across the repo

### Most important next step
- [ ] Reconcile **current project status, benchmark evidence, and manuscript framing** into one clean, repo-local source of truth

---

## Immediate next actions

1. [ ] Audit current status/docs for contradictions (`PLAN.md`, `LIVE_STATUS.md`, phase docs, README)
2. [ ] Create a concise `CURRENT_STATUS.md` for AutoResearch-SMB
3. [ ] Tighten README framing around agent-orchestrated optimization
4. [ ] Map code modules to paper concepts in one architecture doc
5. [ ] Clean BibTeX / citation notes for the manuscript

---

## Notes

- This repo is already much further along than a fresh scaffold.
- The main need is not to rebuild a toy orchestrator, but to **reconcile framing, evidence, and current status** around the real system that already exists here.
- Future TODO updates should be based only on the state of `AutoResearch-SMB`, not other workspaces.
