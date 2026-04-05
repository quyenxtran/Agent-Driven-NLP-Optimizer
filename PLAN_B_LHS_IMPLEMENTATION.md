# Plan B: LHS + Physics Filtering Implementation

## 🎯 Objective
Implement Latin Hypercube Sampling with physics-based filtering to systematically explore the 385-configuration space before running full 11-hour benchmarks.

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
- **Space**: 4D (nc[0], nc[1], nc[2], nc[3])
- **Ranges**: [1, 4] for each dimension (385 valid configs)
- **Sample size**: 50-80 stratified points
- **Constraint**: Each dimension divided into N equal strata

### 1.2 Implementation
**File**: `benchmarks/lhs_sampler.py` (NEW)
```python
def generate_lhs_configs(n_samples=60, seed=42):
    """Generate Latin Hypercube stratified samples of NC space"""
    # Returns: List[List[int]] representing [nc[0], nc[1], nc[2], nc[3]]

def is_valid_nc_config(nc):
    """Check basic validity (not all constraints, just structure)"""
    # Returns: bool
```

### 1.3 Validation Checkpoint
- [ ] Generate 60 LHS points
- [ ] Verify coverage (all dimensions stratified)
- [ ] Ensure all points in valid range

---

## ⚙️ Phase 2: Physics Constraint Filtering

### 2.1 Hard Constraints (Eliminates Invalid Configs)
**File**: `benchmarks/physics_filter.py` (NEW)

```python
class PhysicsFilter:
    def apply_zone_residence_time_constraint(nc):
        """
        Each zone must have feasible residence time:
        τ = column_length / interstitial_velocity
        Valid range: 0.5s to 30s (tunable)
        """
        # Eliminates ~40-50% of invalid configs
        
    def apply_mass_balance_feasibility(nc):
        """
        Check if mass balance is achievable:
        F1 = Ffeed + Fraf
        F1 = Fdes + Fex
        """
        # Soft check (actual flows will be optimized)
```

### 2.2 Soft Heuristics (Ranks Valid Configs)
```python
class ConfigScorer:
    def score_selectivity_potential(nc):
        """
        Longer zones typically better for separation
        Score: sum(nc) * scaling_factor
        """
        
    def score_throughput_estimate(nc):
        """
        More columns (higher nc) = higher throughput
        But also longer residence times
        """
        
    def score_solver_difficulty(nc):
        """
        Estimate conditioning from config structure
        Simpler topologies easier to solve
        """
        
    def combined_score(nc, weights={"selectivity": 0.4, "throughput": 0.3, "solver": -0.3}):
        """Weighted combination"""
```

### 2.3 Validation Checkpoint
- [ ] Filter LHS points through hard constraints
- [ ] Score remaining configs
- [ ] Rank top 40-50 candidates

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
**Job**: 27B model, 5 min runtime
- Test LHS sampling pipeline
- Test physics filtering
- Verify no crashes

### 4.2 Expected Improvements
| Metric | Before | After | Target |
|--------|--------|-------|--------|
| Config coverage | Greedy | Stratified | 80%+ diverse |
| Initial quality | Random ranking | Physics-ranked | Top 20 better |
| Diagnostic rate | 40% | <30% | <20% |
| Iterations/11h | ~45 | ~50-60 | 60+ |

### 4.3 Validation Checkpoint
- [ ] LHS smoke test passes
- [ ] Physics filtering working
- [ ] Integration complete and tested

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

### Phase 1: LHS Sampling
- [ ] Create `benchmarks/lhs_sampler.py`
- [ ] Implement `generate_lhs_configs()`
- [ ] Implement `is_valid_nc_config()`
- [ ] Test: Generate 60 points, verify stratification
- [ ] Commit to main

### Phase 2: Physics Filtering  
- [ ] Create `benchmarks/physics_filter.py`
- [ ] Implement `PhysicsFilter` class (hard constraints)
- [ ] Implement `ConfigScorer` class (soft heuristics)
- [ ] Test: Filter 60 points → ~30-40 valid
- [ ] Score top 20 candidates
- [ ] Commit to main

### Phase 3: Agent Integration
- [ ] Modify `benchmarks/agent_runner.py`
- [ ] Add `initialize_config_shortlist()` function
- [ ] Update initial priority plan logic
- [ ] Test: LHS ordering vs agent ranking
- [ ] Commit to main

### Phase 4: Smoke Test
- [ ] Create `slurm/pace_smb_27b_smoke_lhs.slurm`
- [ ] Submit and monitor 5-min test
- [ ] Verify no crashes
- [ ] Check coverage metrics
- [ ] Approve for full run

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
| LHS sampling | 20 min | 🔲 Not started |
| Physics filtering | 25 min | 🔲 Not started |
| Agent integration | 20 min | 🔲 Not started |
| Smoke test | 10 min | 🔲 Not started |
| Full benchmark | 32h | 🔲 Queued |
| **TOTAL** | **~33h** | 🔲 Starting now |

---

## 📋 Notes

- Keep all LHS configs + scores in `artifacts/lhs_configs.json` for analysis
- Log physics filter statistics (# eliminated, avg scores)
- Compare final results vs Plan A greedy baseline
- Document learnings for future optimization

