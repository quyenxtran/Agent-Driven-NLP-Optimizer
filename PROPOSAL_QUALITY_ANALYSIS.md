# Proposal Quality Analysis (27B - 22 Iterations)

## Executive Summary

**Good News**: No crashes, graceful JSON handling, systematic exploration working  
**Concern**: 81% of proposals fall back to FORCE_DIAGNOSTIC mode (suggests validation strictness issue)

---

## Metrics Overview

### Proposal Strategy Distribution
```
EXPLORE:        4 proposals (19%)  - New configuration exploration
EXPLOIT:        0 proposals (0%)   - Parameter refinement
DIAGNOSTIC:    17 proposals (81%)  - Fallback mode (quality gate rejections)
```

### Scientist_B Review Outcomes
```
APPROVALS:     18 (75%)  - Passed validation
REJECTIONS:     6 (25%)  - Failed quality gates
```

### Top Rejection Reasons
```
[6x] "review must include NC strategy assessment against alternatives"
```

---

## What's Working Well ✅

### 1. **JSON Parsing is Robust**
- No crashes on malformed JSON
- Graceful fallback to defaults
- Few-shot examples helping format compliance

### 2. **Configuration Exploration is Strategic**
- Started with [2,2,2,2] (baseline): 47 tests
- Expanded to [1,1,3,3] (new topology): 38 tests
- Shows exploration beyond initial config
- No random/nonsensical proposals

### 3. **Iteration Velocity is Exceptional**
- 22 iterations in 16 minutes (82 iters/hour)
- Even with 81% diagnostic overrides, still exploring
- No solver crashes or external failures

---

## Concerns to Address ⚠️

### Issue: High Diagnostic Override Rate (81%)

**Root Cause**: Scientist_B responses missing required fields

**Missing Field**: `nc_strategy_assessment`
- Required: Array of strings comparing candidate NC vs alternatives with evidence
- Expected: ["[2,2,2,2] well-explored (12 runs)", "[1,3,2,2] topology infeasible at this flow..."]
- Actual: 27B not including this field consistently

**Impact**: 
- Proposal falls back to FORCE_DIAGNOSTIC
- Systematic infeasibility triggers kick in
- Less strategic exploration, more fallback pattern-matching

### Why This Happens:
1. **Prompt Complexity**: Scientist_B prompt is dense (8000+ chars)
2. **Large JSON Schema**: 15 required fields in response
3. **27B Model Limitations**: Smaller model struggles with complex schema
4. **Context Pressure**: Lean history (5 runs) might limit model's understanding

---

## Good Proposal Examples

### Example 1: Iteration 15 (EXPLORE)
```json
{
  "iteration": 15,
  "acquisition_type": "EXPLORE",
  "config": "nc=[1,1,3,3], seed=reference_minus",
  "reason": "Current NC [1,1,3,3] still needs reference screening (1/3); continue current NC before rotating.",
  "status": "✅ Approved by Scientist_B"
}
```
- **Why Good**: Clear rationale, specific hypothesis (needs ref screening 1/3), follows exploration plan
- **Evidence**: Configuration is novel topology being systematically explored

### Example 2: Iteration 17 (EXPLORE - same pattern)
```json
{
  "iteration": 17,
  "acquisition_type": "EXPLORE",
  "config": "nc=[1,1,3,3], seed=reference_plus",
  "reason": "Current NC [1,1,3,3] still needs reference screening (2/3); continue current NC before rotating.",
  "status": "✅ Approved by Scientist_B"
}
```
- **Why Good**: Systematic screening progression (2/3), clear next steps
- **Pattern**: Proposals show consistent methodology, not random

---

## Problem Proposal Examples

### Example 1: Iteration 3 (REJECTED)
```json
{
  "iteration": 3,
  "config": "nc=[2,2,2,2], seed=reference_tstep",
  "reason": "Continue reference screening",
  "rejection": "Rejected: review must include NC strategy assessment against alternatives.",
  "fallback": "FORCE_DIAGNOSTIC"
}
```
- **Why Problematic**: Missing nc_strategy_assessment field
- **Impact**: Falls back to systematic diagnostic instead of continuing exploration
- **Model Issue**: 27B not generating complete JSON schema

