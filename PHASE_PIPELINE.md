# Three-Phase Optimization Pipeline: Fixed Eval → Optimization → BO Surrogates

## Overview

A hierarchical approach to find global optima across the SMB design space and build accurate surrogate models for agent-guided optimization.

```
Phase 1: Quick Screening        Phase 2: Optimization           Phase 3: BO Surrogates
┌─────────────────────┐        ┌──────────────────────┐        ┌──────────────────────┐
│ Fixed Flow Eval     │        │ Real Optimization    │        │ Agent-Guided BO      │
├─────────────────────┤        ├──────────────────────┤        ├──────────────────────┤
│ • 31 NC configs     │        │ • Top 5-10 NCs       │        │ • Fit BO models      │
│ • Default flows     │   →    │ • Optimize flows     │   →    │ • Agent prioritizes  │
│ • ~1 min total      │        │ • Hard constraints   │        │ • Explores best      │
│ • Rank by baseline  │        │ • Max productivity   │        │ • Confirms global    │
│ • Data: baseline J  │        │ • ~10 min total      │        │ • Data: J,pu,rec     │
└─────────────────────┘        └──────────────────────┘        └──────────────────────┘
          ↓                              ↓                              ↓
    Identify top NCs            Collect optimization data      Train GP/DNN/PINN models
    for Phase 2                 (productivity, purity, rec)    on outputs (3 metrics)
```

---

## Phase 1: Fixed Flow Evaluation (Smoke Tests)

**Purpose**: Quick baseline to rank NC configurations

**What it does**:
- Evaluates each of 31 NC configs **once** with fixed default flows
- Uses reference flows from NOTEBOOK_SEEDS
- Each eval runs IPOPT from that single starting point
- Captures: productivity (J), purity, recovery at fixed flows

**Configuration**:
```bash
# Fixed default flows
Ffeed = 1.3 ml/min
Fdes = 1.2 ml/min
Fex = 0.9 ml/min
F1 = 2.2 ml/min (zone 1 base)
tstep = 9.4 min
```

**Results**:
- 31 data points (one per NC)
- Baseline productivity for ranking
- Identify top 5-10 NCs for Phase 2

**Time**: ~1 minute (low fidelity: nfex=5, nfet=2, ncp=1)

**Runners**:
- `benchmarks/lhs_only_runner.py` - LHS physics ranking
- `benchmarks/bo_gp_runner.py` - BO+GP guided selection

---

## Phase 2: Constrained Optimization (Real Optima)

**Purpose**: Find true optimal flows for each top-ranked NC

**What it does**:
- Takes top 5-10 NCs from Phase 1
- Runs **real optimization** with IPOPT as optimizer
- Unfixes all 5 flow variables: [Ffeed, Fdes, Fex, F1, tstep]
- Applies hard constraints:
  - Purity (MeOH-free, extract) ≥ **0.70** (exploratory)
  - Recovery (GA) ≥ **0.90**
  - Recovery (MA) ≥ **0.90**
  - Max pump flow ≤ **3.0** ml/min
- Maximizes: **Productivity (J)**

**What we collect**:
- Optimized flows for each NC
- Productivity (objective)
- Purity (at optimum)
- Recovery (GA & MA, at optimum)
- This is the **Pareto frontier** data

**Results**:
- 50-100 data points (5-10 NCs × multiple flows each)
- Shows true optima vs Phase 1 baseline
- Reveals flow interactions and constraints

**Time**: ~10 minutes (medium fidelity: nfex=6, nfet=3, ncp=2)

**Script**: `slurm/pace_smb_phase2_optimization.slurm`

**Key differences from Phase 1**:
| Aspect | Phase 1 | Phase 2 |
|--------|---------|---------|
| Flows | **Fixed** | **Optimized** |
| Purity constraint | None | ≥ 0.70 |
| Recovery constraint | None | ≥ 0.90 |
| Objective | Evaluate only | **Maximize** |
| Iterations | 31 × 1 | 5-10 × many |

---

## Phase 3: BO Surrogates & Agent Optimization

**Purpose**: Build accurate predictive models and find global optimum via agent guidance

**What BO learns**:
- Three independent surrogate models (GP, DNN, PINN)
- Each predicts the **three outputs** from Phase 2 data:
  1. **Productivity** (J) - main objective
  2. **Purity** (extract, MeOH-free) - constraint metric
  3. **Recovery** (GA & MA) - constraint metric

**BO as calculator**:
- Each BO method independently predicts best (productivity, purity, recovery) for all 31 NCs
- Returns predictions: `{best_config, J_pred, purity_pred, recovery_pred, uncertainty}`

