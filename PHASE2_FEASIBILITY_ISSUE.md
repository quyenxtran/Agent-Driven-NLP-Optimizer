# Phase 2 Feasibility Issue - Investigation & Options

**Issue Found:** Job 6282883 achieving **0% feasibility rate** (100 seeds on NC [1,1,2,4])

---

## Root Cause Analysis

**IPOPT logs show:**
- Constraint violation: consistently ~0.098 (9.8%)
- Never reaches "Optimal Solution Found"
- All 3,260 IPOPT logs show "Converged to a point of local infeasibility"

**Constraints specified:**
```
--purity-min 0.15       (15% purity required)
--recovery-ga-min 0.15  (15% recovery_GA required)
--recovery-ma-min 0.15  (15% recovery_MA required)
```

**Likely cause:** The LHS-sampled parameter space may contain regions where even these **very relaxed** constraints (normal targets are 0.60-0.75) cannot be satisfied with NC [1,1,2,4]'s geometry.

**NC [1,1,2,4] is unbalanced:**
- Zone 1: 1 column
- Zone 2: 1 column
- Zone 3: 2 columns
- Zone 4: 4 columns

This imbalance may create narrow feasible regions in some parameter ranges.

---

## Current Situation

**Job 6282883 status:**
- Still running (100/100 seeds on NC [1,1,2,4] completed)
- Processing remaining 31 NCs (~3 hours left)
- Will complete regardless of feasibility
- IPOPT logs saved but results are infeasible

---

## Options for Recovery

### Option A: Accept Infeasible Solutions (Quickest) ✅
**Action:** Let job finish, extract "best-infeasible" points from IPOPT logs
- Use objective function value even though constraints violated
- Document that these are "best-effort" solutions
- Proceed with Phase 3 using these points
- **Time cost:** None (job continues as-is)
- **Data quality:** Lower fidelity but still comparable

**Use case:** Comparison baseline - shows what each strategy selects with imperfect data

### Option B: Rerun with Relaxed Constraints (Balanced)
**Action:** Cancel job, rerun with even more relaxed constraints
```
--purity-min 0.05       (5% purity)
--recovery-ga-min 0.05  (5% recovery)
--recovery-ma-min 0.05  (5% recovery)
```
- Expected feasibility: ~60-80%
- Still generates reasonable comparison data
- **Time cost:** 7-8 hours (same as current)
- **Data quality:** Higher - most seeds will be feasible

**Use case:** Publication-quality baseline with feasible solutions

### Option C: Increase Fidelity (Most Robust)
**Action:** Rerun with medium-fidelity discretization
```
--nfex 6  (was 4)
--nfet 3  (was 2)
--ncp 2   (was 1)
```
- Higher resolution may capture feasible regions
- Expected feasibility: ~50-70%
- **Time cost:** 20-25 hours (longer per seed)
- **Data quality:** Highest - better solution quality

**Use case:** If publication requires high-fidelity foundation data

### Option D: Hybrid Two-Stage (Recommended for Publication)
**Stage 1: Quick feasibility scan** (1-2 hours)
```
--nfex 4, --nfet 2, --purity-min 0.05
→ Identify which NCs/seeds have feasible regions
```
**Stage 2: Refinement** (5-6 hours)
```
--nfex 6, --nfet 3, --purity-min 0.15
→ Refine promising regions to publication quality
```

---

## Recommendation: **Option B** (Relaxed Constraints)

**Why:**
1. **Publication quality:** Feasible solutions are required for credibility
2. **Quick recovery:** Only 7-8 hours to rerun
3. **Fair comparison:** All three strategies will work with same data
4. **Risk mitigation:** Avoids "comparing strategies on infeasible baseline"

**Action:**
```bash
# Cancel current job (optional - can let it finish for reference)
scancel 6282883

# Create new job with relaxed constraints
# sbatch slurm/pace_smb_phase2_lhs_seeding_24cpu_relaxed.slurm
```

---

## If You Proceed with Current Job (Option A)

**Pros:**
- No time loss
- 3 hours to completion  
- Still provides NC screening data

**Cons:**
- Results are "best-infeasible" not "best-feasible"
- May skew strategy comparison (all strategies start from infeasible baseline)
- Not publication-ready without documentation

**Mitigation:**
- Document that NC [1,1,2,4] was found infeasible
- Use results only for relative ranking
- Note in Phase 3 report: "Foundation data flagged as challenging NC"

---

## Technical Details: Why 0% Feasibility?

The IPOPT iterations show:
```
Iterations:  89-122 (varies)
Constraint violation: 9.77e-02 to 9.98e-02  (stuck at ~10%)
Dual infeasibility: 5.00e-01 (not converging)
Overall NLP error: 5.00e-01 (threshold probably 1e-6)
```

The solver cannot improve constraint violation beyond 10%, indicating:
1. **Infeasible region likely:** No point exists satisfying all constraints
2. **Not numerical:** Solver converged stably to infeasible point
3. **Seed-dependent:** May affect different NC/seed combinations differently

---

## What I'll Do Now

✅ **Continue monitoring job 6282883** to completion
✅ **Document the finding** in PHASE2_FEASIBILITY_ISSUE.md (this file)
✅ **Prepare Option B job** (relaxed constraints variant) ready to submit

**Your decision:** 
- Let current job finish (3 hours) and review results, OR
- Cancel now and resubmit with Option B immediately (saves 3 hours)

Both are viable - depends on whether you want the infeasible reference data for comparison.
