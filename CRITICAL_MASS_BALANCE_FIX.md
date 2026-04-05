# CRITICAL FIX: Mass Balance Constraint Correction

**Date**: 2026-04-05 (16:52 UTC)  
**Commit**: cf27ef6  
**Status**: ✅ FIXED & RESUBMITTED  
**Severity**: CRITICAL - Previous constraint was completely inverted

## The Error

The previous seed generation fix checked the WRONG physical constraint:

### ❌ WRONG (Previous Implementation)
```python
# Incorrect constraint
fraf = seed['f1'] - seed['ffeed']  # f1 = fdes + fex (WRONG)
if fraf >= 0:  # Checking: Fdes + Fex ≥ Ffeed
```

This allowed seeds where **Ffeed + Fdes < Fex**, which violates the true mass balance.

### ✅ CORRECT (Current Implementation)  
```python
# Correct constraint from optimization.py:67
fraf = seed['ffeed'] + seed['fdes'] - seed['fex']
if fraf >= 0:  # Checking: Ffeed + Fdes ≥ Fex
```

## Root Cause

The mass balance in SMB from `src/sembasmb/optimization.py` line 67:

```python
m.RaffinateConsistency = Constraint(expr=m.UR == m.UF + m.UD - m.UE)
```

In flow terms: **Fraf = Ffeed + Fdes - Fex**

For physical feasibility: **Ffeed + Fdes ≥ Fex ≥ 0**

## Impact

**Job 6285813** (22 min runtime):
- ❌ CANCELLED - was using incorrect constraint
- Evaluated seeds that violate true mass balance
- Results not trustworthy for Phase 3

**Job 6286017** (RESUBMITTED):
- ✅ Uses correct constraint: Fraf = Ffeed + Fdes - Fex ≥ 0
- All 25 generated seeds verified feasible
- Ready for Phase 2 screening

## Verification

Sample seed from corrected generation:
```
ffeed=2.3810, fdes=1.5096, fex=1.9486
Fraf = 2.3810 + 1.5096 - 1.9486 = 1.9420 ✓
F1 = ffeed + fraf = 2.3810 + 1.9420 = 4.3229 ✓
```

## Files Updated

1. `benchmarks/phase2_parallel_stochastic.py`
2. `benchmarks/phase2_parallel_seeds.py`
3. `benchmarks/phase2_parallel_seeds_checkpointed.py`

All three now correctly enforce: **Fraf = Ffeed + Fdes - Fex ≥ 0**

## Next Steps

1. Monitor job 6286017 (32 NCs × 25 seeds = 800 jobs)
2. ETA: ~50-60 minutes total runtime
3. Completion expected: ~17:45-17:55 UTC
4. Proceed with Phase 2 aggregation once complete