**Agent's role**:
- Receives predictions from all 3 BO methods
- Analyzes agreement/disagreement:
  - **Consensus**: All agree on best → exploit that region
  - **Disagreement**: Explore promising gaps between predictions
  - **Risk-adjusted**: Balance exploitation (high productivity) vs exploration (constraint safety)
- Decides which NC+flows to evaluate next

**Agent decision patterns**:
```python
if gp_pred == dnn_pred == pinn_pred:
    # Strong consensus → exploit this region
    agent.prioritize("exploit", consensus_config)
elif gp.productivity > pinn.productivity but pinn.constraint_margin > gp.margin:
    # Trade-off between objective and constraint safety
    agent.prioritize("risk_adjusted", gp_config, caution_level="medium")
else:
    # Explore disagreement region
    agent.prioritize("explore", gap_region)
```

**Expected performance**:
- Converges faster than single BO method
- Finds regions that single method might miss
- Agent adapts to surrogate uncertainty/disagreement
- Can confirm global optimum with high confidence

**Data pipeline**:
```
Phase 1 results (31 evals) 
    ↓
Phase 2 results (50-100 evals) 
    ↓
BO training data: (NC, flows) → (J, purity, recovery)
    ↓
Three surrogates: GP, DNN, PINN
    ↓
Agent receives predictions → decides next config
    ↓
Evaluate selected config → update surrogates
    ↓
Repeat until convergence or budget exhausted
```

---

## Why This Pipeline Works

1. **Phase 1** (1 min)
   - No optimization overhead
   - Quickly rank all 31 NCs
   - Eliminates obviously poor choices

2. **Phase 2** (10 min)
   - Focuses on top NCs only
   - Finds real optima under constraints
   - Collects rich data: productivity, purity, recovery across design space

3. **Phase 3** (time budget)
   - Builds surrogates from diverse data
   - Agent exploits complementary strengths of BO methods
   - Finds and confirms global optimum

**Total data collected**: ~100-150 evaluations across all phases
- Enough for 3 independent BO models
- Diverse: includes both baseline and optimized points
- Rich: captures all 3 output metrics

**Why BO on outputs (J, purity, recovery)?**
- Single-output BO (J only) might miss constraint-respecting regions
- Multi-output BO learns trade-offs and Pareto frontier
- Agent can evaluate risk: "high J but low margin on recovery" vs "lower J but safe recovery"

---

## Execution Checklist

- [ ] **Phase 1**: Run smoke tests (6278261, 6278262) → Wait for completion
- [ ] **Phase 1 results**: Extract top 5-10 NCs from artifact JSONs
- [ ] **Phase 2**: Update NC list in `pace_smb_phase2_optimization.slurm`
- [ ] **Phase 2**: Submit optimization job → Wait for completion  
- [ ] **Phase 2 results**: Collect productivity/purity/recovery data
- [ ] **Phase 3**: Train BO models (GP/DNN/PINN) on Phase 2 data
- [ ] **Phase 3**: Implement agent-guided multi-BO calculator
- [ ] **Phase 3**: Run agent for exploration budget
- [ ] **Validation**: Compare Phase 1 baseline vs Phase 2 optimized vs Phase 3 global

---

## Expected Outcomes

**Phase 1 smoke test results** (after 1 min):
```json
{
  "method": "LHS-Only",
  "best_config": [2, 2, 2, 2],
  "best_productivity": 45.2,
  "all_nc_results": {...}
}
```

**Phase 2 optimization results** (after 10 min):
```json
{
  "nc": [2, 2, 2, 2],
  "optimized_flows": {
    "Ffeed": 1.5,
    "Fdes": 1.1,
    "Fex": 0.8,
    "F1": 2.4,
    "tstep": 9.8
  },
  "productivity": 52.1,
  "purity": 0.72,
  "recovery_ga": 0.91,
  "recovery_ma": 0.92
}
```

**Phase 3 BO predictions** (continuous):
```python
gp_pred = {"best_config": [2, 2, 2, 2], "J": 52.3, "purity": 0.73, "recovery": 0.92}
dnn_pred = {"best_config": [2, 2, 2, 2], "J": 52.1, "purity": 0.72, "recovery": 0.91}
pinn_pred = {"best_config": [1, 2, 2, 3], "J": 50.9, "purity": 0.75, "recovery": 0.93}

# Agent: Consensus on [2,2,2,2] but PINN suggests [1,2,2,3] has better constraint margin
agent_decision = "exploit [2,2,2,2] with caution; verify constraint margin"
```
