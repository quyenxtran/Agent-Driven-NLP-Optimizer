# PHASE_PIPELINE_V2.md

Archived pipeline design note.

This file describes an earlier redesigned pipeline concept and should be treated as **historical planning context**, not the current canonical plan.

## Current source of truth
- Read **`PLAN.md`** for the most up-to-date project plan.
- Use `CURRENT_STATUS.md` and `docs/DOCUMENTATION_INDEX.md` to navigate active status docs.

## Why this file is archived
It describes an older multi-strategy pipeline design with assumptions that are no longer the primary reconciled plan.

---

# Redesigned Pipeline: Phase 2 → Phase 3 (4 Strategies) → Phase 4

## Overview

Remove initial screening phase. Use Phase 2 to generate comprehensive screening data via N-dimensional LHS. Phase 3 becomes a strategy comparison framework showing how multi-BO + agent outperforms alternatives. Phase 4 validates the winner.

```
Phase 2: Foundation Data (100 LHS seeds/NC, all 31 NCs)
    ↓
    ~300-350 feasible seed evaluations (screening data)
    ↓
Phase 3: Strategy Comparison (4 alternatives)
    ├─ Strategy 1: Regular LHS (screen → optimize top 5)
    ├─ Strategy 2: BO Baseline (fit GP, optimize top BO predictions)
    ├─ Strategy 3: Agent+LHS (intelligent NC ranking)
    └─ Strategy 4: Agent+BO (multi-BO + agent prioritization)
    ↓
    Compare best J across all 4 strategies
    ↓
Phase 4: Final Validation (STRICT constraints on winner)
```

---

## Phase 2: Foundation Data Generation

**Purpose**: Generate comprehensive screening data across design space using LHS sampling.

**Input**: All 31 NC configurations, 100 LHS seeds per NC

**Process**:
```
For each NC:
  1. Generate 100 LHS seeds (N-dimensional, configurable bounds)
  2. Screen all 100 at LOW fidelity (nfex=4, nfet=2)
  3. Filter: keep feasible (purity≥0.20, recovery≥0.20, recovery_ma≥0.20)
  4. Expected: ~25-30 feasible seeds per NC
```

**Output**: `phase2_summary.json`
```json
{
  "n_ncs": 31,
  "n_seeds_per_nc": 100,
  "results": [
    {
      "nc": [n0, n1, n2, n3],
      "all_seed_results": [
        {
          "seed_idx": 0-99,
          "metrics": {
            "productivity": float,
            "purity": float,
            "recovery_ga": float,
            "recovery_ma": float
          },
          "feasible": bool
        }
      ]
    }
  ]
}
```

**Expected Results**: 
- 31 NCs × ~25-30 feasible seeds ≈ 775-930 feasible screening points
- Covers design space systematically via LHS
- Provides foundation for all Phase 3 strategies

**Important Note**: All Phase 3 strategy files reference `artifacts/phase2_lhs_seeding/phase2_summary.json`

**Key Feature**: N-dimensional LHS
- Generic for any design space
- Configurable `var_names` and `bounds`
- Default: 5D SMB flow space
- Deterministic (`seed=42`) for reproducibility

---

## Phase 3: Strategy Comparison Framework

**Purpose**: Demonstrate that multi-BO + agent beats all alternative approaches.

**Input**: Phase 2 screening data (~300-350 feasible points per full run)

**4 Strategies Compared**:

### Strategy 1: Regular LHS
```
Approach: Naive LHS → pick top 5 by productivity → optimize
├─ Analyze Phase 2B screening results
├─ Rank all NCs by best seed productivity
├─ Select top 5 DISTINCT NCs
└─ Optimize each with HIGH fidelity (nfex=10, nfet=5)

Result: Simple baseline (no intelligence)
Expected J: Lower (only using screening productivity)
```

### Strategy 2: BO Baseline
```
Approach: Single BO method → predict → optimize
├─ Fit BO(GP) to screening data
├─ Predict all NCs (mean + uncertainty)
├─ Select top 5 by BO prediction
└─ Optimize each with HIGH fidelity (nfex=10, nfet=5)

Result: Single BO method (no multi-BO, no agent)
Expected J: Moderate (BO guidance but limited)
Tool availability:
  - GP: always (fit to screening)
  - DNN: after ~100 points
  - PINN: after ~150 points
```

### Strategy 3: Agent + LHS
```
Approach: Agent analyzes screening → intelligent selection → optimize
├─ Agent receives screening data
├─ Agent applies heuristics & domain knowledge
├─ Agent intelligently ranks NCs (not just by productivity)
├─ Select top 5 by agent reasoning
└─ Optimize each with HIGH fidelity (nfex=10, nfet=5)

Result: Agent intelligence + LHS (no BO)
Expected J: Moderate-High (agent heuristics useful)
Agent reasoning: e.g., "NC [2,2,2,2] is balanced → likely robust"
```

