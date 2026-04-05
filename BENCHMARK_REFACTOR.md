# Benchmark Refactoring: From Mock Scoring to Real IPOPT Evaluation

## Summary

The initial smoke tests revealed that `lhs_only_runner.py` and `bo_gp_runner.py` were using **simulated/mock objective scores** instead of real IPOPT optimization. This defeated the purpose of benchmarking these strategies. Both runners have been refactored to use **real IPOPT evaluation** for each NC configuration.

---

## Issues in Original Smoke Tests

### 1. **LHS-Only (Job 6277729)**
- **Problem**: Used simulated objectives (physics_score + random noise)
- **Symptom**: All 31 configs "evaluated" in 0.76 seconds total
- **Expected**: Should take minutes or hours depending on fidelity
- **Impact**: Results were not comparable to agent-based optimization

### 2. **BO+GP (Job 6277730)**  
- **Problem**: Failed with ImportError in bo_gp_runner.py
- **Root Cause**: Importing non-existent functions from run_stage.py
- **Fixed**: Removed bad imports, added real evaluation

### 3. **LHS+Agent (Job 6277728)**
- **Problem**: All solver errors with "infeasible" status
- **Root Cause**: Flow constraints too tight for tested configurations
- **Investigation**: Pump flow constraint (max 3.0 ml/min) combined with purity/recovery requirements may be infeasible for some NC configs

---

## Refactoring Changes

### `benchmarks/lhs_only_runner.py`
**Before**: 
```python
# Simulated objective
simulated_score = physics_score + np.random.normal(0, random_noise)
```

**After**:
```python
# Real IPOPT evaluation
eval_result = evaluate_candidate(args, config)
objective_value = eval_result.get("objective_mean", None)
```

**Key additions**:
- `setup_benchmark_args()`: Creates proper argparse.Namespace with SMB solver config
- Real `evaluate_candidate()` calls from run_stage.py
- Tracks actual feasibility and objective values
- Configurable fidelity (nfex, nfet, ncp parameters)

### `benchmarks/bo_gp_runner.py`
**Before**: 
```python
# Penalty function proxy
score = 100.0 - imbalance * 3.0 - abs(total_cols - 8.0) + np.random.normal(0, 1.0)
```

**After**:
```python
# Real IPOPT evaluation
eval_result = evaluate_candidate(args, config)
objective_value = eval_result.get("objective_mean", None)
score = objective_value if objective_value is not None else 0.0
```

**Key additions**:
- Same `setup_benchmark_args()` helper
- Real `evaluate_candidate()` calls
- Proper handling of feasible/infeasible results
- Configured for low fidelity smoke tests

---

## New Smoke Tests

### LHS-Only Real IPOPT (Job 6278161)
**Script**: `slurm/pace_smb_lhs_only_real_ipopt_smoke.slurm`

- **Time**: 30 minutes
- **CPUs**: 8 with OMP threading for MA97
- **Fidelity**: Low (nfex=5, nfet=2, ncp=1)
- **Solver**: IPOPT with MA97 parallel linear solver
- **Evaluations**: Up to 31 configs (all valid NC configs)
- **Expected**: Deterministic ranking by physics score with real optimization

### BO+GP Real IPOPT (Job 6278162)
**Script**: `slurm/pace_smb_bo_gp_real_ipopt_smoke.slurm`

- **Time**: 30 minutes
- **CPUs**: 8 with OMP threading for MA97
- **Fidelity**: Low (nfex=5, nfet=2, ncp=1)
- **Solver**: IPOPT with MA97 parallel linear solver
- **Evaluations**: Up to 15 configs (BO-guided selection)
- **Expected**: Intelligent config selection via Gaussian Process

---

## Benchmark Comparison (When Complete)

After smoke tests complete, we can compare:

| Metric | LHS-Only | BO+GP | LHS+Agent |
|--------|----------|-------|-----------|
| Evaluations | Up to 31 | Up to 15 | 11h budget |
| Selection method | Physics ranking | Expected Improvement | LLM-guided |
| Coverage | Sequential (deterministic) | BO-optimized (adaptive) | Agent-adaptive |
| Best objective | Likely high (explores all) | Likely fast discovery | May find global |
| Feasibility | Real IPOPT results | Real IPOPT results | Real IPOPT results |

---

## Technical Details

### Discretization Levels
- **Low Fidelity** (smoke tests): nfex=5, nfet=2, ncp=1
  - ~5-10 seconds per configuration
  - Total: ~5-15 minutes for 15 configs
  
- **Medium Fidelity**: nfex=6, nfet=3, ncp=2
  - ~10-20 seconds per configuration
  
- **High Fidelity**: nfex=10, nfet=5, ncp=2
  - ~20-60 seconds per configuration
  - Reference validation level

### Solver Configuration
- **Solver**: IPOPT (interior point)
- **Linear solver**: MA97 (parallel HSL sparse solver)
- **Threads**: 8 OMP threads
- **Environment**: OPENBLAS_NUM_THREADS=1 (no nested threading)

### Flow Constraints
- **Pump limit**: max(F1, Ffeed, Fdes, Fex) ≤ 3.0 ml/min
- **Purity**: extract ≥ 0.60 (exploratory, 0.90 for production)
- **Recovery**: GA ≥ 0.75, MA ≥ 0.75
- **Mass balance**: Fraf = Ffeed + Fdes - Fex (automatic)

---

## Next Steps

1. **Monitor jobs**: 
   - LHS-Only: 6278161
   - BO+GP: 6278162
   - Previous BO+GP (old attempt): 6278076

2. **Analyze results**:
   - Compare feasibility rates (how many infeasible?)
   - Compare best objectives found
   - Compare convergence speed
   - Check if BO+GP benefits from intelligent exploration

3. **Debug LHS+Agent infeasibility**:
   - May need to relax pump constraint or flow bounds
   - May need to provide better initial seeds
   - May need to adjust purity/recovery targets

4. **Design Phase 5 full benchmarks**:
   - Scale smoke test winners to 11-hour production runs
   - Use higher fidelity (medium or high)
   - Collect comprehensive convergence data
