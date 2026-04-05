---
name: Phase 2 Scaling Decision - 8 CPUs vs 24 CPUs
description: Decision to keep current 8 CPU job running while creating 24 CPU checkpointed variant for future
type: project
---

## Decision Made (2026-04-05)

**Current Job 6282883:** Keep running at 8 CPUs
- Status: 1.6% complete (52/3200 seeds)
- Speed: 34-35 seconds per seed per worker
- Projected completion: 7-8 hours (within 20-hour walltime)
- **Decision:** Do not cancel and restart

**Why:** Restarting would cost 40+ minutes (cancel + queue wait + restart setup), possibly negating any speedup from 24 CPUs

## New High-Performance Variant Created

**24 CPU Version** (`pace_smb_phase2_lhs_seeding_24cpu.slurm`)
- 12 workers × 2 OMP_NUM_THREADS = 24 CPUs
- **3x speedup:** 2.5-3 hours instead of 7-8 hours
- **Checkpointing:** Saves results after each NC (resumable)
- **Walltime:** 6 hours (ample margin)
- **Use case:** Future runs, Phase 3 validation, production publication quality

## Scaling Approach

**Two-tier strategy:**
1. **8 CPU version** (`phase2_parallel_seeds.py`): Quick prototyping, baseline
2. **24 CPU version** (`phase2_parallel_seeds_checkpointed.py`): Production runs with checkpoint/resume

**How checkpointing works:**
- Results saved in JSON after each NC completes
- File: `phase2_checkpoint.json` tracks completed NCs
- If job killed at NC 16/32: Resubmit with `--resume` flag to skip completed NCs
- Zero code changes needed for resumption

## Why:** Checkpointing matters for production

Without checkpointing, interruptions = lost progress. With checkpointing:
- Safe to use high-CPU allocation (more aggressive queue requests)
- Easy recovery from system failures
- Can run multiple sequential jobs and combine results
- Better for publication pipeline (confidence in completeness)

## Timeline

- Now: Keep 6282883 running (7-8 hours to completion)
- Later: Use 24 CPU version for Phase 3 validation runs or future iterations
- Archive: Both versions for different use cases

## Memory for future: 

When running future Phase 2 (or scaling Phase 3 to 24 CPUs):
```bash
# Submit 24 CPU high-performance job
sbatch slurm/pace_smb_phase2_lhs_seeding_24cpu.slurm

# If interrupted, auto-resumes from checkpoint
sbatch slurm/pace_smb_phase2_lhs_seeding_24cpu.slurm  # Just resubmit, script detects checkpoint

# Check progress anytime
python phase2_recovery_and_aggregate.py --check-progress
```
