# TODO — AutoResearch-SMB Live Priorities

Date: 2026-04-13
Repo: `AutoResearch-SMB`

## Purpose

This TODO is the active execution checklist for the current project direction in `PLAN.md`.

It replaces the older checklist that focused too heavily on repo cleanup and generic status reconciliation. Cleanup was necessary, but it is no longer the main blocker.

The live blocker now is:

**canonicalizing the benchmark story, method ladder, and research foundation**

## Core framing

Keep this sentence stable across code, docs, slides, and manuscript drafts:

> The agent does not replace numerical optimization; it allocates optimization effort and experimental budget more intelligently across rounds.

Implications:
- IPOPT and related solvers remain responsible for mathematical optimization
- BO and hybrid methods remain responsible for surrogate-guided search
- the agent remains a narrow policy layer for evaluation purpose, prioritization, and fidelity choice

## What is already done

### Repo hygiene
- [x] root markdown clutter reduced
- [x] stale status docs moved under `docs/archive/status/`
- [x] duplicate local-command notes removed from `slurm/`
- [x] old artifact trees archived out of the live repo
- [x] artifact archiving helper added: `scripts/archive_stale_artifacts.sh`
- [x] `PLAN.md` rewritten around the new cost-aware mixed-optimization roadmap

### Existing technical assets
- [x] SMB model and solver stack exist in `src/sembasmb/`
- [x] benchmark and orchestration code exist in `benchmarks/`
- [x] tests and Slurm launchers already exist
- [x] BO baseline code exists
- [x] agent orchestration code exists
- [x] study/protocol/manuscript docs already exist

## What is still unresolved

- [ ] canonical Phase 3 strategy family is not locked
- [ ] canonical Phase 2 → Phase 3 artifact contract is not locked
- [ ] literature layer does not yet exist as a first-class deliverable
- [ ] benchmark claims are stronger than the explicit artifact-to-claim traceability
- [ ] publication-facing method story is not fully aligned with the current code and roadmap

## Priority objectives

### 1. Lock the canonical benchmark contract

- [ ] Decide whether the canonical strategy set is:
  - [ ] 3-strategy `A/B/C`
  - [ ] 4-strategy `heuristic / BO / Agent+LHS / Agent+Multi-BO`
- [ ] Unify strategy names across:
  - [ ] `PLAN.md`
  - [ ] study docs
  - [ ] benchmark scripts
  - [ ] output artifact names
- [ ] Define the canonical candidate abstraction:
  - [ ] `(discrete layout, continuous controls, fidelity level)`
- [ ] Define the canonical modeled outputs:
  - [ ] objective
  - [ ] feasibility
  - [ ] evaluation cost
- [ ] Define the authoritative artifact files for each phase

### 2. Reconcile Phase 2 outputs with Phase 3 inputs

- [ ] Decide whether Phase 3 should read the current reference-eval outputs directly
- [ ] If not, implement a converter from current Phase 2 outputs to the canonical Phase 3 schema
- [ ] Name the canonical Phase 2 artifact
- [ ] Name the canonical Phase 3 result artifacts
- [ ] Name the canonical Phase 4 / validation artifacts
- [ ] Document the artifact chain in one publication-safe summary

### 3. Build the real research layer

- [ ] Create `RESEARCH.md`
- [ ] Create `docs/research/index.md`
- [ ] Create `docs/research/papers/`
- [ ] Define and use one rigid per-paper template:
  - [ ] citation
  - [ ] problem setting
  - [ ] method
  - [ ] assumptions
  - [ ] constraint handling
  - [ ] mixed-variable handling
  - [ ] expensive-data handling
  - [ ] empirical evidence
  - [ ] direct relevance to this repo
  - [ ] implementation takeaways
  - [ ] limitations
- [ ] Populate the five literature bins:
  - [ ] classical NLP/MINLP baselines
  - [ ] constrained and mixed BO
  - [ ] multi-fidelity and cost-aware optimization
  - [ ] BO + local NLP hybrids
  - [ ] autonomous-lab and scientific-agent systems

### 4. Implement the forward optimization ladder

- [ ] Treat the comparison ladder as:
  - [ ] IPOPT multi-start on fixed layouts
  - [ ] direct MINLP where tractable
  - [ ] constrained mixed-space BO baseline
  - [ ] BO→IPOPT hybrid
  - [ ] agent-guided BO or agent-guided BO→IPOPT
- [ ] Make sure each rung has:
  - [ ] a precise implementation target
  - [ ] a benchmark interface
  - [ ] a fair comparison story

### 5. Narrow and benchmark the agent role

- [ ] Restrict the agent role to:
  - [ ] ranking candidate batches
  - [ ] choosing `EXPLORE` / `EXPLOIT` / `VERIFY` / `DIAGNOSE`
  - [ ] choosing fidelity level
  - [ ] emitting structured evaluation memos
- [ ] Avoid evaluating the agent as a free-form final-setting generator
- [ ] Document exactly what deterministic code handles vs what the LLM handles
- [ ] Keep explicit limits visible:
  - [ ] no claim of global optimality
  - [ ] IPOPT remains local
  - [ ] agent allocates evaluation budget rather than replacing solver math

## Immediate next actions

### A. Benchmark canonicalization
- [ ] pick the canonical Phase 3 strategy family
- [ ] update docs and scripts to match that choice
- [ ] define the canonical metric set:
  - [ ] best feasible objective vs cumulative cost
  - [ ] time to first feasible point
  - [ ] feasibility rate
  - [ ] regret / gap to best-known
  - [ ] promotion efficiency across fidelities
- [ ] make the benchmark budget-normalized, not merely iteration-matched

### B. Research layer bootstrap
- [ ] create `docs/research/` structure
- [ ] seed it with the initial paper list from the roadmap
- [ ] mark `research.md` explicitly as a run log / working note, not the canonical literature layer

### C. Method implementation path
- [ ] define the interface for the constrained mixed-space BO baseline
- [ ] define the handoff contract from BO to IPOPT refinement
- [ ] define what evidence the agent sees before making a policy choice

## Publication-safety checks

- [ ] no benchmark number should appear in a paper-facing doc without an explicit supporting artifact
- [ ] no method claim should survive if the current code path does not support it
- [ ] no doc should imply “LLM replaces optimizer”
- [ ] no result summary should outrun the canonical artifact chain

## Definition of done for the next milestone

The next milestone is complete when:

- [ ] the strategy family is canonical and consistently named
- [ ] the Phase 2 → Phase 3 artifact contract is explicit
- [ ] the research layer exists and is populated with the seed literature
- [ ] the constrained mixed-space BO baseline has a concrete implementation plan
- [ ] the BO→IPOPT hybrid has a clear interface and benchmark role
- [ ] the agent role is written as a narrow policy layer, not a monolithic optimizer

## Short version

The project is no longer mainly blocked by cleanup.

It is now blocked by:

1. benchmark canonicalization
2. research-layer construction
3. cost-aware mixed BO baseline definition
4. BO→IPOPT hybrid definition
5. disciplined narrowing of the agent role
