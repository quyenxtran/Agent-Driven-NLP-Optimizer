# Architecture and Status Guide

Date: 2026-04-13

## What this project is

AutoResearch-SMB is best understood as an **agent-orchestrated optimization system** for SMB process search.

The important division of labor is:
- **Numerical optimizers and SMB model code** perform the mathematical and physical simulation work.
- **Agent logic** decides how to allocate search effort, which candidate to try next, how to use evidence from prior runs, and when to escalate or redirect the search.

In other words:

> The agent does not replace numerical optimization; it allocates optimization effort and experimental budget more intelligently across rounds.

## Source of truth

### Current status / planning
- **Primary current plan:** `PLAN.md`
- **Current repo-local summary:** `CURRENT_STATUS.md`
- **Current project TODO:** `TODO-2026-04-13-agent-optimizer.md`

### Archived / historical status note
- `LIVE_STATUS.md` is archival and should not be treated as the current source of truth.

## Main code map

### Physical / optimization core
- `src/sembasmb/model.py`
- `src/sembasmb/optimization.py`
- `src/sembasmb/solver.py`
- `src/sembasmb/config.py`
- `src/sembasmb/metrics.py`

These files define the SMB model, optimization problem, solver configuration, and metrics.

### Agent orchestration
- `benchmarks/agent_runner.py` — main orchestration loop
- `benchmarks/agent_policy.py` — task ordering, screening, gating, and policy rules
- `benchmarks/agent_scientists.py` — proposer/reviewer/executive behavior
- `benchmarks/agent_db.py` — SQLite history and convergence tracking
- `benchmarks/agent_evidence.py` — evidence extraction and grounding
- `benchmarks/agent_results.py` — result parsing and ranking helpers
- `benchmarks/agent_llm_client.py` — LLM client wrapper

### Baselines / evaluation
- `benchmarks/bo_gp_baseline.py`
- `benchmarks/lhs_only_runner.py`
- `benchmarks/phase3_strategy*.py`
- `benchmarks/evaluate_phase3_strategies.py`

## Practical interpretation

### What the agent is responsible for
- proposing the next simulation / optimization candidate
- balancing explore / exploit / verify behavior
- using prior evidence from SQLite history, heuristics, and recent outcomes
- deciding how to spend limited search budget
- coordinating reviewer and executive moderation logic

### What the numerical optimizer is responsible for
- solving the continuous nonlinear subproblem
- enforcing model equations and constraints
- returning candidate performance metrics and feasibility outcomes

### Why this matters for writing

When describing the method in papers, slides, or README text, avoid saying or implying:
- the LLM itself is the optimizer
- the LLM replaces IPOPT or other numerical solvers
- the agent proves global optimality

Prefer language like:
- agent-guided optimization
- agent-orchestrated constrained optimization
- reasoning-guided experiment / optimization loop
- agent-mediated allocation of solver and evaluation budget

## Recommended reading order for new contributors

1. `README.md`
2. `PLAN.md`
3. `CURRENT_STATUS.md`
4. this file
5. `benchmarks/agent_runner.py`
6. `benchmarks/agent_policy.py`
7. `src/sembasmb/optimization.py`

## Current repo need

The main need is not to build a toy orchestrator from scratch. The repo already contains a substantial real system.

The current need is to keep three things aligned:
1. scientific framing
2. experimental status
3. actual implementation
