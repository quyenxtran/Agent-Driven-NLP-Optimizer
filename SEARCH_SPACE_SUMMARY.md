# SMB Optimization Search Space - Complete Summary

## Problem Structure

```
┌─────────────────────────────────────────────────────────────┐
│ Two-Level Hierarchical Optimization Problem                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ LEVEL 1: Discrete NC Configuration Selection               │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Choose: [nc0, nc1, nc2, nc3] where:                    │ │
│ │   - Each nc ∈ {1, 2, 3, 4}                             │ │
│ │   - Constraint: sum(nc) = 8 (CRITICAL)                │ │
│ │   - Valid configs: 31 total                            │ │
│ │                                                         │ │
│ │ Example valid: [1,1,2,4], [2,2,2,2], [1,3,2,2]        │ │
│ └─────────────────────────────────────────────────────────┘ │
│              ↓                                              │
│ LEVEL 2: Continuous Flow/Timestep Optimization             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ For each NC config, optimize:                          │ │
│ │                                                         │ │
│ │   Variables (5-dimensional continuous space):          │ │
│ │   • tstep (switching time): [8.0, 12.0] min           │ │
│ │   • ffeed (feed flow): [0.5, 2.5] ml/min              │ │
│ │   • fdes (desorbent): [0.5, 2.5] ml/min               │ │
│ │   • fex (extract): [0.5, 2.5] ml/min                  │ │
│ │   • f1 (zone 1 base): [0.5, 5.0] ml/min               │ │
│ │                                                         │ │
│ │   Derived (automatic):                                 │ │
│ │   • fraf = ffeed + fdes - fex (mass balance)           │ │
│ │   • All other zone flows (computed from balance)       │ │
│ │                                                         │ │
│ │   Constraints:                                         │ │
│ │   • max(all flows) ≤ 3.0 ml/min (pump limit)          │ │
│ │   • purity ≥ 0.60 (extract purity goal)                │ │
│ │   • recovery ≥ 0.75 (both components)                  │ │
│ │                                                         │ │
│ │   Objective:                                           │ │
│ │   • Maximize J = productivity (extract quality)         │ │
│ └─────────────────────────────────────────────────────────┘ │
│              ↓                                              │
│ OUTCOME:                                                    │
│ • Best objective value J for each NC                        │
│ • Agent/Algorithm ranks NCs by J                            │
│ • Iteratively refines best NCs                              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Discrete Search Space (NC Configurations)

### All 31 Valid Configurations (sum=8, each nc ∈ [1,4])

```
By imbalance (max - min):

Balanced (imbalance = 0-1):
  [2, 2, 2, 2] - perfect square (1 config)
  [1,1,3,3], [1,3,1,3], [1,3,3,1], [3,1,1,3], [3,1,3,1], [3,3,1,1] - symmetric (6)
  [1,2,2,3], [1,2,3,2], [1,3,2,2], [2,1,2,3], [2,1,3,2], [2,2,1,3],
  [2,2,3,1], [2,3,1,2], [2,3,2,1], [3,1,2,2], [3,2,1,2], [3,2,2,1] - variants (12)

Medium Imbalance (imbalance = 2-3):
  [1,1,2,4], [1,1,4,2], [1,2,1,4], ... (8 configs)

High Imbalance (imbalance = 3):
  [1,1,1,5] - INVALID (5 > 4)
  [1,4,1,2], [1,4,2,1], [4,1,1,2], [4,1,2,1], [4,2,1,1] (5 configs)

Total: 31 valid
```

### Physics Scoring (from physics_filter.py)

```
Score = 0.4 × selectivity + 0.3 × throughput - 0.3 × difficulty

Selectivity:   Prefers more columns (longer residence time)
Throughput:    Prefers more columns (more adsorbent capacity)
Difficulty:    Penalizes imbalance and high column count

Result: Best scores ~41.67 (balanced, small/medium)
        Worst scores ~44.67 (imbalanced, large)
        Range: Very narrow (all 31 are reasonable)
```

**Top 5 Ranked Configs:**
1. [1, 1, 2, 4] → score 41.67
2. [1, 1, 3, 3] → score 41.67
3. [1, 1, 4, 2] → score 41.67
4. [1, 2, 1, 4] → score 41.67
5. [1, 2, 4, 1] → score 41.67

---

## Continuous Search Space (Flow Optimization)

### Bounds per Variable

| Variable | Lower | Upper | Range | Unit | Meaning |
|----------|-------|-------|-------|------|---------|
| tstep | 8.0 | 12.0 | 4.0 | minutes | Switching cycle time |
| ffeed | 0.5 | 2.5 | 2.0 | ml/min | Feed injection rate |
| fdes | 0.5 | 2.5 | 2.0 | ml/min | Desorbent circulation |
| fex | 0.5 | 2.5 | 2.0 | ml/min | Extract withdrawal |
| f1 | 0.5 | 5.0 | 4.5 | ml/min | Zone 1 base flow |

### Flow Balance Equation (Automatic)

```
Fraf = Ffeed + Fdes - Fex

Example:
  If ffeed=1.0, fdes=2.0, fex=1.5
  Then fraf = 1.0 + 2.0 - 1.5 = 1.5 ml/min

