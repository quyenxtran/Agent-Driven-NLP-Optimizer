# PLAN.md

_Last reconciled: 2026-04-13 16:10 EDT_

This file is the **single authoritative live plan** for AutoResearch-SMB.

If other planning or status documents conflict with this one:
- follow **this file first**
- treat older plan/status notes as archive or supporting context unless they are explicitly reconciled here

Related navigation:
- `CURRENT_STATUS.md` — short current summary
- `docs/DOCUMENTATION_INDEX.md` — document priority guide
- `docs/ARCHITECTURE_AND_STATUS.md` — architecture and framing map

## Executive summary

This project is an SMB optimization pipeline aimed at comparing strategy quality for NC selection and downstream high-fidelity validation.

The current working plan is:

1. **Build Phase 2 foundation/reference data** across many NCs and seeds.
2. **Use that Phase 2 data in Phase 3** to compare multiple selection strategies.
3. **Run Phase 4/final validation** on the winning strategy/configuration under stricter requirements.

At the moment, the repo contains **multiple historical Phase 2 variants**. The currently running production job is a **reference-evaluation Phase 2 variant**, while some markdown files still describe earlier or alternate low-fidelity optimize-all-seeds plans.

---

## Source-of-truth status right now

### Active running job

**Current Slurm job:** `6289854`
- **Name:** `smb-phase2-ref`
- **Script:** `slurm/pace_smb_phase2_reference_eval.slurm`
- **Work dir:** `/storage/home/hcoda1/4/qtran47/AutoResearch-SMB`
- **Stdout:** `logs/smb-phase2-ref-6289854.out`
- **Artifacts dir:** `artifacts/phase2_lhs_seeding`

### What this job is doing

This is **Phase 2 reference evaluation with 5D LHS sampling**, not full optimize-layouts screening.

- **32 NCs**
- **25 seeds per NC**
- **800 total reference evaluations**
- Fixed-flow `reference-eval` stage
- Medium fidelity: `nfex=6`, `nfet=3`, `ncp=1`
- Relaxed constraints:
  - purity >= 0.05
  - recovery_GA >= 0.10
  - recovery_MA >= 0.15
- Parallel layout:
  - `12` workers
  - `2` OMP threads per worker
  - `24` CPUs total

### Observed progress

From the live log, job `6289854` had completed a large block of NCs and was in the middle of:
- **NC `[1,2,2,3]`**
- with visible progress at **10/25 seeds** when checked

So the run is clearly active and producing per-seed JSON artifacts.

---

## Current pipeline plan

## Phase 2: Foundation data generation

### Current intent

Generate broad NC/seed coverage so later strategy comparison is based on shared data instead of one-off intuition.

### Current practical reality

There are **two distinct Phase 2 styles** in the repo:

#### A. Older / alternate Phase 2 style: low-fidelity optimize-all-seeds
Described in several older status docs.

Characteristics:
- 100 seeds per NC
- low fidelity (`nfex=4`, `nfet=2`, `ncp=1`)
- optimize-layouts / screening style
- intended output: `artifacts/phase2_lhs_seeding/phase2_summary.json`

Status:
- historically important
- partially implemented / previously run
- associated docs contain stale job IDs and inconsistent runtime expectations
- current `phase2_summary.json` in artifacts exists but is **not currently a reliable representation of the live production run**

#### B. Current production-style Phase 2: reference evaluation
**This is what is running right now.**

Characteristics:
- 25 seeds per NC
- medium fidelity (`nfex=6`, `nfet=3`, `ncp=1`)
- fixed-flow reference evaluation
- per-seed JSON outputs named like:
  - `reference-eval.<jobid>.phase2_ref_nc_[... ]_seed_<k>.json`
- aggregate output expected:
  - `artifacts/phase2_lhs_seeding/phase2_reference_summary.json`

### What to treat as the current Phase 2 target

