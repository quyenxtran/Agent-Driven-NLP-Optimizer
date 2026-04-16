# PLAN.md

_Last reconciled: 2026-04-13 18:05 EDT_

This file is the **single authoritative live plan** for AutoResearch-SMB.

If other planning or status documents conflict with this one:
- follow **this file first**
- treat older plan/status notes as archive or supporting context unless they are explicitly reconciled here

Related navigation:
- `docs/status/CURRENT_STATUS.md` — short current summary
- `docs/DOCUMENTATION_INDEX.md` — document priority guide
- `docs/ARCHITECTURE_AND_STATUS.md` — architecture and framing map

## Executive summary

The project should be framed as **agent-orchestrated optimization for expensive SMB evaluations**.

The bottleneck is not only solving a nonlinear program. The harder problem is deciding:
- which expensive simulation or experiment to pay for next
- which fidelity level to use
- whether the next round should explore, exploit, verify, or diagnose

The numerical optimizer remains the optimizer. IPOPT and related solver tooling do the mathematical search. The agent layer should remain narrow, benchmarkable, and policy-oriented.

The next milestone sequence is:

1. **Cleanup baseline** — largely complete
2. **Real literature layer**
3. **Canonical benchmark contract**
4. **Cost-aware mixed-space BO baseline**
5. **BO→IPOPT hybrid**
6. **Agent chooses evaluation purpose and fidelity**

## Current state

### What is already in good shape

- `src/sembasmb/` contains the real SMB model and solver stack
- `benchmarks/` contains benchmark, BO, and agent orchestration code
- `tests/` exists and the packaging remains lightweight and coherent
- stale status docs have been archived under `docs/archive/status/`
- duplicate local-command notes in `slurm/` were removed
- old artifact trees were archived out of the live repo
- `scripts/archive_stale_artifacts.sh` now supports routine artifact cleanup

### What is still unresolved

- the repo still has **two competing Phase 3 stories**
  - a 3-strategy A/B/C design in study docs and execution scripts
  - a 4-strategy design in roadmap-style docs and some benchmark code
- the current reference-eval Phase 2 artifact format is not yet the canonical input contract for downstream strategy comparison
- the literature/research layer is still missing as a first-class, curated deliverable
- the benchmark story is still stronger than the explicit artifact-to-claim chain

### What should no longer be treated as the main blocker

Basic repo hygiene is no longer the primary problem. The live problem is now:

**benchmark and roadmap canonicalization**

That means:
- locking the method vocabulary
- locking the artifact schema used for comparisons
- aligning docs, code, and publication-facing claims

## Core objectives

### 1. Canonical framing

Keep the repo, paper, and benchmark language aligned around:

> The agent does not replace numerical optimization; it allocates optimization effort and experimental budget more intelligently across rounds.

This means:
- no “LLM is the optimizer” framing
- no claim of global optimality from LLM reasoning
- explicit separation of solver responsibilities and policy responsibilities

### 2. Canonical benchmark contract

Define one benchmark contract that states:
- what the candidate representation is
- what objective is optimized
- how feasibility is modeled
- how evaluation cost is modeled
- which artifact files are authoritative for each stage
- which strategy family is canonical

Until this is done, benchmark conclusions should be treated as promising but not fully canonical.

### 3. Real research layer

Build a durable literature layer that supports the “intelligence per round” thesis and the mixed expensive optimization roadmap.

Required structure:
- `RESEARCH.md` — top-level research entry point
- `docs/research/index.md` — organized literature map
- `docs/research/papers/<slug>.md` — one summary per source

Required literature bins:
- classical NLP/MINLP baselines
- constrained and mixed BO
- multi-fidelity and cost-aware optimization
- BO + local NLP hybrids
- autonomous-lab and scientific-agent systems

Each paper summary should use one rigid template:
- citation
- problem setting
- method
- assumptions
- constraint handling
- mixed-variable handling
- expensive-data handling
- empirical evidence
- direct relevance to this repo
- implementation takeaways
- limitations

### 4. Forward technical roadmap

The technical core should evolve toward:

**mixed, constrained, cost-aware, multi-fidelity BO feeding local refinement**

not:

**ask an LLM for the next point**

The candidate abstraction should be:
- `(discrete layout, continuous controls, fidelity level)`

The modeled outputs should be:
- objective
- feasibility / constraint satisfaction
- evaluation cost

### 5. Narrow, benchmarkable agent role

The agent should not free-form emit final process settings as the primary method.

The canonical agent role should be:
- rank candidate batches proposed by BO, heuristics, or local search
- decide whether the next round is `EXPLORE`, `EXPLOIT`, `VERIFY`, or `DIAGNOSE`
- choose the next evaluation fidelity
- write a structured rationale covering:
  - expected objective gain
  - feasibility learning
  - uncertainty reduction
  - diagnostic value
  - expected cost

## Canonical comparison ladder

The forward method ladder should be:

1. **IPOPT multi-start on fixed layouts**
2. **Direct MINLP where tractable**
3. **Constrained mixed-space BO baseline**
4. **BO→IPOPT hybrid**
5. **Agent-guided BO or agent-guided BO→IPOPT**

Interpretation:
- Step 1 establishes the local continuous optimization baseline
- Step 2 tests whether tractable mixed-integer solvers can compete on reduced instances
- Step 3 adds mixed categorical/continuous surrogate optimization
- Step 4 adds local continuous refinement after BO proposes a promising candidate
- Step 5 adds a narrow policy layer that decides evaluation purpose and fidelity

## Roadmap