Zone flows derived from:
  F1, Fraf, Fex, Fdes → compute zone velocities
```

### Active Pump Constraint

**Critical**: max(ffeed, fdes, fex, f1) ≤ 3.0 ml/min

This reduces feasible region significantly:
- F1 ∈ [0.5, 5.0] becomes [0.5, 3.0]
- Other bounds unchanged but interdependent

---

## Problem Complexity

### Size Comparison

```
Discrete Space:
  Full: 4^4 = 256 possible configs
  Valid (sum=8): 31 configs (12% of space)
  
Continuous Space (per NC):
  Dimensions: 5
  Density: Infinite (continuous)
  Grid approximation (10 pts/dim): 100,000 evaluations

Total Search Space:
  31 NCs × ∞ continuous = Mixed-Integer Nonlinear Program (MINLP)
  
Practical Tractability:
  - Can enumerate all 31 NC configs ✓
  - Can solve IPOPT for each config ✓
  - Total: 31 NLP solves = ~8-25 min (at low fidelity)
  - Cannot grid search continuous space ✗
```

### Optimization Approach vs Grid Search

```
❌ GRID SEARCH:
   [tstep, ffeed, fdes, fex, f1] with 10 points each
   = 10^5 = 100,000 simulations per NC
   × 31 NCs = 3.1M simulations
   Time: ~100,000 core-hours (infeasible)

✅ NLP OPTIMIZATION:
   [tstep, ffeed, fdes, fex, f1] with IPOPT solver
   = 1 solve per NC
   × 31 NCs = 31 solves
   Time: ~5-15 min (feasible, we do this)

✅ AGENT-GUIDED:
   Start: 31 NCs ranked by physics heuristics
   Agent: Explores best→good→promising based on history
   Active refinement: ~8-40 iterations in 11 hours
   Quality: Often finds global or near-global optima
```

---

## Methodology: How Algorithms Use This Space

### 1. LHS + Agent (Proposed)

```
Step 1: Enumerate 31 valid NC configs (discrete space)
Step 2: Rank by physics heuristics (LHS scoring)
Step 3: Agent iteratively:
        a) Select best unexplored NC from ranking
        b) Run IPOPT on that NC (continuous optimization)
        c) Record J value, update beliefs
        d) Decide next NC based on:
           - History of results
           - Exploration vs exploitation
           - Physics insights
Step 4: Repeat until time budget exhausted

Expected: 8-40 iterations in 11 hours
Quality: Often finds J > 50 (strong performance)
```

### 2. BO+GP (Baseline)

```
Step 1: Enumerate 31 valid NC configs (discrete space)
Step 2: Randomly sample 3 initial configs
Step 3: Fit GP to results in 5-D continuous + discrete NC space
Step 4: Use Expected Improvement to select next config
Step 5: Run IPOPT on selected config
Step 6: Update GP model
Step 7: Repeat until time budget exhausted

Expected: ~8-25 iterations (more systematic, less exploration)
Quality: Often finds local optima, reproducible
```

### 3. LHS-Only (Pure Ranking)

```
Step 1: Enumerate and rank all 31 configs by physics
Step 2: For each config in order:
        a) Run IPOPT (continuous optimization)
        b) Record J value
Step 3: Continue until time budget or all 31 evaluated

Expected: 8-31 iterations (deterministic, no learning)
Quality: Good coverage, but no exploitation of best regions
```

---

## Summary Statistics

```
╔════════════════════════════════════════════════════════════╗
║ SMB OPTIMIZATION PROBLEM DIMENSIONS                       ║
╠════════════════════════════════════════════════════════════╣
║ Discrete (NC):                                            ║
║   - Valid configurations: 31                              ║
║   - Decision type: Which NC topology to optimize           ║
║                                                           ║
║ Continuous (Flows):                                       ║
║   - Decision variables: 5 (tstep, ffeed, fdes, fex, f1)  ║
║   - Constraints: 2 major (pump limit, mass balance)       ║
║   - Objectives: 4 (purity, recovery, productivity)        ║
║                                                           ║
║ Combined Problem:                                         ║
║   - Type: Mixed-Integer Nonlinear Program (MINLP)         ║
║   - Solver: IPOPT for continuous, agent for discrete      ║
║   - Feasible evaluations: ~1 per minute (IPOPT)           ║
║   - Time budget: 11 hours → ~660 minutes → ~660 evals     ║
║   - Practical iterations: 8-60 (11h budget)               ║
╚════════════════════════════════════════════════════════════╝
```

---

## Interpretation

✅ **31 NC configs** = Manageable discrete space (can enumerate)
✅ **5-D continuous** = Standard NLP problem (IPOPT solves well)
✅ **Pump limit (3.0 ml/min)** = Active constraint (reduces feasibility)
✅ **Constrained total cols (8)** = Physics-informed, reduces search

⚠️ **No closed-form solution** = Need numerical optimization
⚠️ **Multi-objective tradeoffs** = Can't maximize everything
⚠️ **Nonlinear interactions** = Hard to predict best config a priori

**Why Agent+LHS works**: 
- Agents exploit history + heuristics together
- LHS gives good starting ranking from physics
- Agent learns which NC families are promising
- Can refine best candidates in continuous space
