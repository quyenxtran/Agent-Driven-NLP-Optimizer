# OPTIMIZATION_PLAN.md

Archived planning note.

This file should be treated as historical planning context unless it is explicitly reconciled back into `PLAN.md`.

## Current source of truth
- Read **`PLAN.md`** for the most up-to-date project plan.
- See `CURRENT_STATUS.md` for the short current summary.

## Why this file is archived
There are multiple plan-like documents in the repo; `PLAN.md` is the designated primary plan.

---

# Agent Iteration Speed Optimization Plan

## Problem Statement

Current iteration cycle time: **~40 minutes**

Breakdown:
- Database context construction: 5-10 min (biggest bottleneck)
- JSON parsing/repair cycles: 5-10 min (recurring failures)
- 3 sequential LLM calls (A, B, C): ~30 sec total
- IPOPT solve: 1-7 sec (negligible)
- SQLite storage: 1 min

**Result**: Only ~10-15 iterations per 11-hour benchmark run instead of 50+

---

## Root Causes

1. **Full SQLite history loaded into every prompt** (~3606 tokens of context)
   - All 100+ prior results serialized as JSON
   - All hypothesis occurrences[] arrays included
   - All failure occurrences[] arrays included
   - No caching or delta updates

2. **JSON parsing failures trigger expensive repair cycles**
   - Scientist_B returns malformed JSON (missing keys, syntax errors)
   - Triggers validation loop: parse → fail → repair → retry
   - Each repair cycle adds 5-10 minutes
   - No schema enforcement during generation

3. **Sequential LLM calls with no parallelization**
   - Must wait for Scientist_A before running Scientist_B
   - Must wait for IPOPT solve before fetching next proposal
   - GPU is idle during database operations

---

## Optimization Strategies (Ranked by ROI)

### **Tier 1: High ROI, Low Effort** (Expected: 40 min → 20 min)

#### 1.1 Selective History Query (5-10 min saved)
**Problem**: Full SQLite history (100+ rows) bloats every prompt  
**Solution**: Retrieve only last N=20-30 results + summary of older patterns

**Implementation**:
- Query: `SELECT * FROM convergence_tracker ORDER BY iteration DESC LIMIT 20`
- Append summary: "Prior runs (iterations 1-30): best J was 45.2, worst 12.3, median purity 0.58"
- Hypothesis/failures: Show only recent 5 occurrences per item, summarize rest

**Expected savings**: 3500 → 1500 tokens of context = ~2-3 min per iteration

---

#### 1.2 Compress Context Format (1-2 min saved)
**Problem**: Full markdown + full JSON arrays are verbose

**Solution**: Abbrevated one-liner format
```
# Before (verbose)
## Hypothesis H5: Lower F1 increases extract acid recovery
- Description: Decreasing feed flow improves component separation
- Simulation results:
  - [2,2,2,2]: {J: 45.2, pur: 0.62, rec_GA: 0.78}
  - [1,2,3,2]: {J: 38.1, pur: 0.59, rec_GA: 0.71}

# After (compressed)
H5: Lower F1→extract recovery. Tests: [2,2,2,2]✓(J45.2,pur62,rec78%), [1,2,3,2]✗(J38.1)
```

**Expected savings**: 20-30% prompt size reduction = ~1-2 min per iteration

---

#### 1.3 Fix JSON Format with Grammar/Schema Constraints (5-10 min saved)
**Problem**: Scientist_B returns invalid JSON, triggering repair loops

**Solutions** (in order of preference):
1. **llama.cpp Grammar Feature** (best if supported)
   - Define GBNF grammar for valid Scientist_B JSON schema
   - llama.cpp enforces format during token generation
   - Zero repair cycles needed
   - Check: `llamacpp-server --help | grep -i grammar`

2. **Few-Shot Examples in Prompt** (works with current setup)
   - Add 2-3 working JSON examples to Scientist_B system prompt
   - Teach exact format through examples
   - Reduces repair calls from ~30% to ~5%
   - Example:
     ```json
     {
       "rating": "PROMISING",
       "reasoning": "This config explores new F1 region...",
       "confidence": 0.78,
       "required_keys": ["rating", "reasoning", "confidence"]
     }
     ```

3. **Simpler Output Format** (fallback)
   - Instead of JSON, use structured text
   - "RATING: PROMISING\nREASONING: ...\nCONFIDENCE: 0.78"
   - Much easier to parse, harder to get wrong

**Expected savings**: Eliminate 5-10 min repair cycles entirely

---

#### 1.4 Pre-Fetch Next Proposal During IPOPT Solve (2-3 min saved)
**Problem**: GPU is idle during IPOPT solve, then serial for next LLM call

