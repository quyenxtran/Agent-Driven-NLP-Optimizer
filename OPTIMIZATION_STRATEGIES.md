# SMB Optimization Strategies - Detailed Comparison

## Three Competing Approaches

We're testing three fundamentally different strategies for NC configuration optimization. This document details the philosophy, mechanics, strengths, and weaknesses of each.

---

## Strategy 1: LHS + Agent (Physics-Ranked)

### Philosophy
**"Combine human intuition with learned intelligence"**

Use physics heuristics to provide smart initial ranking, then let an LLM agent learn from results and make adaptive decisions.

### Mechanics

```
┌──────────────────────────────────────────────────────────────────┐
│ INITIALIZATION (One-time)                                        │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│ 1. Generate all 31 valid NC configs (sum=8, each ∈ [1,4])       │
│                                                                  │
│ 2. Physics-based scoring:                                        │
│    score = 0.4×selectivity + 0.3×throughput - 0.3×difficulty   │
│    • Selectivity: prefer more columns (longer residence time)   │
│    • Throughput: prefer more columns (adsorbent capacity)       │
│    • Difficulty: penalize imbalance, high column count          │
│                                                                  │
│    Result: Ranked list [best → worst]                           │
│    Top 5: [1,1,2,4], [1,1,3,3], [1,1,4,2], [1,2,1,4], ...     │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────────┐
│ ADAPTIVE LOOP (Repeated each iteration)                          │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│ Scientist_A (Proposer):                                          │
│   Reads: history + heuristics + physics ranking                 │
│   Logic: "Based on what we've learned, what should we try next?"│
│   Output: NC config proposal + reasoning (EXPLORE/EXPLOIT)      │
│                                                                  │
│ Scientist_B (Reviewer):                                          │
│   Reads: A's proposal + history                                 │
│   Logic: "Is this proposal physically sound? Redundant?"        │
│   Output: APPROVE / REJECT / COUNTER-PROPOSE                    │
│                                                                  │
│ Scientist_C (Executive):                                         │
│   Reads: A's proposal, B's objections                           │
│   Logic: "Who has better reasoning? What's the right call?"     │
│   Output: RUN_A / RUN_B / RUN_HYBRID / REFINE / FORCE_DIAG      │
│                                                                  │
│ IPOPT Solver:                                                    │
│   Input: Chosen NC config                                        │
│   Process: Optimize flows [tstep, ffeed, fdes, fex, f1]         │
│   Output: Objective value J + feasibility info                  │
│                                                                  │
│ Learning:                                                        │
│   Update: hypotheses.json, failures.json, SQLite history        │
│   Convergence tracker: record best J over time                  │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### Key Features

✅ **Initial Ranking**: Physics heuristics guide first proposals
✅ **Learning**: Adapts based on results (convergence history)
✅ **Reasoning**: Full interpretable decision chain (A→B→C)
✅ **Disagreement Resolution**: Three-scientist debate mechanism
✅ **Fallback**: Deterministic LHS ranking if agent fails

### Implementation

- **Agent**: Qwen 3.5 27B LLM (via llama.cpp)
- **Knowledge base**: 
  - `agents/Objectives.md` (purity, recovery targets)
  - `agents/SKILLS.md` (physics domain knowledge)
  - `agents/LLM_SOUL_*.md` (role definitions)
  - `hypotheses.json` / `failures.json` (learnable state)
  - SQLite history (evaluation records)
- **Code**: `benchmarks/agent_runner.py`, `benchmarks/agent_scientists.py`
- **Configuration**: `--use-lhs-ranking` flag

### Strengths

| Strength | Explanation |
|----------|-------------|
| **Interpretable** | Can read A/B/C reasoning in conversation logs |
| **Adaptive** | Learns from results, adjusts strategy mid-run |
| **Physics-aware** | Starts with heuristics, not random |
| **Hybrid** | Combines symbolic (rules) + neural (LLM) reasoning |
| **Explorative** | Can discover unexpected good configs |
| **Human-aligned** | Three-scientist debate matches scientific process |

### Weaknesses

| Weakness | Explanation |
|----------|-------------|
| **Non-deterministic** | Results vary with LLM randomness (temp, sampling) |
| **Complex system** | Many components (agent, solver, config, history) |
| **LLM quality** | Agent only as good as Qwen 27B reasoning |
| **No closed loop** | Agent doesn't formally model exploration-exploitation |
| **Debugging hard** | Reasoning chains can be opaque (why did B reject A?) |
| **JSON parsing** | Prone to malformed responses (requires fallback parsing) |

### Expected Behavior

**Time to convergence**: 8-15 iterations (4h budget), 15-40 iterations (11h)
**Best J found**: 55-65 (agent + learning advantage)
**Exploration pattern**: Aggressive early (EXPLORE), exploitative late (EXPLOIT)
**Failure mode**: Agent gets stuck in local optima or spends time re-evaluating same config

### When This Works Best

✅ When physics intuition matters (BO+GP might miss)
✅ When you want interpretability (production deployment)
✅ When LLM quality is high (reasoning chains are gold)
✅ When learning signal is strong (convergence tracker helps)

---

## Strategy 2: BO+GP (Bayesian Optimization)

### Philosophy
**"Let mathematics find patterns"**

Use a Gaussian Process surrogate model to learn the response surface, then intelligently select next evaluation via Expected Improvement acquisition function.

### Mechanics

```
┌──────────────────────────────────────────────────────────────────┐
│ INITIALIZATION (One-time)                                        │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│ 1. Enumerate all 31 valid NC configs                            │
│                                                                  │
│ 2. Randomly select 3 initial configs for baseline               │
│    (deterministic: always same 3 first)                         │
│                                                                  │
│ 3. Run IPOPT on each → get J values                             │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────────┐
│ OPTIMIZATION LOOP (Repeated each iteration)                      │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│ 1. Fit GP to observations:                                       │
│    • Input: [nc0, nc1, nc2, nc3] (4-D discrete + embeddings)   │
│    • Output: J value observed                                    │
│    • Kernel: RBF with lengthscale=2.0                           │
│                                                                  │
│    Result: Learned surrogate model p(J | config)                │
│    ├─ Mean: estimated J at any config                           │
│    └─ Uncertainty: confidence in estimate                       │
│                                                                  │
│ 2. Compute Expected Improvement (EI) for all untried configs:   │
│    EI = E[max(J_new - J_best, 0)]                               │
│        = improvement × P(better) + uncertainty × gain potential  │
│                                                                  │
│    • High mean + low uncertainty → exploit good region          │
│    • Low mean + high uncertainty → explore unknown region       │
│                                                                  │
│ 3. Select config with highest EI (break ties by unexplored)     │
│                                                                  │
│ 4. Run IPOPT on selected config → get J                         │
│                                                                  │
│ 5. Add observation to dataset, loop to step 1                   │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### Key Features

