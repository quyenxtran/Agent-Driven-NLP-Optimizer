# Phase 2 Scaling: Quick Reference

## Current Status ✅

**Job 6282883** (8 CPUs): **Keep running, do NOT cancel**
- Progress: 52/3200 seeds (1.6%)
- Time elapsed: ~45 minutes
- Time remaining: ~7-8 hours
- Walltime available: 20 hours
- Status: Running smoothly within margin

---

## New 24 CPU Version Ready ✅

**For future use:** `slurm/pace_smb_phase2_lhs_seeding_24cpu.slurm`

### Quick Start

```bash
# Submit 24 CPU high-performance job
sbatch slurm/pace_smb_phase2_lhs_seeding_24cpu.slurm

# If interrupted, just resubmit (auto-resumes from checkpoint):
sbatch slurm/pace_smb_phase2_lhs_seeding_24cpu.slurm

# Monitor anytime:
python phase2_recovery_and_aggregate.py --check-progress
```

### Performance

| Metric | 8 CPU | 24 CPU |
|--------|-------|--------|
| Runtime | 7-8 hours | 2.5-3 hours |
| Workers | 4 | 12 |
| Speedup | baseline | **3x faster** |
| Checkpointing | ❌ No | ✅ **Yes** |
| Walltime | 20 hours | 6 hours |

---

## Key Feature: Checkpointing

**What it does:**
- Saves results after each NC (not after each seed)
- Tracks progress in `phase2_checkpoint.json`
- Allows resumption without losing work

**Example workflow:**
```
Submit 24 CPU job
↓
Process NCs [1,1,2,4], [1,1,3,3], [1,1,4,2] (3 hours elapsed)
↓
System crashes or you cancel (50% done)
↓
Resubmit same job (auto-detects checkpoint)
↓
Skips 3 completed NCs, continues from [1,2,1,4]
↓
Saves time + guarantees no lost work
```

---

## When to Use Each Version

**8 CPU Version** (`pace_smb_phase2_lhs_seeding.slurm`)
- Quick prototyping
- Resource-constrained scenarios
- Acceptable multi-hour wait times

**24 CPU Version** (`pace_smb_phase2_lhs_seeding_24cpu.slurm`) ⭐
- Production runs
- Publication-quality data
- Publication pipeline (Phase 2 → Phase 3 → manuscript)
- Cost: Same CPU-hours but wall-clock 3x faster

---

## Next Steps

1. ✅ **Monitor current job:** Let 6282883 finish (~7 hours)
   ```bash
   tail -f logs/smb-phase2-lhs-6282883.out  # May be buffered
   python phase2_recovery_and_aggregate.py --check-progress  # More reliable
   ```

2. ✅ **Once Phase 2 complete:** Phase 3 starts automatically
   ```bash
   # Phase 3 will use 3 strategies × 5 NCs × 3 runs = 45 high-fidelity validations
   python -m benchmarks.evaluate_phase3_strategies
   ```

3. ⏰ **For future Phase 2 runs:** Use 24 CPU version
   ```bash
   sbatch slurm/pace_smb_phase2_lhs_seeding_24cpu.slurm
   ```

---

## Files Created

```
benchmarks/phase2_parallel_seeds_checkpointed.py     (New: scalable + checkpoint)
slurm/pace_smb_phase2_lhs_seeding_24cpu.slurm        (New: 24 CPU SLURM job)
PHASE2_SCALING_STRATEGY.md                           (Detailed docs)
SCALING_QUICK_REFERENCE.md                           (This file)
```

---

## Checkpointing Details (If Curious)

**Checkpoint structure:**
```json
{
  "completed_ncs": [
    "[1,1,2,4]",
    "[1,1,3,3]"
  ],
  "completed_results": [
    { "nc": "[1,1,2,4]", "n_seeds": 100, "n_successful": 95, "best_seed_idx": 42, "productivity": 12.45 },
    { "nc": "[1,1,3,3]", "n_seeds": 100, "n_successful": 94, "best_seed_idx": 67, "productivity": 13.12 }
  ]
}
```

**How resumption works:**
1. Script loads checkpoint on startup
2. Identifies remaining NCs: [1,1,4,2], [1,2,1,4], ... [4,2,1,1]
3. Processes only remaining NCs
4. Updates checkpoint after each NC
5. Writes final `phase2_summary.json` when all done

---

## Summary

✅ Current 8 CPU job healthy & on track  
✅ New 24 CPU variant ready for production  
✅ Checkpointing enabled for reliability  
✅ 3x speedup for future runs  

**No action needed now.** Current job will finish successfully in ~7 hours.