### Strategy 4: Agent + Multi-BO ⭐
```
Approach: Multi-BO + Agent (full intelligence)
├─ Fit all available BO methods (GP → DNN → PINN)
├─ Agent receives predictions from all methods
├─ Agent analyzes:
│   ├─ Consensus: All agree on region?
│   ├─ Disagreement: Methods suggest different optima?
│   └─ Trade-off: Risk vs reward?
├─ Agent selects top 5 intelligently
└─ Optimize each with HIGH fidelity (nfex=10, nfet=5)

Result: Full intelligence (multi-BO + agent prioritization)
Expected J: Highest (multiple tools + smart agent)
Agent reasoning: e.g., "DNN predicts J≈63, PINN only J≈58.
                       DNN more aggressive. Try DNN.
                       If fails, PINN is safer fallback."

Tool availability:
  - GP: from start (fit to screening ~300 pts)
  - DNN: immediately (300 > 100)
  - PINN: immediately (300 > 150)
```

---

## Phase 3 Output

**File**: `phase3_comparison_summary.json`
```json
{
  "screening_data_points": 300-350,
  "strategies_compared": ["1", "2", "3", "4"],
  "results": {
    "Regular LHS": {
      "strategy": "Regular LHS",
      "best_config": [n0, n1, n2, n3],
      "best_j": float,
      "evaluations": 5
    },
    "BO Baseline (Single GP)": {
      "strategy": "BO Baseline (Single GP)",
      "best_config": [...],
      "best_j": float,
      "evaluations": 5
    },
    "Agent + LHS": {
      "strategy": "Agent + LHS",
      "best_config": [...],
      "best_j": float,
      "evaluations": 5
    },
    "Agent + Multi-BO": {
      "strategy": "Agent + Multi-BO",
      "best_config": [...],
      "best_j": float,
      "evaluations": 5
    }
  }
}
```

**Expected Ranking**:
```
1st: Agent + Multi-BO    (best J, intelligent + comprehensive)
2nd: Agent + LHS         (good J, intelligent heuristics)
3rd: BO Baseline         (moderate J, single method)
4th: Regular LHS         (lowest J, no intelligence)
```

---

## Key Differences from Old Pipeline

| Aspect | Old | New |
|--------|-----|-----|
| **Old Phase 1** | 31 NC baseline evaluation | ❌ REMOVED |
| **Old Phase 2** | Fixed reference seeds | ➜ Refactored |
| **Phase 2** | N/A | ➜ **Foundation data generation (100 LHS/NC)** |
| **Phase 3** | N/A | ➜ **4-strategy comparison (separate files)** |
| **Phase 4** | N/A | ➜ **Final validation on winner** |
| **Purpose** | Single optimization | ➜ **Prove multi-BO beats alternatives** |
| **LHS** | 5D hardcoded | ➜ **N-dimensional generic** |

---

## Advantages of Redesign

✅ **Cleaner**: No redundant Phase 1 screening  
✅ **Comprehensive**: 300+ screening points vs 31 initial  
✅ **Fair comparison**: All strategies use same screening data  
✅ **Demonstrates value**: Agent+BO clearly beats alternatives  
✅ **Generalizable**: LHS works for any design space (not just SMB)  
✅ **Reproducible**: Deterministic seeding, same seeds for all NCs  

---

## Execution Checklist

- [ ] Phase 2 complete: 31 NCs × 100 seeds screened (~300+ feasible points)
- [ ] Phase 3: Run 4 strategies separately, compare best J across all
- [ ] Phase 3 results: Agent+BO wins (highest J, intelligent decisions)
- [ ] Phase 4: Validate winner with STRICT constraints (purity≥0.70, recovery≥0.90)
- [ ] Final report: Agent+BO achieves global optimum under production specs

---

## Next Steps

1. Run Phase 2: `sbatch slurm/pace_smb_phase2_lhs_seeding.slurm`
2. Wait for Phase 2 completion (~2-3 hours)
3. Run Phase 3 strategies (can run in parallel or sequential):
   - `sbatch slurm/pace_smb_phase3_strategy1.slurm`
   - `sbatch slurm/pace_smb_phase3_strategy2.slurm`
   - `sbatch slurm/pace_smb_phase3_strategy3.slurm`
   - `sbatch slurm/pace_smb_phase3_strategy4.slurm`
4. Compare results: Which strategy wins?
5. Run Phase 4 on winning strategy with strict constraints