### Phase A — Cleanup baseline and canonical vocabulary

Status: **mostly complete**

Done:
- archive stale status docs instead of deleting aggressively
- reduce root clutter
- remove duplicate local-command notes
- move old artifacts out of the live repo

Still required:
- choose the canonical Phase 3 strategy family
- unify names across docs, scripts, and benchmark outputs
- treat `research.md` as a run log, not as the literature layer

### Phase B — Literature and research layer

Status: **not started**

Deliverables:
- `RESEARCH.md`
- `docs/research/index.md`
- `docs/research/papers/<slug>.md`

Minimum source set should include:
- IPOPT and Wächter–Biegler
- BONMIN
- COUENNE
- SCIP
- constrained BO references
- multi-fidelity BO references
- TuRBO
- CoCaBO
- MIVABO
- BoTorch mixed-space modeling docs
- at least one BO-IPOPT hybrid paper
- constrained BO for hybrid / grey-box models
- A-Lab
- Coscientist
- at least one recent LLM-agent lab paper
- cost-constrained BO
- adaptive surrogate experimental design
- Bayesian experimental design for expensive experiments

### Phase C — Canonical benchmark contract

Status: **not complete**

Required decisions:
- choose the canonical strategy set:
  - either 3-strategy `A/B/C`
  - or 4-strategy `heuristic / BO / Agent+LHS / Agent+Multi-BO`
- decide the canonical Phase 2 artifact contract
- decide whether Phase 3 reads current reference-eval outputs directly or via a converter
- define publication-safe metrics and artifact mappings

Required benchmark metrics:
- best feasible objective vs cumulative cost
- time to first feasible point
- feasibility rate
- regret or gap to best-known
- promotion efficiency from cheap to expensive fidelity

The benchmark protocol should be **budget-normalized**, not merely iteration-matched.

### Phase D — Cost-aware mixed-space BO baseline

Status: **planned**

Deliverable:
- a constrained mixed-space BO baseline that treats layout, controls, and fidelity explicitly

Requirements:
- model objective separately from feasibility and cost
- use the candidate abstraction `(layout, controls, fidelity)`
- make the acquisition rule cost-aware when possible
- benchmark directly against heuristic and IPOPT baselines

### Phase E — BO→IPOPT hybrid

Status: **planned**

Deliverable:
- a hybrid method where BO proposes promising mixed candidates and IPOPT performs local continuous refinement

Why this is the next serious technical step:
- it matches the structure of the problem
- it is better grounded in the optimization literature than free-form agent proposals
- it yields a clean ablation path against both BO-only and IPOPT-only baselines

### Phase F — Agent-guided evaluation policy

Status: **planned**

Deliverable:
- a narrow policy layer on top of the hybrid stack

The agent should decide:
- whether the round is explore / exploit / verify / diagnose
- which fidelity to run next
- which candidate batch is worth paying for next

The agent should **not** be evaluated as a black-box generator of final process settings.

### Phase G — Publication package

Status: **planned**

Deliverables:
- one publication-safe benchmark summary
- one artifact-to-claim traceability map
- reconciled methods text
- contribution statement tied to the actual implemented comparison ladder

## Current operational context

### Active Phase 2 data source

The currently visible live operational context is still the reference-evaluation workflow centered on:
- `slurm/pace_smb_phase2_reference_eval.slurm`
- `artifacts/phase2_lhs_seeding/phase2_reference_summary.json`

This remains useful operational evidence.

But it should no longer be mistaken for the whole project roadmap.

### How to interpret the current Phase 2 outputs

Use the current reference-eval outputs as:
- empirical evidence that the repo runs real expensive SMB evaluations
- a candidate seed dataset for later comparison work
- a schema-reconciliation problem that must be solved before canonical Phase 3 benchmarking

Do **not** assume that the current `phase2_reference_summary.json` alone fully defines the final benchmark contract.

## Immediate next actions

1. Lock the canonical Phase 3 strategy family and naming.
2. Define the canonical artifact contract from Phase 2 into Phase 3.
3. Create the literature layer (`RESEARCH.md`, `docs/research/index.md`, paper summaries).
4. Implement the constrained mixed-space BO baseline around `(layout, controls, fidelity)`.
5. Define the BO→IPOPT hybrid interface and evaluation protocol.
6. Restrict the agent role to evaluation-purpose and fidelity choice, then benchmark it.

## Files that should be treated as primary

- `PLAN.md` ← single authoritative live plan
- `docs/status/CURRENT_STATUS.md`
- `docs/DOCUMENTATION_INDEX.md`
- `docs/ARCHITECTURE_AND_STATUS.md`
- `README.md`
- `agents/Objectives.md`
- `docs/benchmarks/BENCHMARK_EVIDENCE_STATUS.md`

## Files that should be treated mainly as archive or support

- `docs/archive/status/LIVE_STATUS.md`
- `docs/archive/status/PHASE2_STATUS.md`
- `docs/archive/status/PHASE2_FINAL_CONFIG.md`
- `docs/archive/status/PHASE2_FEASIBILITY_ISSUE.md`
- `docs/archive/status/PHASE2_SCALING_STRATEGY.md`
- `docs/phases/PHASE2_OPTIONS_GUIDE.md`
- `research.md` ← currently a run log / working note, not the canonical literature layer

## Clean project truth in one sentence

**AutoResearch-SMB should now be treated as a project for cost-aware, mixed, expensive SMB optimization where the agent’s job is to allocate evaluation budget intelligently on top of solver and surrogate methods, not to replace the optimizer itself.**
