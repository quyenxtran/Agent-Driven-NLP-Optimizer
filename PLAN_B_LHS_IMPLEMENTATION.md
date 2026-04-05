# Plan B: LHS + Physics Filtering Implementation

## 🎯 Objective
Implement Latin Hypercube Sampling with physics-based filtering to systematically explore the constrained NC configuration space before running full 11-hour benchmarks.

**Critical Constraints**:
- ✅ Total column count = 8 (nc[0] + nc[1] + nc[2] + nc[3] = 8)
- ✅ Maximum pump flow rate = 3.0 ml/min
- Each dimension: [1, 4] columns

**Timeline**: ~2-3 hours development + validation  
**Target**: Deploy improved sampling by [INSERT_TIME], then submit benchmarks

---

## 📊 Baseline Metrics (Before Plan B)

| Metric | Value | Notes |
|--------|-------|-------|
| Diagnostic override rate | 40% | After schema simplification |
| Configuration sampling | Greedy (heuristic) | Local hill-climbing only |
| Coverage of 385 configs | Unknown | Not systematic |
| Iterations/11h | ~40-50 | Improved from 15 |

---

## 🏗️ Phase 1: LHS Configuration Generation

### 1.1 Design LHS Sampling
- **Space**: 4D constrained (nc[0], nc[1], nc[2], nc[3])
- **Ranges**: [1, 4] for each dimension
- **Constraint**: sum(nc) = 8 (CRITICAL)
- **Valid configs**: 31 total (not 385)
- **Sample size**: All 31 configs (LHS selects stratified subset)

### 1.2 Implementation ✅ COMPLETE
**File**: `benchmarks/lhs_sampler.py`
```python
def generate_valid_constrained_configs(target_sum=8):
    """Enumerate all valid [nc0, nc1, nc2, nc3] where sum=target_sum"""
    # Returns: 31 configurations
    
def generate_lhs_configs(n_samples=60, seed=42, target_sum=8):
    """Generate LHS samples from the valid configuration space"""
    # Returns: All valid configs with sum=8
```

### 1.3 Validation Checkpoint ✅ COMPLETE
- [✅] Generate LHS points with sum=8 constraint
- [✅] Verify all 31 valid configs enumerated
- [✅] All points in valid range [1,4]
- [✅] Test output: 31/31 valid, 100% pass constraint

---

## ⚙️ Phase 2: Physics Constraint Filtering

### 2.1 Hard Constraints (Eliminates Invalid Configs) ✅ COMPLETE
**File**: `benchmarks/physics_filter.py`

```python
class PhysicsFilter(target_sum=8):
    def apply_total_columns_constraint(nc):
        """
        CRITICAL: Total columns MUST equal 8
        Eliminates any configs with sum(nc) != 8
        """
        
    def apply_zone_residence_time_constraint(nc):
        """
        Each zone must have feasible residence time
        (Soft validation - NLP solver does final check)
        """
```

### 2.2 Soft Heuristics (Ranks Valid Configs) ✅ COMPLETE
```python
class ConfigScorer:
    def score_selectivity_potential(nc):
        """Longer zones = better separation"""
        
    def score_throughput_estimate(nc):
        """More columns = higher capacity"""
        
    def score_solver_difficulty(nc):
        """Balance complexity: imbalanced = harder"""
        
    def combined_score(nc, weights=default):
        """Weighted: selectivity=0.4, throughput=0.3, solver=-0.3"""
```

### 2.3 Validation Checkpoint ✅ COMPLETE
- [✅] Filter LHS through hard constraints (sum=8)
- [✅] All 31 configs pass feasibility (100%)
- [✅] Score and rank all valid configs
- [✅] Top configs: [1,1,2,4], [1,1,3,3], [1,1,4,2]... (score 41.67)

---

## 🤖 Phase 3: Integration with Agent

### 3.1 Initialization Strategy
**File**: `benchmarks/agent_runner.py` (MODIFY)

```python
def initialize_config_shortlist(lhs_configs, physics_filter, agent_priority_plan):
    """
    1. Generate 60 LHS points
    2. Filter through physics (hard constraints)
    3. Score remaining configs (soft heuristics)
    4. Agent ranks by acquisition strategy
    5. Return prioritized list [1st, 2nd, 3rd, ...]
    """
```

### 3.2 Agent Learning
- Agent doesn't override initial LHS ranking immediately
- Learns from first 5-10 config results
- Then proposes exploratory/exploitative candidates
- Fallback to LHS ranking if all proposals rejected

### 3.3 Validation Checkpoint
- [ ] LHS + physics filter integrated with agent
- [ ] Shortlist initialization working
- [ ] Agent can propose and rank-override

---

## 📈 Phase 4: Smoke Test Validation (Plan B)

### 4.1 Quick LHS Test
**Job**: 27B model, 15 min runtime
- Test LHS sampling pipeline (31 valid configs)
- Test physics filtering with sum=8 constraint
- Verify agent can use ranked configs
- Verify no crashes in optimization loop

### 4.2 Expected Improvements
| Metric | Before | After | Target |
|--------|--------|-------|--------|
| Config space | 385 (unlimited) | 31 (sum=8) | Focused search |
| Initial quality | Greedy heuristic | Physics-ranked | Top 20 better |
| Diagnostic rate | 40% | <30% | <20% |
| Convergence | Slow exploration | Guided by heuristics | 50-60 iter/11h |