**Solution**: Async proposal generation
```
Timeline (current):
LLM_A → Parse → LLM_B → Parse → IPOPT [1-7 sec] → LLM_A_next

Timeline (optimized):
LLM_A → Parse → LLM_B → Parse → [IPOPT in background] LLM_A_next in parallel
```

**Implementation**:
- Start IPOPT solve on current config
- While IPOPT runs, queue Scientist_A inference for next proposal
- When IPOPT finishes, next proposal is ready
- Saves: IPOPT time (1-7 sec) + LLM time overlap

**Expected savings**: 2-3 min per iteration

---

### **Tier 2: Medium ROI, Medium Effort** (Expected: additional 5-10 min saved)

#### 2.1 Batched LLM Calls (A+B in Single Response)
**Problem**: Scientist_A and Scientist_B are independent but serial

**Solution**: Single LLM call with explicit roles
```
System: "You are two scientists reviewing an SMB configuration.
Scientist_A (proposer): Suggest next config based on history.
Scientist_B (reviewer): Validate A's proposal independently.

Output format:
SCIENTIST_A_THOUGHT: ...
SCIENTIST_A_PROPOSAL: {json}
SCIENTIST_B_THOUGHT: ...
SCIENTIST_B_REVIEW: {json}
```

**Expected savings**: ~15-20 sec per iteration (eliminate B's LLM call latency)

---

#### 2.2 Probabilistic Scientist_C Skip
**Problem**: Always run 3-scientist arbitration even when A and B agree

**Solution**: Skip C if confidence > threshold
```python
if (proposal_confidence > 0.85 and review_confidence > 0.80):
    # Both high confidence, skip arbitration
    decision = "IMPLEMENT_A"
else:
    # Run expensive arbitration
    arbitration_result = scientist_c(...)
```

**Expected savings**: ~10-15% of iterations skip C entirely (~5 sec each)

---

#### 2.3 Cached Agent Reviews for Repeated Configs
**Problem**: Same configuration reviewed multiple times

**Solution**: Memoize LLM responses
- Store hash(config + context_hash) → review JSON
- If seen before and context unchanged, use cached review
- TTL: 30 min (context may have evolved)

**Expected savings**: ~5-10% of B calls are cache hits (~10 sec each)

---

### **Tier 3: Large Impact, Higher Effort**

#### 3.1 Model Routing (27B for A, 35B for B)
**Current**: Always 35B (slower, higher quality)  
**Idea**: Use 27B for proposals, 35B only for critical reviews

**Trade-off**:
- 27B: ~200 tok/sec (vs 104 tok/sec for 35B)
- Scientist_A: 1000 tokens → 5 sec (27B) vs 9.6 sec (35B)
- **Savings**: ~5 sec per iteration

---

#### 3.2 Infrastructure: vLLM or Dedicated GPU
**Current**: Single RTX 6000 for all LLM  
**Idea**: vLLM batching, or separate GPU for inference

**Trade-off**: Complex setup, diminishing returns after Tier 1/2 optimizations

---

## Implementation Roadmap

### **Phase 1: High-ROI Quick Wins** (estimated impact: 40 min → 15-20 min)
1. Implement selective history query (1.1)
2. Compress context format (1.2)
3. Add few-shot JSON examples + validation (1.3)
4. Test on single iteration, measure wall-clock time

### **Phase 2: Medium-Effort Gains** (estimated impact: 15-20 min → 10-12 min)
5. Implement pre-fetch async for IPOPT (1.4)
6. Batch LLM calls A+B (2.1)
7. Test on full benchmark run

### **Phase 3: Polish & Fine-Tune**
8. Probabilistic C skip (2.2)
9. Cached reviews (2.3)
10. Model routing if needed (3.1)

---

## Metrics to Track

For each iteration, log:
- `context_tokens`: Size of SQLite context
- `json_repair_attempts`: Number of parse failures
- `lm_a_latency_sec`: Time for Scientist_A call
- `lm_b_latency_sec`: Time for Scientist_B call
- `ipopt_solve_time_sec`: IPOPT wall-clock
- `total_iteration_time_sec`: End-to-end wall-clock

**Target**: Reduce `total_iteration_time_sec` from 2400s (~40 min) to <600s (~10 min)

---

## JSON Parsing Issues: Detailed Solutions

### **The Problem**
Scientist_B (and occasionally A, C) return invalid JSON:
- Missing closing braces
- Missing required keys
- Syntax errors (unescaped quotes, trailing commas)
- Partially generated responses (hit token limit)

Current handling: Parse fails → retry with explicit repair prompt → wastes 5-10 min

### **Solution 1: Grammar Constraints (Recommended)**

**If llama.cpp supports GBNF grammar**:
```bash
llamacpp-server --help | grep -i grammar
```

If yes, define a strict grammar for each scientist's output schema:
```gbnf
root   := scientist_b_review
scientist_b_review := "{" rating "," reasoning "," confidence "}"
rating := "\"rating\":" ("\"PROMISING\"" | "\"NEEDS_REFINEMENT\"" | "\"SKIP\"")
reasoning := "\"reasoning\":" string
confidence := "\"confidence\":" number
string := "\"" ([^"\\] | "\\" ["\\/bfnrt])* "\""
number := [0-9]+ ("." [0-9]+)?
```

**Impact**: Zero repair cycles, enforced during generation

---

### **Solution 2: Few-Shot Learning (Works Now)**

Add to Scientist_B system prompt:
```markdown
## Output Examples (You MUST follow this format exactly):

Example 1 (PROMISING):
{
  "rating": "PROMISING",
  "reasoning": "Configuration explores new F1 region (1.5-2.5 mL/min). Prior [2,2,2,2] at F1=3.0 gave J=45.2. This variation tests hypothesis H3.",
  "confidence": 0.82
}

Example 2 (NEEDS_REFINEMENT):
{
  "rating": "NEEDS_REFINEMENT",
  "reasoning": "Purity constraint unsatisfiable at this flow rate. Similar [1,2,3,2] already tested, failed. Suggest tighter desorbent flow.",
  "confidence": 0.91
}

Example 3 (SKIP):
{
  "rating": "SKIP",
  "reasoning": "Duplicate of [2,2,2,2] from iteration 5. No new information.",
  "confidence": 0.95
}

CRITICAL: Your response MUST be valid JSON. It will be parsed with Python's json.loads().
Include ALL three keys: rating, reasoning, confidence.
```

**Impact**: Reduces malformed output from ~30% to ~5%

---

### **Solution 3: Structured Output Format (Fallback)**

Replace JSON with plain text if parsing keeps failing:
```
RATING: PROMISING
REASONING: Configuration explores new F1 region (1.5-2.5 mL/min). Prior [2,2,2,2] at F1=3.0 gave J=45.2. This variation tests hypothesis H3.
CONFIDENCE: 0.82
```

Parse with simple regex:
```python
rating = re.search(r'RATING:\s*(\w+)', response).group(1)
reasoning = re.search(r'REASONING:\s*(.+?)(?=CONFIDENCE:)', response, DOTALL).group(1).strip()
confidence = float(re.search(r'CONFIDENCE:\s*([\d.]+)', response).group(1))
```

**Impact**: Even more robust, harder for LLM to break

---

### **Solution 4: Validation + Intelligent Repair**

If JSON parsing fails:
1. Try `json.loads(response)` — if it works, use it
2. If fails, attempt auto-repair:
   - Add missing closing braces: `response += "}" * (response.count("{") - response.count("}"))`
   - Remove trailing commas: `response = response.replace(",}", "}")`
   - Retry `json.loads()`
3. If still fails, extract via regex for required keys
4. If still fails, return default review: `{"rating": "SKIP", "reasoning": "Parse error", "confidence": 0.1}`

**Code sketch**:
```python
def parse_scientist_b_json(response: str) -> dict:
    # Try direct parse
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass
    
    # Try auto-repairs
    repaired = response.replace(",}", "}")  # trailing comma
    repaired = repaired + "}" * (repaired.count("{") - repaired.count("}"))  # missing braces
    try:
        return json.loads(repaired)
    except:
        pass
    
    # Fall back to regex extraction
    rating = re.search(r'"rating":\s*"([^"]+)"', response)
    reasoning = re.search(r'"reasoning":\s*"([^"]+)"', response)
    confidence = re.search(r'"confidence":\s*([\d.]+)', response)
    
    if rating and reasoning and confidence:
        return {
            "rating": rating.group(1),
            "reasoning": reasoning.group(1),
            "confidence": float(confidence.group(1))
        }
    
    # Default: skip and log error
    logging.warning(f"Could not parse Scientist_B JSON: {response[:200]}")
    return {"rating": "SKIP", "reasoning": "Parse error", "confidence": 0.0}
```

**Impact**: Graceful degradation, no expensive retries

---

## Recommended Approach

**Start with**:
1. **Few-shot examples** (1.3.2) — implement immediately, lowest risk
2. **Validation + repair** (4) — implement in agent_runner.py as fallback
3. **Check for GBNF grammar** (1.3.1) — if available, add to llamacpp-server config

This gives you:
- 95%+ valid JSON (few-shot teaches format)
- 100% graceful handling (repair catches edge cases)
- Optional: 100% enforced if grammar available

---

## Success Criteria

- [ ] Single iteration completes in <600 seconds (~10 min) [down from ~2400s]
- [ ] 11-hour benchmark yields 50+ iterations [up from ~15]
- [ ] JSON parsing failures <5% [down from ~30%]
- [ ] No expensive repair cycles blocking execution
