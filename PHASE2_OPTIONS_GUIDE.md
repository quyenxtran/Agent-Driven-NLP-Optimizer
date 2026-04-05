# Phase 2 Options Implementation Guide

**Status:** Job 6282883 cancelled. Ready to implement Options B, C, or D.

---

## Quick Comparison

| Aspect | Option B | Option C | Option D |
|--------|----------|----------|----------|
| **Purpose** | Fast publication-ready | Highest quality | Balanced hybrid |
| **Constraints** | 0.05 (relaxed) | 0.15 (standard) | 0.05→0.15 (staged) |
| **Fidelity** | Low (nfex=4) | Medium (nfex=6) | Low→Medium (staged) |
| **Expected Feasibility** | 60-80% | 50-70% | 80-95% (stage1) → 60-75% (stage2) |
| **Runtime** | **7-8 hours** | 20-25 hours | 5-6h + 12-15h = **~20 hours** |
| **Best For** | Quick publication | Maximum accuracy | Balanced approach |
| **Stages** | 1 (single run) | 1 (single run) | 2 (sequential jobs) |
| **Parallelization** | 24 CPUs (12 workers) | 24 CPUs (12 workers) | 24 CPUs (12 workers) |
| **Checkpointing** | ✅ Yes | ✅ Yes | ✅ Yes |

---

## Option B: Relaxed Constraints (Recommended for Speed)

**Use this if:** You want publication-quality results FAST

### Configuration
```
Constraints: purity ≥ 0.05, recovery ≥ 0.05 (RELAXED from 0.15)
Discretization: nfex=4, nfet=2, ncp=1 (low-fidelity)
CPUs: 24 (12 workers × 2 threads)
Walltime: 10 hours
Expected runtime: 7-8 hours
Feasibility rate: 60-80%
```

### Rationale
- Relaxing constraints from 0.15 → 0.05 greatly increases feasible region
- Low-fidelity discretization is still adequate for NC screening
- 60-80% feasibility is sufficient for publication comparison
- Fast turnaround: 7-8 hours vs 20-25 for Option C

### Submit
```bash
sbatch slurm/pace_smb_phase2_option_b_relaxed.slurm
```

### Monitor
```bash
python phase2_recovery_and_aggregate.py --check-progress
```

---

## Option C: Higher Fidelity (Best Quality)

**Use this if:** Maximum solution quality matters more than time

### Configuration
```
Constraints: purity ≥ 0.15, recovery ≥ 0.15 (standard)
Discretization: nfex=6, nfet=3, ncp=2 (MEDIUM fidelity)
CPUs: 24 (12 workers × 2 threads)
Walltime: 28 hours
Expected runtime: 20-25 hours
Feasibility rate: 50-70%
```

### Rationale
- Medium fidelity (nfex=6, nfet=3) provides better solution resolution
- Standard constraints (0.15) are still achievable in most regions
- 50-70% feasibility is good for quality baseline
- Higher computational cost justified by better solution details
- Useful if Phase 3 needs high-precision results

### Submit
```bash
sbatch slurm/pace_smb_phase2_option_c_highfidelity.slurm
```

### Monitor
```bash
python phase2_recovery_and_aggregate.py --check-progress
```

---

## Option D: Hybrid Two-Stage (Recommended for Publication)

**Use this if:** You want BOTH speed AND quality (best balanced approach)

### Stage 1: Quick Feasibility Scan (5-6 hours)
```
Constraints: purity ≥ 0.05, recovery ≥ 0.05 (ULTRA-RELAXED)
Discretization: nfex=4, nfet=2, ncp=1 (low-fidelity)
Purpose: Identify feasible regions quickly
Feasibility rate: 80-95%
```

### Stage 2: High-Fidelity Refinement (12-15 hours)
```
Constraints: purity ≥ 0.15, recovery ≥ 0.15 (standard)
Discretization: nfex=6, nfet=3, ncp=2 (MEDIUM fidelity)
Purpose: Refine all NCs at higher quality
Feasibility rate: 60-75% at high quality
```

### Rationale
- Stage 1 quickly identifies feasible regions (80-95% success)
- Stage 2 refines those regions at higher fidelity
- Total time: ~20 hours (same as Option C!)
- Better feasibility than Option C (Stage 1 data guides Stage 2)
- Provides detailed information on feasible/infeasible regions
- Excellent for understanding problem structure

### Submit
```bash
# First, submit Stage 1:
sbatch slurm/pace_smb_phase2_option_d_hybrid_stage1.slurm

# Wait for completion (5-6 hours), then Stage 2:
sbatch slurm/pace_smb_phase2_option_d_hybrid_stage2.slurm
```

### Monitor
```bash
# After Stage 1 completes:
python phase2_recovery_and_aggregate.py --check-progress

# After Stage 2 completes:
python phase2_recovery_and_aggregate.py --check-progress
```

---

## Decision Matrix

**Choose Option B if:**
- ✅ Fast turnaround is critical
- ✅ 60-80% feasibility is acceptable
- ✅ Low-fidelity results are sufficient for NC ranking
- ✅ You want results in 7-8 hours