### 4.3 Validation Checkpoint ⏳ READY TO SUBMIT
- [✅] Created smoke test script: `slurm/pace_smb_27b_smoke_test_lhs.slurm`
- [✅] Configured with --use-lhs-ranking flag
- [✅] Physics filtering: 31/31 valid (100% pass)
- [✅] Agent integration complete (rank_configs_with_lhs)
- [ ] Run smoke test (submit job)
- [ ] Verify configuration exploration
- [ ] Approve for Phase 5

---

## 🚀 Phase 5: Full Benchmark Submission

### 5.1 27B Full Run
- Command: `sbatch slurm/pace_smb_27b_full_with_lhs.slurm`
- Duration: 11 hours
- Expected: 50-60 iterations, better coverage

### 5.2 35B Full Run
- Command: `sbatch slurm/pace_smb_35b_full_with_lhs.slurm`
- Duration: 11 hours
- Expected: 20-30 iterations (model size), improved quality

### 5.3 Validation Checkpoint
- [ ] Both jobs submitted
- [ ] Monitoring dashboard live
- [ ] Early results show diversity

---

## 📊 Success Metrics (Post-Benchmark)

| Metric | Goal | Success Criterion |
|--------|------|------------------|
| Unique configs explored | 30+ (27B) | >25 unique NC topologies |
| Iteration quality | >70% approve | <20% diagnostic override |
| Coverage evenness | Stratified | All NC dimension ranges tested |
| Best J found | >50 | Better than previous baseline |
| Solver reliability | >80% feasible | Consistent convergence |

---

## 📝 Implementation Checklist

### Phase 1: LHS Sampling ✅ COMPLETE
- [✅] Create `benchmarks/lhs_sampler.py`
- [✅] Implement `generate_valid_constrained_configs(target_sum=8)`
- [✅] Implement `generate_lhs_configs(target_sum=8)` 
- [✅] Implement `is_valid_nc_config(target_sum=8)`
- [✅] Test: Generate 31 valid points, all sum to 8
- [✅] Commit to main (7d65ab3)

### Phase 2: Physics Filtering ✅ COMPLETE
- [✅] Create `benchmarks/physics_filter.py`
- [✅] Implement `PhysicsFilter.apply_total_columns_constraint()` (CRITICAL)
- [✅] Implement `ConfigScorer` class (soft heuristics)
- [✅] Test: Filter 31 points → 31 valid (100%)
- [✅] Score all 31 candidates
- [✅] Commit to main (7d65ab3)

### Phase 3: Agent Integration ✅ COMPLETE
- [✅] Modify `benchmarks/agent_policy.py`
- [✅] Add `rank_configs_with_lhs()` function
- [✅] Integrate with `build_search_tasks()` to re-rank NC library
- [✅] Add `--use-lhs-ranking` flag to `benchmarks/agent_runner.py`
- [✅] Fallback to default ranking if LHS import fails
- [✅] Commit to main (89bf858)

### Phase 4: Smoke Test ⏳ READY TO SUBMIT
- [✅] Create `slurm/pace_smb_27b_smoke_test_lhs.slurm`
- [✅] Enabled --use-lhs-ranking flag
- [ ] Submit and monitor 15-min test
- [ ] Verify no crashes
- [ ] Check coverage metrics
- [ ] Approve for Phase 5

### Phase 5: Full Benchmark
- [ ] Create `slurm/pace_smb_27b_full_with_lhs.slurm`
- [ ] Create `slurm/pace_smb_35b_full_with_lhs.slurm`
- [ ] Submit both jobs
- [ ] Monitor live results
- [ ] Archive final metrics

---

## 🎯 Decision Points

**If LHS smoke test shows no improvement**: Fall back to Plan A (full greedy benchmark)

**If physics constraints too strict**: Relax thresholds (residence time, solver difficulty)

**If agent learns better ranking**: Allow it to override LHS after 5 iterations

---

## 📅 Timeline Estimate

| Phase | Time | Status |
|-------|------|--------|
| LHS sampling | 20 min | ✅ Complete (31 configs enumerated) |
| Physics filtering | 25 min | ✅ Complete (sum=8 constraint enforced) |
| Agent integration | 20 min | ✅ Complete (LHS ranking integrated) |
| Smoke test (15 min) | 10 min | ⏳ Ready to submit (Phase 4) |
| Full benchmark (27B + 35B) | 32h | 🔲 Pending (Phase 5) |
| **TOTAL** | **~33h** | ⏳ Phase 4 ready, awaiting approval |

---

## 📋 Notes

### Constraint Enforcement
- **Total column count = 8**: ENFORCED in `generate_valid_constrained_configs()` and `apply_total_columns_constraint()`
  - Only 31 valid configs exist (not 385)
  - All LHS samples guaranteed to satisfy this constraint
  - All filtered configs pass this hard constraint
  
- **Max pump flow = 3.0 ml/min**: 
  - TBD: Depends on operating point (feed concentration, separation targets)
  - Will be validated during NLP optimization
  - Can be added as NLP constraint if needed

### Artifacts & Analysis
- Keep all 31 valid LHS configs + scores in `artifacts/lhs_configs_sum8.json` for analysis
- Log physics filter statistics (feasibility, scores distribution)
- Compare agent exploration coverage: target is to visit all 31 topologies
- Compare final results vs Plan A greedy baseline

### Key Insights
- Constraining sum(nc)=8 dramatically reduces search space: 385 → 31 configs
- This enables systematic exploration of the full valid topology space
- All 31 configs are physically reasonable (symmetric dimension distribution)
- Scoring is more granular now (average imbalance, selectivity trade-offs)

