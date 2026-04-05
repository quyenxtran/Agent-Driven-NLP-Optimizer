# SMB Optimization Benchmark Suite - Comparison Framework

## Overview

This document describes the comprehensive benchmark suite for comparing optimization methods for SMB NC configuration search within the constrained space (sum=8, max pump flow=3.0 ml/min).

**Key Constraint**: All methods search within the same **31 valid configurations** (sum of NC dimensions = 8).

---

## Methods Compared

### 1. LHS + Agent (No Ranking)
**Method**: Latin Hypercube Sampling to initialize, then LLM agent explores
- Uses all 31 valid configs
- Agent selects next config based on reasoning (no physics ranking)
- Random initialization order

**Benchmarks**:
- Low (15 min): `slurm/pace_smb_27b_lhs_low_fidelity.slurm`
- Medium (4h): `slurm/pace_smb_27b_lhs_med_fidelity.slurm` 
- High (8h): `slurm/pace_smb_27b_lhs_high_fidelity.slurm`

**Expected**: ~8-10 iter (15min), ~15-20 iter (4h), ~30-40 iter (8h)

### 2. LHS + Agent (Physics-Ranked)
**Method**: LHS with physics-based scoring to rank configs, then agent explores
- Uses all 31 valid configs
- **Configs pre-ranked by selectivity/throughput/solver difficulty**
- Agent learns from initial ranking
- Flag: `--use-lhs-ranking`

**Benchmarks**:
- Low (15 min): `slurm/pace_smb_27b_smoke_test_lhs.slurm`
- Medium (4h): Can adapt from above
- High (8h): Can adapt from above

**Expected**: Same iteration counts as #1, but better config selection quality

### 3. BO+GP Baseline (Pure Deterministic)
**Method**: Bayesian Optimization with Gaussian Process, Expected Improvement acquisition
- No LLM involved
- Purely mathematical optimization
- Uses same 31 valid configs
- Sequential evaluation with GP surrogate

**Benchmarks**:
- Medium (4h): `slurm/pace_smb_27b_bo_gp_baseline.slurm`

**Expected**: ~15-25 iter (4h), systematic coverage, reproducible

---

## Configuration Space Density

```
Total valid NC configs (sum=8): 31
Enumerated space: {(nc0, nc1, nc2, nc3) | each in [1,4], sum=8}

Sample distribution (all methods):
  1,1,1,5  -> INVALID (5 > 4)
  1,1,2,4  -> VALID (first rank by score)
  1,1,3,3  -> VALID
  ...
  4,2,1,1  -> VALID
  4,4,0,0  -> INVALID (0 < 1)
```

**LHS Density**: 100% (all 31 configs can be sampled)
- No subsampling needed (space is already small and finite)
- All methods evaluate from the complete set

---

## Scoring Mechanism (Physics Filter)

**Selectivity Potential**: Longer zones better for separation
- Score: normalized by total columns (lower is better)
- Range: 0-100 scale

**Throughput Estimate**: More columns = higher capacity
- Score: same normalization as selectivity
- Range: 0-100 scale

**Solver Difficulty**: Balance vs complexity
- Penalty for imbalanced zones (max-min too high)
- Penalty for more columns (more constraints)
- Range: 0-100 scale

**Combined Score**: Weighted sum
- Default weights: selectivity=0.4, throughput=0.3, solver=-0.3
- Lower score = more preferred

**Example ranking**:
```
Rank 1: [1,1,2,4] -> 41.67 (very balanced, small)
Rank 2: [1,1,3,3] -> 41.67 (symmetric, medium)
Rank 3: [1,1,4,2] -> 41.67 (variations of top)
...
Rank 31: Various high-imbalance configs -> 44.67
```

---

## Comparison Metrics

### Primary Metrics

| Metric | Measurement | Expected Outcome |
|--------|-------------|------------------|
| **Iterations/Time** | # configs evaluated | LHS+Agent ≈ BO+GP; LHS ranks might enable earlier convergence |
| **Best Score Found** | Max objective value | BO+GP might find local optima; Agent might explore better |
| **Convergence Speed** | Iterations to best | LHS+Agent should converge faster with ranking |
| **Exploration Coverage** | % of 31 configs tried | BO+GP: systematic; Agent: may concentrate on promising areas |

### Secondary Metrics

| Metric | Measurement | Notes |
|--------|-------------|-------|
| **Config Diversity** | # unique configs evaluated | BO+GP more systematic; Agent may focus |
| **Physics Alignment** | Preference for balanced configs | LHS ranking explicit; BO+GP learns implicitly |
| **Solver Success Rate** | % of evals that converge | Should be ~80-90% for all |
| **Reproducibility** | Variance across seeds | BO+GP: deterministic; Agent: stochastic |

---

## Running the Benchmarks

### Quick Test (15 min)
```bash
# LHS + Agent (no ranking) smoke test
sbatch slurm/pace_smb_27b_lhs_low_fidelity.slurm

# LHS + Agent (physics-ranked) smoke test
sbatch slurm/pace_smb_27b_smoke_test_lhs.slurm
```