**Choose Option C if:**
- ✅ Solution quality is paramount
- ✅ You can wait 20-25 hours
- ✅ Medium-fidelity discretization is needed
- ✅ High-precision optimization results matter

**Choose Option D if:**
- ✅ You want both speed AND quality (best of both worlds)
- ✅ Understanding feasible regions is important
- ✅ 20 hours is acceptable (same as Option C)
- ✅ You want better feasibility than pure high-fidelity
- ✅ **RECOMMENDED for publication quality**

---

## Customization: Adjusting Parameters

All options use `phase2_parallel_seeds_checkpointed.py` which accepts parameters:

```bash
python -m benchmarks.phase2_parallel_seeds_checkpointed \
  --nfex <N>              # Spatial elements (default 4)
  --nfet <N>              # Temporal elements (default 2)
  --ncp <N>               # Collocation points (default 1)
  --purity-min <val>      # Purity constraint (default 0.15)
  --recovery-min <val>    # Recovery constraint (default 0.15)
  --n-workers <N>         # Workers (default 12)
  --timeout <sec>         # Timeout per seed (default 120)
  --artifact-dir <path>   # Output directory
  --n-seeds <N>           # Seeds per NC (default 100)
  --resume                # Resume from checkpoint
  --verbose               # Print progress
```

### Examples

**Create custom variant with nfex=5, lower constraints:**
```bash
sbatch -J "smb-phase2-custom" slurm/pace_smb_phase2_option_b_relaxed.slurm
# Then modify the --nfex, --purity-min values in the script
```

---

## Output Files

After completion, find results in:
```
artifacts/phase2_option_b_relaxed/phase2_summary.json  (Option B)
artifacts/phase2_option_c_hifidelity/phase2_summary.json  (Option C)
artifacts/phase2_option_d_hybrid/phase2_summary.json  (Option D)
```

Each contains:
```json
{
  "status": "ok",
  "stage": "phase2_parallel_checkpointed",
  "ncs_tested": 32,
  "results": [
    {
      "nc": "[1,1,2,4]",
      "n_seeds": 100,
      "n_successful": 78,  // Feasible seeds
      "best_seed_idx": 42,
      "productivity": 12.45,
      "metrics": { "purity": 0.62, "recovery_ga": 0.78, "recovery_ma": 0.75 }
    },
    // ... 31 more NCs ...
  ],
  "statistics": {
    "total_seeds": 3200,
    "total_successful": 2482,  // Overall success rate
    "feasibility_rate": "77.6%"
  }
}
```

---

## Next Steps After Phase 2 Completes

### 1. Verify Results
```bash
# Check summary file exists
ls -lh artifacts/phase2_option_*/phase2_summary.json

# View statistics
python -c "import json; d=json.load(open('artifacts/phase2_option_b_relaxed/phase2_summary.json')); print(f\"Success: {d['statistics']['total_successful']}/{d['statistics']['total_seeds']}\")"
```

### 2. Start Phase 3
Once Phase 2 is done, trigger Phase 3 comparative strategy evaluation:
```bash
python -m benchmarks.evaluate_phase3_strategies \
  --phase2-results artifacts/phase2_option_b_relaxed/phase2_summary.json \
  --output-dir artifacts/phase3_results
```

### 3. Expected Phase 3 Runtime
- 3 strategies × 5 NCs × 3 validations = 45 high-fidelity optimizations
- Expected time: 30-36 hours
- Total to publication: Phase 2 (7-20h) + Phase 3 (36h) = **43-56 hours**

---

## Troubleshooting

### If job is killed before completion:
- Checkpointing is enabled - just resubmit the same job
- Script auto-detects completed NCs and continues from where it left off
```bash
sbatch slurm/pace_smb_phase2_option_b_relaxed.slurm  # Resumes automatically
```

### If feasibility is lower than expected:
- Try Option B with even more relaxed constraints (0.02-0.03)
- Or run Option D Stage 2 with nfex=8 for even finer discretization

### If you want to compare all three:
- Submit all three in sequence (they use different artifact directories)
- Compare `phase2_summary.json` across all three
- Choose the one with best feasibility/quality tradeoff

---

## Recommendation Summary

🎯 **For publication pipeline:** **Option D (Hybrid)**
- Best balance of speed and quality
- Same time as Option C, better results
- Two-stage approach provides insights into problem structure

⚡ **For quick results:** **Option B (Relaxed)**
- Fast (7-8 hours)
- Still publication-ready (60-80% feasibility)
- Good for prototyping or quick publication

🏆 **For maximum quality:** **Option C (High-Fidelity)**
- Best solution quality
- 50-70% feasibility
- Use if precision is critical

---

## Files
- `slurm/pace_smb_phase2_option_b_relaxed.slurm` — Option B
- `slurm/pace_smb_phase2_option_c_highfidelity.slurm` — Option C
- `slurm/pace_smb_phase2_option_d_hybrid_stage1.slurm` — Option D Stage 1
- `slurm/pace_smb_phase2_option_d_hybrid_stage2.slurm` — Option D Stage 2
- `benchmarks/phase2_parallel_seeds_checkpointed.py` — Core script (all options)

**Ready to submit!** Choose your option above and run the sbatch command.