**Treat the reference-evaluation variant as the active Phase 2 plan unless deliberately superseded.**

Why:
- it is the actual live job
- it is producing artifacts now
- it avoids some of the earlier feasibility / timeout / empty-summary problems seen in older Phase 2 runs

---

## Phase 3: Strategy comparison

### Goal

Compare multiple ways of selecting promising NCs using shared Phase 2 data.

### Intended strategy family

The repo consistently points toward comparing variants such as:

1. **Regular / heuristic baseline**
2. **BO baseline**
3. **Agent + LHS / domain reasoning**
4. **Agent + multi-BO**

### High-level hypothesis

The expected winner in the design docs is:
- **Agent + Multi-BO**

Reasoning in the docs:
- combine statistical surrogates with agent/domain reasoning
- balance exploitation and exploration
- outperform pure heuristic ranking and single-model BO

### Current implementation state

Phase 3 code appears to be substantially implemented in the repo, but execution readiness depends on Phase 2 data being in the format expected by the evaluators.

Important caveat:
- Some Phase 3 docs assume `phase2_summary.json` contains dense seed-level optimization results.
- The currently running job is instead generating **reference-eval seed artifacts** and a different aggregate summary.

So before Phase 3 runs cleanly, the project needs one of:
1. Phase 3 readers updated to consume the reference-eval output format, or
2. a conversion/aggregation step that turns current reference-eval outputs into the Phase 3 input schema.

---

## Phase 4: Final validation

### Goal

Take the best strategy / best NC candidates and validate them at stricter or more production-like conditions.

Typical intent across the docs:
- run higher-fidelity or stricter-constraint validation
- verify that the strategy winner remains best under final conditions
- use this as the publication / final-results stage

This phase is conceptually stable across documents, even though exact thresholds vary between files.

---

## What is outdated vs still useful

This section is normative: unless a file is listed as primary here or reconciled later into this plan, it should not override `PLAN.md`.

## Outdated or partially outdated docs

### `LIVE_STATUS.md`
Useful historically, but stale.

Why outdated:
- references old job `6280391`
- assumes auto-submission timeline that no longer matches the current live run
- describes a different Phase 2 execution mode

### `PHASE2_STATUS.md`
Useful as an archive of an older production run, but not current truth.

Why outdated:
- tied to old job `6282883`
- describes 100-seed low-fidelity optimize-all-seeds behavior
- does not reflect current `6289854` reference-eval job

### `PHASE2_FINAL_CONFIG.md`
Useful historical configuration note, but no longer the active plan.

Why outdated:
- tied to old job `6282213`
- assumes 3,100-seed optimize-all-seeds run
- runtime math in the file conflicts internally with later operational reality

### `PHASE2_OPTIONS_GUIDE.md` / `PHASE2_FEASIBILITY_ISSUE.md` / `PHASE2_SCALING_STRATEGY.md`
Useful as recovery history and design rationale.

Why only partially current:
- they explain why earlier Phase 2 variants struggled
- they document useful tradeoffs
- but they are not the current live execution plan

## Still useful / conceptually current docs

### `PHASE_PIPELINE_V2.md`
Best high-level description of the intended scientific workflow.

What remains useful:
- Phase 2 → Phase 3 → Phase 4 structure
- idea of shared Phase 2 data feeding strategy comparison
- emphasis on comparing multiple methods fairly

### `IMPLEMENTATION_ROADMAP.md`
Useful for how Agent + BO is supposed to work conceptually.

What remains useful:
- the reasoning logic for strategy comparison
- expected role of BO, domain knowledge, and exploration

### `PHASE3_IMPLEMENTATION_STATUS.md`
Useful snapshot of strategy implementation readiness.

Caveat:
- some details assume an older Phase 2 input schema

### `OPTIMIZATION_STATUS.md`
Useful for agent-loop performance and robustness improvements.

Caveat:
- this is more about agent/runtime optimization than the core current Phase 2 production run

---

## Current artifact reality