### Medium Fidelity (4 hours, ~15-20 iterations)
```bash
# LHS + Agent (physics-ranked) - medium
sbatch slurm/pace_smb_27b_lhs_med_fidelity.slurm

# BO+GP baseline - medium
sbatch slurm/pace_smb_27b_bo_gp_baseline.slurm
```

### High Fidelity (8 hours, ~30-40 iterations)
```bash
# LHS + Agent (physics-ranked) - high
sbatch slurm/pace_smb_27b_lhs_high_fidelity.slurm
```

### Full Sweep (All methods, 4 hours each)
```bash
# Submit all medium-fidelity runs
sbatch slurm/pace_smb_27b_lhs_med_fidelity.slurm     # LHS+Agent (no rank)
sbatch slurm/pace_smb_27b_bo_gp_baseline.slurm        # BO+GP
# Also run with --use-lhs-ranking separately or manually
```

---

## Result Analysis

### Output Directories
```
artifacts/lhs_bench_27b_low/     -> 15-min LHS results
artifacts/lhs_bench_27b_med/     -> 4-hour LHS results
artifacts/lhs_bench_27b_hi/      -> 8-hour LHS results
artifacts/bo_gp_bench_27b/       -> 4-hour BO+GP results
artifacts/parse_qwen27b_smoke_test_lhs/  -> LHS+ranking smoke test
```

### Key Files per Run
- `{run_name}.sqlite`: Evaluation history (agent only)
- `bo_gp_results.json`: BO+GP summary and iteration log
- `conversation_log.jsonl`: Agent reasoning/decisions (agent only)

### Analysis Script Template
```python
import json
import sqlite3

# BO+GP results
with open("bo_gp_results.json") as f:
    bo_results = json.load(f)
    print(f"BO+GP best score: {bo_results['best_score']}")
    print(f"BO+GP iterations: {bo_results['iterations']}")

# Agent results (from SQLite)
conn = sqlite3.connect("smb_agent_context.sqlite")
cursor = conn.cursor()
cursor.execute("SELECT nc, J FROM evaluations WHERE run_name = ? ORDER BY iteration DESC LIMIT 1", 
               (run_name,))
best_nc, best_j = cursor.fetchone()
print(f"Agent best score: {best_j}, config: {best_nc}")
```

---

## Hypothesis

**Predicted Outcome**:

1. **LHS + Agent (no ranking)**: Baseline agent performance
   - Expected: ~8 iter (15min), best J ~50-55
   - Reasoning: No pre-ordering, agent learns from scratch

2. **LHS + Agent (physics-ranked)**: Improved agent via hints
   - Expected: ~8 iter (15min), best J ~55-60
   - Reasoning: Agent starts with good configs, can exploit better

3. **BO+GP**: Systematic but potentially myopic
   - Expected: ~8-10 iter (15min), best J ~50-55
   - Reasoning: GP learns structure but may miss human insights

**Secondary Prediction**: 
- Agent+ranking likely finds more diverse configs (explores more of 31-space)
- BO+GP likely concentrates on local optima more quickly
- Iteration efficiency: BO+GP ≈ Agent; Quality: Agent+ranking > BO+GP > Agent

---

## Configuration Details

### All Methods
- Config space: 31 valid (sum=8 constraint)
- Solver: IPOPT with MA97 linear solver
- Fidelity: Low (4-5 finite elements), not production-quality
- Seeds: notebook reference seeds (deterministic initialization)
- Time budget: 4 hours standard (15 min smoke test)

### LHS + Agent Specifics
- LLM: Qwen 3.5 27B
- Three-scientist loop: A (proposer), B (reviewer), C (executive)
- Acquisition strategies: EXPLORE, EXPLOIT, VERIFY
- Learning: Updates hypotheses.json and failures.json after each run

### BO+GP Specifics
- Kernel: RBF with lengthscale=2.0
- Acquisition: Expected Improvement (EI)
- Initial random: 3 points, then GP-guided
- No LLM, no learning across runs

---

## Interpretation Guide

### If LHS+Ranking is Best
- Physics heuristics genuinely helpful
- Agent reasoning + good initialization = strong combination
- Recommendation: Use LHS+ranking in production

### If BO+GP is Best
- Deterministic, reproducible methods may be preferable
- Structure learning more efficient than reasoning
- Recommendation: Consider pure BO+GP or hybrid

### If All Similar
- Random init dominates; heuristics don't matter much
- Config space too small for advantage
- Recommendation: Use simplest (BO+GP) for speed

---

## Future Extensions

1. **BO+GP with Warm-Start**: Use LHS ranking as prior mean for GP
2. **Agent+BO Hybrid**: LLM proposes, BO ranks, agent implements
3. **Multi-Fidelity**: Low-fidelity (4 FE), Medium (6 FE), High (10 FE)
4. **Budget Comparison**: Normalized to same # evaluations (e.g., 15 evals total)
5. **Parallel Evaluation**: Multiple configs per batch for speed

---

## Conclusion

This suite enables rigorous comparison of three optimization paradigms:
- **Heuristic + Learning** (LHS + Agent)
- **Heuristic + Deterministic** (LHS + Physics)
- **Deterministic + Learnable** (BO+GP)

Results will inform the choice of method for the full 11-hour production benchmark.