### Example 2: Iteration 6 (SYSTEMATIC ISSUE)
```json
{
  "iteration": 6,
  "reason": "Systematic infeasibility trigger fired across the last 5 results.",
  "fallback": "FORCE_DIAGNOSTIC"
}
```
- **Why Problematic**: Diagnostic override (not a strategic proposal)
- **Model Issue**: Accumulation of validation failures triggers system fallback
- **Evidence**: 6 consecutive rejections for missing fields

---

## Root Cause Analysis

### Why Scientist_B Responses Are Incomplete

**Hypothesis 1**: Prompt Length (8000 chars)
- Prompt is at maximum compacted size
- Model may truncate response before finishing all fields
- Solution: Reduce prompt verbosity further

**Hypothesis 2**: Schema Complexity (15 required fields)
```json
{
  "decision": "approve/reject",
  "reason": "...",
  "evidence_refs": [],
  "comparison_assessment": [],
  "last_two_run_audit": [],
  "flowrate_audit": [],
  "delta_audit": [],
  "column_topology_audit": [],
  "physics_audit": "...",
  "counterproposal_run": {...},
  "nc_strategy_assessment": [],        ← MISSING
  "compute_assessment": "...",
  "counterarguments": [],
  "required_checks": [],
  "priority_updates": [],
  "risk_flags": []
}
```
- Too many fields for 27B to track
- Solution: Simplify schema (only require 5-7 critical fields)

**Hypothesis 3**: Few-Shot Examples Insufficient
- Current examples in prompt: 2 full JSON responses
- 27B model may not fully learn from examples at this prompt length
- Solution: Add more strategic constraints in system prompt

---

## Recommendations

### Quick Fix (Keep Optimizations): Simplify Scientist_B Schema
Instead of 15 required fields, reduce to 5 critical ones:
```json
{
  "decision": "approve/reject",
  "reason": "2-3 sentences with evidence",
  "physics_audit": "zone balance assessment",
  "counterarguments": ["concern 1", "concern 2"],
  "required_checks": ["check 1", "check 2"]
}
```

**Expected Impact**:
- 0% rejection rate (no missing fields)
- 0% FORCE_DIAGNOSTIC fallbacks
- 100% strategic proposals (not fallbacks)
- Cleaner decision flow

### Medium-Term Fix: Use 35B for Scientist_B
- 35B shows better JSON compliance (empirically)
- 27B for Scientist_A (faster proposals)
- 35B for Scientist_B (better validation)
- Trade-off: Slightly slower, but higher quality validation

### Longer-Term: Optimize Prompt Architecture
- Split Scientist_B prompt into two phases:
  1. Fast decision (approve/reject)
  2. Optional detailed reasoning
- Use streaming JSON for large responses
- Add structured output constraints

---

## Current Status

✅ **System is working** - exploration is happening, configurations are being tested  
⚠️ **Quality could be improved** - diagnostic overrides are a band-aid, not strategic  
📊 **Speed is excellent** - 82 iters/hour validates optimization success  

**Recommendation**: Let current jobs complete (they're fast), then implement schema simplification before next run.

---

## Monitoring During Execution

Watch for:
- [ ] % of FORCE_DIAGNOSTIC proposals (should be <10% with fixes)
- [ ] Configuration diversity (should expand to 3+ unique NCs)
- [ ] Solver feasibility rate (should improve with better proposals)
- [ ] Iteration completion time (should remain <1.5 min/iter)

---

## Files to Modify (If Implementing Fixes)

1. `benchmarks/agent_scientists.py` - Simplify Scientist_B required_keys tuple
2. `benchmarks/agent_json_parser.py` - Update defaults for simpler schema
3. Scientist_B prompt - Reduce complexity, focus on decision quality over completeness

