# Optimization Implementation Status

## Completed (Phase 1: High-ROI, Low-Effort)

### 1. ✅ JSON Parsing Robustness
**File**: `benchmarks/agent_json_parser.py` (new)

**What**: Multi-fallback JSON parser that eliminates expensive repair cycles
- **Strategy 1**: Direct JSON parse
- **Strategy 2**: Auto-repair (fixes missing braces, trailing commas, markdown backticks)
- **Strategy 3**: Regex extraction (last resort for partially-malformed JSON)
- **Strategy 4**: Graceful defaults (never return None, fills missing keys)

**Expected Impact**: Reduces JSON parsing failures from ~30% to <5%, eliminates 5-10 min repair cycles

**Code Changes**:
```python
from agent_json_parser import (
    parse_json_with_fallbacks,
    validate_required_keys,
    apply_defaults_for_missing_keys,
)

# Old way (expensive):
data, raw, _repaired, repair_error = request_json_with_single_repair(...)
if not isinstance(data, dict):
    return low_quality_recovery()

# New way (robust):
raw = client.chat(...)  # Single LLM call
data, parse_status = parse_json_with_fallbacks(raw, required_keys)
data = apply_defaults_for_missing_keys(data, required_keys)
# Always returns valid dict, no expensive repair needed
```

---

### 2. ✅ Few-Shot Examples in Scientist_B Prompt
**File**: `benchmarks/agent_scientists.py`, lines 695-740

**What**: Embedded two working JSON examples in the Scientist_B review prompt
- Example 1: APPROVE decision with full reasoning
- Example 2: REJECT decision with counterproposal

**Expected Impact**: Teaches LLM exact format → reduces malformed output from ~30% to ~5%

**Embedded in Prompt**:
```
## Example valid review responses:

### Example 1: APPROVE with concerns
{
  "decision": "approve",
  "reason": "Explores F1=2.0...",
  ...
}

### Example 2: REJECT
{
  "decision": "reject",
  ...
}

CRITICAL: Your response MUST be valid JSON. Return ONLY JSON, no markdown, no explanation.
```

---

### 3. ✅ SQLite Context Optimization
**File**: `benchmarks/agent_db.py`, line 411

**Changes**:
- Added `optimize_context: bool = True` parameter
- Skip expensive composition metrics extraction when `optimize_context=True`
- Reduces raw_json parsing overhead (was parsing all recent records)

**Code**:
```python
def sqlite_history_context(conn, max_feasible=5, max_near=5, max_recent=6, optimize_context=True):
    # ... fetch top feasible, near-feasible, recent ...
    
    # NEW: Skip expensive composition metrics when optimize_context=True
    if not optimize_context:
        lines.append("Recent composition snapshots (outlet CE/CR):")
        # ... extract composition from raw_json ...
        # ... compute flow/composition trends ...
```

**Expected Impact**: 1-2 min saved per iteration (eliminates JSON parsing from 100+ raw_json blobs)

**Applied in**: `benchmarks/agent_runner.py`, lines 1480 and 1600
```python
sqlite_excerpt = sqlite_history_context(sqlite_conn, optimize_context=True)
```

---

## Expected Performance Gains

### Before Optimizations
```
40 minute iteration cycle:
  - Database context construction: 5-10 min (bottleneck)
  - JSON repair failures: 5-10 min (blocking)
  - 3 sequential LLM calls: 30 sec
  - IPOPT solve: 1-7 sec
  - Other overhead: 1-2 min
  ─────────────────────────
  Total: ~40 min per iteration
  
  11-hour budget: ~15-16 iterations
```

### After Phase 1 Optimizations (Projected)
```
18-23 minute iteration cycle:
  - Database context construction: 1-2 min (optimized, no composition)
  - JSON parsing: <1 sec (no repair cycles)
  - 3 sequential LLM calls: 30 sec
  - IPOPT solve: 1-7 sec
  - Other overhead: 1-2 min
  ─────────────────────────
  Total: ~18-23 min per iteration
  
  11-hour budget: ~30-35 iterations
  
  Speedup: ~2x more iterations in same time budget
```

---

## Files Modified

| File | Changes | Impact |
|------|---------|--------|
| `benchmarks/agent_json_parser.py` | New module with multi-fallback parser | Eliminates repair cycles |
| `benchmarks/agent_scientists.py` | Imports parser, adds few-shot examples, uses fallback logic | Robust JSON handling + format teaching |
| `benchmarks/agent_db.py` | Added `optimize_context` flag, skips composition metrics | Faster context building |
| `benchmarks/agent_runner.py` | Pass `optimize_context=True` to sqlite_history_context | Uses optimized context |

---

## Validation Checklist

- [ ] Run single quick iteration to verify:
  - [ ] No crashes in new JSON parser
  - [ ] Scientist_B review completes (even if JSON imperfect)
  - [ ] Graceful defaults applied for missing keys
  - [ ] Few-shot examples in prompt
  
- [ ] Submit 27B benchmark job:
  - [ ] Monitor first 5 iterations for timing
  - [ ] Verify no expensive repair cycles
  - [ ] Check context sizes in logs
  
- [ ] Compare metrics:
  - [ ] Iteration cycle time: target 18-23 min (down from 40 min)
  - [ ] Total iterations in 11 hours: target 30+ (up from 15)
  - [ ] JSON parse success rate: >95% (no failures)

---

## Future Optimizations (Phase 2)

Still pending (lower priority):

1. **Compress context format** (1-2 min saved)
   - Abbreviate history to one-liners
   - Remove verbose explanations

2. **Pre-fetch async** (2-3 min saved)
   - Start next proposal while IPOPT solves
   - Overlap computation

3. **Batch LLM calls** (15 sec saved)
   - Scientist_A + B in single response
   - Fewer API calls

4. **Probabilistic skip Scientist_C** (5 sec × 10% = 0.5 min saved)
   - Skip arbitration if A and B agree

---

## Next Steps

1. **Verify code integrity** - no syntax errors
2. **Submit 27B job** with optimized code
3. **Monitor first iterations** for timing + parsing stats
4. **Compare against previous run** (6276054)
5. **If successful, submit 35B job**

Expected: 2x speedup → ~35 iterations instead of ~15 in 11-hour budget
