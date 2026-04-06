# PHASE2_SCALING_STRATEGY.md

Archived implementation note.

This file records earlier scaling ideas for a prior Phase 2 variant.

## Current source of truth
- Read **`PLAN.md`** for the reconciled active workflow.

## Why this file is archived
It is still useful reference material, but it is not the current canonical execution plan.

---

# Original archived content

# Phase 2 Scaling Strategy: 8 CPUs vs 24 CPUs

## Current Job (Job 6282883): 8 CPUs - Keep Running ✅

| Parameter | Value |
|-----------|-------|
| **CPUs** | 8 (4 workers × 2 threads) |
| **Walltime** | 20 hours |
| **Progress** | ~1.6% (52/3200 seeds) |
| **Status** | Running smoothly |
| **Projected completion** | 7-8 hours ✅ |

**Decision: Do NOT cancel.** Job will finish successfully within walltime.

---

## Future Jobs: 24 CPUs - High-Performance Variant

### New Files Created

**Script:** `benchmarks/phase2_parallel_seeds_checkpointed.py`
- 12 workers × 2 OMP_NUM_THREADS = 24 CPUs
- **Checkpointing**: Saves results after each NC
- **Resumable**: Can restart from last completed NC
- **3x faster**: Expected ~2.5-3 hours for full Phase 2

**SLURM Job:** `slurm/pace_smb_phase2_lhs_seeding_24cpu.slurm`
- CPU allocation: 24 CPUs per task
- Memory: 64G (matches CPU count)
- Walltime: 6 hours (plenty of margin for 2.5-3 hour runtime)
- Auto-detects checkpoints and resumes if restarted

### Performance Comparison

| Metric | 8 CPUs (Current) | 24 CPUs (Future) |
|--------|-----------------|-----------------|
| **Workers** | 4 | 12 |
| **Parallelism** | 4× | 12× |
| **Expected Runtime** | 7-8 hours | 2.5-3 hours |
| **Walltime Needed** | 20 hours | 6 hours |
| **Queue Wait** | Short | Short-Medium |
| **Cost** | Lower | Higher |

### Checkpoint System

**How it works:**
```
1. Optimize NC [1,1,2,4] (100 seeds)
2. Save results to checkpoint.json ✓
3. Optimize NC [1,1,3,3] (100 seeds)
4. Save results to checkpoint.json ✓
5. ... continue for all 32 NCs ...
6. Write final phase2_summary.json at end
```

**If job is killed at NC [1,1,3,3] (50% complete):**
```bash
# Resubmit with resume flag
sbatch slurm/pace_smb_phase2_lhs_seeding_24cpu.slurm --resume

# OR script auto-detects checkpoint and resumes:
python -m benchmarks.phase2_parallel_seeds_checkpointed \
  --artifact-dir artifacts/phase2_lhs_seeding \
  --n-workers 12 \
  --resume  # Only processes remaining NCs
```

**Checkpoint file:** `artifacts/phase2_lhs_seeding/phase2_checkpoint.json`
```json
{
  "completed_ncs": ["[1,1,2,4]", "[1,1,3,3]"],
  "completed_results": [
    { "nc": "[1,1,2,4]", "n_seeds": 100, "n_successful": 95, ... },
    { "nc": "[1,1,3,3]", "n_seeds": 100, "n_successful": 93, ... }
  ]
}
```

---

## When to Use Each Version

### Current: 8 CPU Version (`pace_smb_phase2_lhs_seeding.slurm`)
✅ **Use for:** Exploratory runs, resource-constrained situations
- Longer but reliable
- Low queue wait times
- Good for getting quick baseline data

### Future: 24 CPU Version (`pace_smb_phase2_lhs_seeding_24cpu.slurm`)
✅ **Use for:** Production runs, publication-quality data, multiple iterations
- Fast completion (2.5-3 hours)
- Resumable via checkpointing
- Cost: Higher CPU allocation but same or lower total time

---

## Recommended Workflow

### For Publication Quality Study (Recommended)

```bash
# Phase 2: High-performance variant
sbatch slurm/pace_smb_phase2_lhs_seeding_24cpu.slurm
# Wait ~3 hours for completion
# Check: ls artifacts/phase2_lhs_seeding/phase2_summary.json

# Phase 3: 45 high-fidelity validations (currently using same 8 CPUs)
# Can be upgraded to 24 CPUs as well for faster results
sbatch slurm/pace_smb_phase3_strategy_comparison.slurm
# Wait ~20 hours for completion
# Check: artifacts/phase3_results/strategy_comparison_stats.json

# Total pipeline: ~23 hours to publication-ready results
```

### If Job Needs to Resume

```bash
# Job was killed mid-way (e.g., after 2 NCs, 50% complete)
# Automatically resumes from checkpoint - no code changes needed
sbatch slurm/pace_smb_phase2_lhs_seeding_24cpu.slurm

# Check progress:
python phase2_recovery_and_aggregate.py --check-progress
# Shows which NCs are completed and which remain
```

---

## Implementation Notes

### Why Checkpointing Works

The new script saves results after **each NC completes**, not after each seed:
- Small overhead (one JSON write per NC = negligible)
- Tracks which NCs are done
- Skips completed NCs on restart
- Gracefully handles interruptions

### Thread Allocation Details

**8 CPU version:**
```
Total CPUs: 8
Workers: 4
Threads/worker: 2
MA97 parallelization: 2 threads per seed optimization
Result: 4 seeds optimize in parallel
```

**24 CPU version:**
```
Total CPUs: 24
Workers: 12
Threads/worker: 2
MA97 parallelization: 2 threads per seed optimization
Result: 12 seeds optimize in parallel
```

### Memory Allocation

- 8 CPU: 32G (4 GB per CPU)
- 24 CPU: 64G (2.7 GB per CPU)
- Each worker subprocess is lightweight (~500 MB)
- Memory scales linearly with CPU count

---

## Next Steps

1. **Immediate:** Let job 6282883 (8 CPU) finish (~7 hours remaining)
2. **Later:** Use `pace_smb_phase2_lhs_seeding_24cpu.slurm` for Phase 3 validation runs or future iterations
3. **Archive:** Keep both versions - 8 CPU for quick prototyping, 24 CPU for production

---

## Files Summary

| File | Purpose | CPUs | Checkpointing |
|------|---------|------|----------------|
| `benchmarks/phase2_parallel_seeds.py` | Original version | 4-8 | ❌ No |
| `benchmarks/phase2_parallel_seeds_checkpointed.py` | **New version** | 12+ | ✅ **Yes** |
| `slurm/pace_smb_phase2_lhs_seeding.slurm` | Current job | 8 | ❌ |
| `slurm/pace_smb_phase2_lhs_seeding_24cpu.slurm` | **New job** | 24 | ✅ **Yes** |

---

## Testing Recommendation

Before running Phase 2 with 24 CPUs on full 3,200 seeds:

```bash
# Quick smoke test: 5 seeds, 1 NC, 4 workers
python -m benchmarks.phase2_parallel_seeds_checkpointed \
  --ncs "[1,1,2,4]" \
  --n-seeds 5 \
  --artifact-dir artifacts/test_24cpu \
  --n-workers 4 \
  --timeout 120

# Should complete in ~2 minutes
# Verify: ls artifacts/test_24cpu/phase2_checkpoint.json
```

Then scale to full run if successful.
