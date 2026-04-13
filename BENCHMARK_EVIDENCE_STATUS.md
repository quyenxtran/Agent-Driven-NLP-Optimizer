# Benchmark Evidence Status

Date: 2026-04-13
Repo: `AutoResearch-SMB`

## Purpose

This note reconciles **what the benchmark/result documents claim** with **what is visibly present in the repository and artifacts**.

It is intended to reduce the risk of overclaiming results in README/manuscript/status docs.

---

## High-confidence observations from the repo

### 1. The repo clearly contains substantial benchmark infrastructure
Present in code:
- Phase 2 generation / screening infrastructure
- Phase 3 strategy-comparison infrastructure
- BO baseline code
- agent-selection code
- LHS / heuristic paths
- validation scripts and Slurm workflows

### 2. The artifacts directory clearly contains real run outputs
Visible artifact categories include:
- BO smoke/baseline outputs
- LHS smoke/baseline outputs
- agent-runner parse/smoke outputs
- many Phase 2 per-seed artifacts under `artifacts/phase2_lhs_seeding/`

This is strong evidence that the repo has been used for real runs, not just planning.

### 3. There is a strong completed-results narrative in `RESULTS_SUMMARY.txt`
That file presents a clean end-to-end story:
- Phase 2 complete
- Phase 3 complete
- consensus on NC `[2,1,3,2]`
- Phase 4 attempted and concluded infeasible
- recommendation to use medium-fidelity Phase 2 operating point

This may be true, but it needs to be treated carefully unless tied to clearly identified artifact files and current pipeline assumptions.

---

## Tensions / mismatches that need to be kept in mind

### A. `PLAN.md` vs completed-results narrative
`PLAN.md` currently frames the project as being centered on a reconciled active Phase 2 reference-evaluation workflow and warns that multiple older Phase 2 variants and schemas exist.

That means:
- `PLAN.md` is cautious and workflow-focused
- `RESULTS_SUMMARY.txt` is confident and outcome-focused

These are not necessarily contradictory, but they are written from different assumptions and likely different moments in the project.

### B. Phase 3 script vs Phase 3 publication plan
`benchmarks/evaluate_phase3_strategies.py` still describes an older design with:
- 5 selected NCs per strategy
- 3 high-fidelity validations per selected NC
- 45 total high-fidelity runs

But `PHASE3_PUBLICATION_PLAN.md` explicitly says the revised design should instead be:
- top 5 selection per strategy
- 1 high-fidelity promotion run per selected NC
- only the single promoted winner gets multi-start robustness validation
- total budget closer to 24 runs than 45

So the **publication plan and the orchestration script are out of sync**.

### C. Artifact presence vs manuscript-ready evidence
The repo contains many raw artifacts, but raw artifact presence alone does not prove that:
- the latest summary files were generated from the latest intended pipeline
- all reported numbers are tied to the current canonical workflow
- the manuscript should quote those numbers without qualification

---

## Safe claims vs unsafe claims

### Safe claims right now
- The repo contains a real multi-stage benchmark pipeline.
- The repo contains real artifacts from BO, LHS, and agent-related runs.
- The project has substantial evidence of Phase 2-style evaluation activity.
- The repo contains a completed-results summary proposing NC `[2,1,3,2]` as the best medium-fidelity candidate.
- The project framing is best understood as **agent-orchestrated optimization**, not LLM replacing numerical solvers.

### Claims that should be made carefully
- that the currently canonical pipeline has fully completed end-to-end
- that every reported number in `RESULTS_SUMMARY.txt` is tied to the current source-of-truth workflow in `PLAN.md`
- that the current Phase 3 code exactly matches the revised publication design
- that all benchmark comparisons are publication-ready without further reconciliation

---

## Current best interpretation

The most defensible interpretation is:

1. The repo already contains meaningful benchmark execution history and a plausible winning candidate.
2. The project has evolved over multiple pipeline versions.
3. Some planning docs, result summaries, and execution scripts are not yet perfectly synchronized.
4. Before publication-facing claims are frozen, the benchmark narrative should be reconciled against:
   - actual artifact files
   - actual scripts used to generate them
   - the current intended evaluation design

---

## Recommended next actions

### 1. Identify canonical artifact files
- [ ] Name the exact canonical Phase 2 summary artifact
- [ ] Name the exact canonical Phase 3 strategy result files
- [ ] Name the exact canonical Phase 4 validation artifact

### 2. Reconcile Phase 3 design
- [ ] Decide whether `PHASE3_PUBLICATION_PLAN.md` or `benchmarks/evaluate_phase3_strategies.py` is the intended design
- [ ] Update the other one to match

### 3. Tie `RESULTS_SUMMARY.txt` to artifacts
- [ ] annotate which artifact files support each major claim
- [ ] mark any conclusions that came from older pipeline variants

### 4. Create publication-safe benchmark summary
- [ ] one markdown/json summary that states:
  - [ ] what was run
  - [ ] what artifact files support it
  - [ ] what conclusions are high confidence
  - [ ] what remains provisional

---

## Bottom line

There is clearly real benchmark evidence in this repo.

But the repo currently contains **multiple layers of planning, execution, and summary documents from different pipeline stages**, so benchmark conclusions should be presented as **strong but still requiring final reconciliation** unless and until the canonical artifact chain is made explicit.
