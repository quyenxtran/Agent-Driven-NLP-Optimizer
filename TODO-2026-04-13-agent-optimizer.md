# TODO — Agent-Orchestrated Optimization Project

Date: 2026-04-13

## Goal

Turn the framing in `Suggest-2026-04-13.md` into an implementable research/software plan for an **agent + optimizer tools** system, where the agent orchestrates optimization effort rather than replacing numerical optimization.

## Core framing to preserve

> The agent does not replace numerical optimization; it allocates optimization effort and experimental budget more intelligently across rounds.

## Deliverables

### 1. Problem statement and research framing
- [x] Write a concise problem statement
- [x] Define the role of the agent vs optimizer clearly
- [x] Write baseline hierarchy:
  - [x] tool-only baseline
  - [x] hybrid optimizer baseline
  - [x] agent + optimizer tools
- [x] Draft candidate paper titles / paradigm names

### 2. System architecture
- [x] Define main components:
  - [x] agent/controller
  - [x] optimizer tools interface
  - [x] fidelity manager
  - [x] experiment/simulation runner
  - [x] belief/model state
  - [x] failure analyzer
  - [x] budget tracker
- [x] Define data flow between rounds
- [x] Define decision points for the agent
- [x] Specify what information the agent observes before each action

### 3. Action space design
- [x] Enumerate possible agent actions
  - [x] select solver
  - [x] select fidelity level
  - [x] choose explore vs exploit
  - [ ] choose restart / warm-start policy
  - [x] choose batch size / candidate set purpose
  - [x] trigger local refinement
  - [x] request retry / reinitialize after failure
- [x] Define action constraints under budget
- [x] Define termination conditions

### 4. State, reward, and budget model
- [x] Define optimization state representation
- [x] Define uncertainty / belief summary passed to the agent
- [x] Define cost model:
  - [x] simulation cost
  - [ ] experiment cost
  - [x] failed run cost
  - [ ] wall-clock budget
- [x] Define success metrics:
  - [x] best feasible objective
  - [ ] regret / sample efficiency
  - [x] feasible-hit rate
  - [x] cost-to-solution

### 5. Baseline implementations
- [x] Specify tool-only baselines
  - [x] IPOPT only
  - [x] BO only
  - [x] MINLP only
- [x] Specify hybrid baselines
  - [x] BO → IPOPT
  - [x] BO + MINLP
  - [x] multi-fidelity BO
- [x] Define fair comparison budget for all baselines

### 6. Agent policy implementation plan
- [x] Decide first implementation mode:
  - [x] rule-based agent
  - [ ] LLM-guided agent
  - [ ] hybrid rule + LLM agent
- [ ] Define agent prompt / policy schema
- [x] Define structured decision output format
- [x] Add guardrails so the agent cannot invent unsupported tool actions
- [x] Define logging for rationale, action, outcome, and cost

### 7. Failure handling and robustness
- [x] Define failure taxonomy:
  - [x] infeasible region
  - [x] bad initialization
  - [x] optimizer numerical failure
  - [x] surrogate/model misspecification
  - [x] noisy or inconsistent experiment
- [x] Map each failure class to a next-step policy
- [x] Add retry and escalation rules

### 8. Evaluation plan
- [ ] Pick benchmark tasks
- [x] Define constrained optimization scenarios
- [x] Define expensive-evaluation scenarios
- [x] Define multi-fidelity scenarios
- [x] Measure benefit of orchestration decisions separately from optimizer quality
- [x] Plan ablations:
  - [x] no failure reasoning
  - [x] no fidelity choice
  - [x] fixed solver schedule
  - [x] no local refinement handoff

### 9. Paper writing assets
- [x] Create an outline for a paper or proposal
- [x] Draft the core contribution statement
- [x] Draft the methods overview paragraph
- [x] Draft the autonomous-lab motivation paragraph
- [ ] Clean and complete BibTeX references

### 10. Code/repo scaffolding
- [x] Create a project directory for this work
- [x] Add README with framing and scope
- [x] Add `docs/architecture.md`
- [x] Add `docs/evaluation-plan.md`
- [x] Add `docs/baselines.md`
- [x] Add `src/agent_policy/`
- [x] Add `src/orchestrator/`
- [x] Add `src/optimizers/`
- [x] Add `src/evaluation/`
- [x] Add `tests/`

## Recommended implementation order

### Phase 1 — Define the concept cleanly
- [x] Create architecture doc
- [x] Create baseline comparison doc
- [x] Create evaluation-plan doc

### Phase 2 — Build minimal orchestrator
- [x] Implement action schema
- [x] Implement round-state schema
- [x] Implement a simple rule-based agent
- [x] Implement stub optimizer interfaces
- [x] Implement logging

### Phase 3 — Add intelligence and experiments
- [ ] Add LLM-guided decision mode
- [x] Add failure interpretation module
- [x] Add fidelity selection logic
- [x] Add BO → IPOPT handoff logic

### Phase 4 — Benchmark and write
- [ ] Run baselines
- [ ] Run ablations
- [ ] Summarize results
- [ ] Draft paper sections

## Immediate next actions

1. [ ] Add LLM-guided decision mode
2. [ ] Add benchmark tasks beyond the deterministic stub environment
3. [ ] Replace optimizer stubs with real BO/IPOPT integrations
4. [ ] Run baselines and ablations
5. [ ] Clean and complete BibTeX references

## Notes

- Keep the claim modest and defensible.
- Position the agent as an **orchestration/control layer**.
- Do not claim the LLM is a replacement for numerical solvers.
- Emphasize budget allocation, solver selection, fidelity selection, and failure-aware decision-making.
