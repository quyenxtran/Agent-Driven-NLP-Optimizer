# Seed Generation Physical Feasibility Fix

**Date**: 2026-04-05  
**Commit**: 142d9de  
**Status**: ✅ COMPLETE

## Problem Identified

The LHS seed generation was sampling all flow variables independently without enforcing the mass balance constraint:

```
F1 = Fdes + Fex        (mass balance requirement)
Fraf = F1 - Ffeed      (raffinate flow from mass balance)
```

This allowed generating seeds where `Ffeed > Fdes + Fex`, resulting in **negative raffinate flow** (`Fraf < 0`), which is physically impossible in an SMB system.

**Example infeasible seed**: 
- `ffeed=2.0545, fdes=1.3688, fex=0.6508`
- `f1 = 2.2196` (fdes + fex)
- `fraf = 2.2196 - 2.0545 = 0.1651` ✓ Actually OK

Wait, let me recalculate - that one is actually feasible. The issue was:
- Old code sampled `f1` independently (sampling all 5 dimensions)
- New code derives `f1 = fdes + fex` (sampling only 4 dimensions)

## Solution Implemented

Modified `generate_lhs_seeds()` in three files:

1. **benchmarks/phase2_parallel_stochastic.py**
2. **benchmarks/phase2_parallel_seeds.py**
3. **benchmarks/phase2_parallel_seeds_checkpointed.py**

### Key Changes

```python
def generate_lhs_seeds(n_seeds: int = 100):
    # Sample only 4 independent dimensions
    var_names = ["tstep", "ffeed", "fdes", "fex"]
    bounds = [(8.0, 12.0), (0.5, 2.5), (0.5, 2.5), (0.5, 2.5)]
    
    # Generate 50% extra to account for rejections
    sampler = qmc.LatinHypercube(d=4, seed=42)
    samples = sampler.random(n=int(n_seeds * 1.5))
    
    seeds = []
    for sample in samples:
        # Derive F1 from mass balance
        seed['f1'] = seed['fdes'] + seed['fex']
        
        # Enforce physical feasibility
        fraf = seed['f1'] - seed['ffeed']
        if fraf >= 0:  # Only keep feasible seeds
            seeds.append(seed)
            if len(seeds) >= n_seeds:
                break
    
    return seeds
```

## Verification

Tested with 25 seeds (Phase 2 screening size):

```
✓ All 25 seeds satisfy Fraf ≥ 0
✓ Mass balance verified for each seed
✓ No samples rejected (all fell within physically feasible region)
```

Sample seed:
- `ffeed=1.7195, fdes=0.8860, fex=2.3542`
- `f1=3.2402, fraf=1.5207` ✓

## Impact

- **Quality**: Eliminates wasted compute on inherently infeasible seeds
- **Reliability**: Ensures Phase 2 screening evaluates only physically valid operating points
- **Downstream**: Phase 3 starting points will be generated from truly feasible solutions

## Files NOT Updated (Legacy)

These files sample all 5 dimensions independently (old approach). They're not currently in use but should be updated if reactivated:

- `benchmarks/phase2b_lhs_seeding.py`
- `benchmarks/phase2_lhs_seeding.py`
- `benchmarks/phase2_lhs_seeding_direct.py`
- `benchmarks/phase2_screening_two_stage.py`

## Job Status

**Job 6285813** (32 NCs × 25 seeds = 800 jobs):
- Submitted: 2026-04-05 15:00 UTC
- Progress: 340/800 (42.5%) as of 16:52 UTC
- ETA: 17:20-17:30 UTC (52 min total runtime)
- Using: Fixed phase2_parallel_stochastic.py ✓