## What exists now

Inside `artifacts/phase2_lhs_seeding` there is evidence of **multiple historical runs**:
- older optimize-layouts outputs
- older reference-eval runs (`6288977`, `6288996`, `6289810`)
- the active current run (`6289854`)
- aggregate files including:
  - `phase2_summary.json`
  - `phase2_reference_summary.json`

## Important caveat on `phase2_summary.json`

Current quick inspection showed:
- `results = 10`
- `nonempty = 0`
- sample keys:
  - `best_productivity`
  - `n_evaluations`
  - `n_feasible`
  - `nc`

That means this file is **not yet the rich, final Phase 2 foundation dataset** that many Phase 3 docs assume.

## Better current artifact signal

`phase2_reference_summary.json` is the more relevant aggregate artifact for the current active Phase 2 style.

The many per-seed `reference-eval.*.json` files for job `6289854` are the clearest evidence that the live run is producing usable data.

---

## Recommended next steps

### Immediate next step

1. **Let job `6289854` finish** unless there is a strong reason to stop it.
2. **Treat its outputs as the current Phase 2 baseline dataset.**
3. **Inspect `phase2_reference_summary.json` after completion** to verify:
   - number of NCs completed
   - success / feasible counts
   - per-NC metrics
   - whether it is sufficient for strategy comparison directly

### After Phase 2 completes

4. Decide whether to:
   - **A. use reference-eval output directly for Phase 3**, or
   - **B. write a converter** from reference-eval outputs to the schema expected by the existing Phase 3 scripts.

### Then

5. Run / validate the Phase 3 strategy comparison on the reconciled Phase 2 dataset.
6. Promote the best candidate(s) to final validation.

---

## Operational plan going forward

## Canonical workflow

### Step 1 — Finish current Phase 2 reference run
- Job: `6289854`
- Output target: `artifacts/phase2_lhs_seeding/phase2_reference_summary.json`

### Step 2 — Consolidate Phase 2 outputs
- cleanly identify the final aggregate artifact from the active run
- avoid mixing old job outputs with new ones
- if needed, archive old Phase 2 summaries separately

### Step 3 — Adapt Phase 3 input expectations
- either update evaluation scripts to read reference-eval summaries
- or generate a normalized `phase2_summary.json` from reference outputs

### Step 4 — Run strategy comparison
- baseline heuristic
- BO baseline
- Agent + LHS/domain
- Agent + multi-BO

### Step 5 — Final validation
- validate winning strategy / NC candidates at strict settings

---

## Clean project truth in one sentence

**The project is currently in Phase 2, and the real live plan is a medium-fidelity LHS-based reference evaluation run (`6289854`) whose outputs should become the foundation dataset for later multi-strategy NC selection and final validation.**

---

## Files that should now be treated as primary

- `PLAN.md` ← single authoritative live plan
- `CURRENT_STATUS.md`
- `docs/DOCUMENTATION_INDEX.md`
- `docs/ARCHITECTURE_AND_STATUS.md`
- `slurm/pace_smb_phase2_reference_eval.slurm`
- `artifacts/phase2_lhs_seeding/phase2_reference_summary.json`
- `logs/smb-phase2-ref-6289854.out`

## Files that should be treated mainly as archive/history

- `LIVE_STATUS.md`
- `PHASE2_STATUS.md`
- `PHASE2_FINAL_CONFIG.md`
- `PHASE2_OPTIONS_GUIDE.md`
- `PHASE2_FEASIBILITY_ISSUE.md`
- `PHASE2_SCALING_STRATEGY.md`

---

## Git / repo note

Remote:
- `https://github.com/quyenxtran/Agent-Driven-NLP-Optimizer.git`

Local status when this plan was reconciled:
- branch `main`
- ahead of origin by `19` commits

That means the working tree/repo state on the machine is likely the most current source of truth, even if GitHub and markdown docs are not perfectly synchronized.