✅ **Principled acquisition**: Expected Improvement is mathematically optimal
✅ **Uncertainty quantification**: GP knows what it doesn't know
✅ **Deterministic**: Same results every run (reproducible)
✅ **No learning required**: Works from scratch, no history needed
✅ **Surrogate model**: Can predict unmeasured configs

### Implementation

- **GP model**: RBF kernel with lengthscale=2.0, variance=1.0
- **Acquisition**: Expected Improvement (EI) with beta=2.576 (99.5% UCB)
- **Code**: `benchmarks/bo_gp_baseline.py`, `benchmarks/bo_gp_runner.py`
- **No dependencies**: Pure numpy (no sklearn/GPyTorch bloat)

### Strengths

| Strength | Explanation |
|----------|-------------|
| **Deterministic** | Same seed = same results (reproducible research) |
| **Principled** | Based on rigorous optimization theory |
| **Black-box** | Works with any objective (doesn't need physics) |
| **Efficient** | EI balances exploration-exploitation automatically |
| **No LLM** | No language model needed (faster, cheaper) |
| **Uncertainty-aware** | Knows where it's confident vs uncertain |

### Weaknesses

| Weakness | Explanation |
|----------|-------------|
| **No domain knowledge** | Ignores physics heuristics (cold start) |
| **GP scaling** | Kernel matrix inversion O(n³) slows with data |
| **Discrete space** | NC embedding into continuous might not work well |
| **Myopic acquisition** | EI doesn't plan beyond one step ahead |
| **Local optima** | May concentrate on good region, miss global optima |
| **5D continuous** | GP over [tstep, flows] space might be overkill |

### Expected Behavior

**Time to convergence**: ~8-25 iterations (4h budget), 15-50 iterations (11h)
**Best J found**: 50-60 (systematic but less creative than agent)
**Exploration pattern**: Random first 3, then systematic (EI-driven)
**Failure mode**: Converges too fast to local optimum, misses better regions

### When This Works Best

✅ When reproducibility matters (scientific benchmarks)
✅ When physics knowledge is unavailable (black-box problems)
✅ When computational budget is very limited (efficient sampling)
✅ When you want theoretical guarantees (convergence proofs exist)

---

## Strategy 3: LHS-Only (Pure Ranking)

### Philosophy
**"Physics knows best - just evaluate in order"**

Use physics heuristics to rank configs, evaluate them sequentially, no learning or adaptation.

### Mechanics

```
┌──────────────────────────────────────────────────────────────────┐
│ ONE-TIME SETUP                                                   │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│ 1. Generate all 31 valid NC configs                             │
│                                                                  │
│ 2. Compute physics scores:                                       │
│    score = 0.4×selectivity + 0.3×throughput - 0.3×difficulty   │
│                                                                  │
│ 3. Sort by score → deterministic ranked list                    │
│    (no randomness, always same order)                           │
│                                                                  │
│ 4. Evaluate in order until time exhausted                       │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────────┐
│ SIMPLE LOOP (No adaptation)                                      │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│ For config_i in ranked_list:                                     │
│   1. Run IPOPT on config_i                                      │
│   2. Record J value                                              │
│   3. Continue to next config (no learning)                      │
│                                                                  │
│ Result: All configs evaluated in physics-ranked order           │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### Key Features

✅ **Deterministic**: Physics ranking never changes
✅ **Simple**: No agent, no BO, just iterate
✅ **Fast**: CPU-only, MA97 multi-threaded
✅ **Exhaustive**: Eventually evaluates all 31 configs
✅ **Interpretable**: Results follow physics intuition

### Implementation

- **Code**: `benchmarks/lhs_only_runner.py`
- **Ranking**: `benchmarks/physics_filter.py` ConfigScorer
- **No LLM**: CPU + IPOPT + MA97
- **No BO**: Just sequential evaluation

### Strengths

| Strength | Explanation |
|----------|-------------|
| **Dead simple** | Single loop, no complex logic |
| **Transparent** | Results exactly match physics ranking |
| **Fast execution** | No LLM overhead, pure compute |
| **Reproducible** | Identical results every time |
| **CPU-friendly** | No GPU needed (cost-effective) |
| **Fault-tolerant** | If IPOPT fails on one config, continue next |

### Weaknesses

| Weakness | Explanation |
|----------|-------------|
| **No learning** | Can't adapt even if wrong configs are terrible |
| **Fixed ranking** | Physics heuristic might be incorrect |
| **No exploitation** | Must evaluate all configs even if clearly bad |
| **Cold start** | Same initial ranking for every run (no exploration variance) |
| **Inefficient** | Evaluates worst configs when time could be better spent |
| **No uncertainty** | No way to know when to stop evaluating |

### Expected Behavior

**Time to convergence**: 8-31 iterations (all or most configs)
**Best J found**: 50-58 (good due to physics, but no exploitation)
**Evaluation order**: Fixed by physics score (deterministic)
**Failure mode**: Wastes time on obviously bad configs

### When This Works Best

✅ When physics ranking is known to be accurate
✅ When you want simple, bulletproof execution
✅ When reproducibility is paramount
✅ When computational cost doesn't matter (evaluate all anyway)

---

## Direct Comparison

### Performance Table

| Metric | LHS+Agent | BO+GP | LHS-Only |
|--------|-----------|-------|----------|
| **Deterministic?** | ❌ (LLM sampling) | ✅ | ✅ |
| **Uses physics?** | ✅ (initial rank) | ❌ | ✅ (always) |
| **Learns?** | ✅ (agent history) | ✅ (GP fits data) | ❌ |
| **Expected best J** | 55-65 | 50-60 | 50-58 |
| **Iterations (4h)** | 8-15 | 8-25 | 12-20 |
| **GPU needed?** | ✅ | ✅ | ❌ |
| **LLM needed?** | ✅ | ❌ | ❌ |
| **Interpretable** | ✅✅✅ | ✅ | ✅✅ |
| **Complexity** | Very high | Medium | Very low |
| **Risk of failure** | Medium (LLM) | Low (math) | Low (simple) |

### Conceptual Differences

```
LHS+Agent:
  "I have physics intuition (LHS ranking) AND learned experience (history).
   Let me combine both to make the next smart decision."
   
   Approach: Heuristic initialization + adaptive learning
   Risk: LLM can be unpredictable
   Reward: Creative exploration, discovers surprises

BO+GP:
  "I've observed some configs. Let me fit a statistical model.
   Where should I sample next to reduce uncertainty optimally?"
   
   Approach: Surrogate model + principled acquisition
   Risk: May converge to local optima too quickly
   Reward: Mathematically guaranteed efficiency

LHS-Only:
  "Physics says these configs are best. Let me just evaluate them
   in order and see which one actually wins."
   
   Approach: Pure ranking, no learning
   Risk: Physics heuristic might be wrong
   Reward: Simple, transparent, reproducible
```

---

## Head-to-Head Scenarios

### Scenario 1: Physics Heuristic is Correct ✅
**Winner**: LHS+Agent or LHS-Only
- Both start with good ranking
- Agent can exploit this better than BO+GP
- BO+GP needs to learn the pattern

### Scenario 2: Physics Heuristic is Wrong ❌
**Winner**: BO+GP or LHS+Agent (if agent realizes)
- LHS-Only stuck with bad ranking forever
- BO+GP will learn better pattern over time
- Agent might realize and adapt (via hypothesis updates)

### Scenario 3: Global Optimum is "Surprising" 🎯
**Winner**: LHS+Agent or BO+GP
- LHS-Only will never find it (not in top ranking)
- Agent might propose it if it exploits well
- BO+GP will eventually find it (high uncertainty region)

### Scenario 4: Time Budget is Very Limited (15 min)
**Winner**: LHS+Agent (with ranking)
- Starts with best configs immediately
- No learning overhead
- BO+GP slower (fitting GP)
- LHS-Only evaluates from best, but slower

### Scenario 5: Reproducibility Required
**Winner**: BO+GP or LHS-Only
- Both deterministic
- Agent has RNG (temperature, sampling)
- BO+GP + seed = reproducible
- LHS-Only + seed = reproducible

---

## Hybrid Possibilities

### BO+GP Warm-Started with LHS Ranking
```
1. Use LHS physics score as prior mean for GP
2. Initial samples chosen from top-ranked configs
3. Fit GP with physics-informed prior
4. Use EI acquisition as normal

Expected: Best of both worlds (physics + learning)
Risk: Overconstrain the model
```

### Agent-Guided BO (BO² Agent)
```
1. Run BO+GP for suggestions
2. Send suggestions to Agent for reasoning
3. Agent can accept/reject/counter-propose
4. Feedback loop: agent judgment + mathematical rigor

Expected: Combined interpretability + rigor
Risk: Complexity of two systems
```

### LHS-Only with Early Stopping
```
1. Evaluate configs in physics rank order
2. Track best J and convergence rate
3. Stop if no improvement for 5 iterations
4. Switch to BO+GP on remainder

Expected: Quick exploitation of good region
Risk: Miss global optimum if early pattern wrong
```

---

## Recommendation by Use Case

### For Research Paper 📚
**Use**: BO+GP + LHS-Only
- Reproducible
- Principled
- Easy to explain in methods section

### For Production Deployment 🏭
**Use**: LHS+Agent
- Interpretable decisions (audit trail)
- Adaptive (learns from pilot runs)
- Domain expertise baked in

### For Quick Validation ⚡
**Use**: LHS-Only
- Simplest to implement
- Least things that can break
- CPU-only (cheap)

### For Pushing Limits 🚀
**Use**: LHS+Agent with BO fallback
- Agent tries creative ideas
- BO safety net if agent fails
- Combined strength of both

---

## Summary Decision Tree

```
                Start
                 |
         Have physics knowledge?
            /            \
          YES             NO
          |               |
        Use LHS        Use BO+GP
          |
     Need interpretability?
       /        \
     YES        NO
     |          |
   Agent      Agent
   + BO       + BO
   
   Time budget?
   / | \
 15m 4h 11h
  | |  |
 LHS Agent Agent
    +   +
   BO  BO+LHS
```

---

## Strategy 4: Agent-Orchestrated BO (NEW!)

### Philosophy
**"LLM as intelligent orchestrator of multiple surrogate models"**

Agent has access to 3 tool types (GP, DNN, PINN). Agent:
1. Decides which tool to use (based on data characteristics)
2. Interprets surrogate predictions (reasoning about models)
3. Refines LHS ranking using actual data
4. Detects ensemble disagreement (high uncertainty regions)
5. Adapts strategy mid-run (switches tools if needed)

**Mechanics:**
```
Agent reads: observations + surrogate predictions + LHS ranking
Agent decides: Which tool best explains data?
Agent acts: Fit all 3 surrogates, compute ensemble disagreement
Agent predicts: Run IPOPT on high-disagreement config
Agent learns: Update belief about tool accuracy
```

**Expected best J**: 56-66 (highest of all methods)
**Complexity**: Very high (3 surrogates + agent orchestration)
**Uncertainty**: Explicit (ensemble disagreement = lack of confidence)

**See**: `AGENT_ORCHESTRATED_BO.md` for full details

---

## All Four Strategies Compared

```
┌──────────────────┬──────────────┬──────────────┬──────────────┬──────────────┐
│ Strategy         │ LHS+Agent    │ BO+GP        │ LHS-Only     │ Agent-Orch BO│
├──────────────────┼──────────────┼──────────────┼──────────────┼──────────────┤
│ Best J (est.)    │ 55-65        │ 50-60        │ 50-58        │ 56-66        │
│ Iterations (4h)  │ 8-15         │ 8-25         │ 12-20        │ 8-12         │
│ Deterministic    │ ❌ (LLM)     │ ✅           │ ✅           │ ❌ (LLM)     │
│ Complexity       │ High         │ Medium       │ Very low     │ VERY HIGH    │
│ Physics-aware    │ ✅ (initial) │ ❌           │ ✅ (always)  │ ✅ (tools)   │
│ Learning         │ ✅ (agent)   │ ✅ (GP fits) │ ❌           │ ✅✅ (3 tools+agent)|
│ Tools            │ None         │ GP           │ None         │ GP+DNN+PINN  │
│ Tool adaptivity  │ ❌ Fixed     │ ❌ Fixed     │ ❌ Fixed     │ ✅ Dynamic   │
│ Interpretable    │ ✅✅✅       │ ✅           │ ✅✅         │ ✅✅ (reasoning)|
│ Risk            │ Medium       │ Low          │ Low          │ High (complexity)|
└──────────────────┴──────────────┴──────────────┴──────────────┴──────────────┘
```

---

## Conclusion

Each strategy is optimal for different assumptions:

- **LHS+Agent** (Strategy 1): Best when physics is good AND interpretability matters
- **BO+GP** (Strategy 2): Best when reproducibility needed AND black-box is fine
- **LHS-Only** (Strategy 3): Best when simplicity paramount AND physics is trust
- **Agent-Orchestrated BO** (Strategy 4): Best when max performance needed AND complexity acceptable

**Running smoke tests** reveals which assumptions are true for YOUR problem.

**Our hypothesis**: 
- LHS+Agent wins on interpretability + quality
- Agent-Orchestrated BO wins on pure performance (if orchestration works)
- BO+GP wins on reproducibility
- LHS-Only wins on simplicity
