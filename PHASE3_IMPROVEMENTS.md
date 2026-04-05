# Phase 3 Strategy Improvements: Before/After BO Knowledge

**Date**: April 5, 2026  
**What Changed**: Integration of BO/LHS/GP research into Phase 3 strategy framework

---

## Executive Summary

### Before (Original Strategies)
```
Strategy 1: Heuristic scoring (ad-hoc)
Strategy 2: GP predictions (exploitation only)
Strategy 3: Agent reasoning (intuitive)
Strategy 4: Agent+BO consensus (limited BO grounding)

Problem: Limited principled reasoning about exploration vs exploitation
```

### After (BO-Informed Strategies)
```
Strategy 1: Heuristic baseline (now serving as reference point)
Strategy 2: BO-baseline with explicit UCB logic
Strategy 3: Agent+LHS with BO-inspired exploration reasoning
Strategy 4: Agent+BO with principled acquisition function

Improvement: Explicit BO theory grounds all strategies
```

---

## Strategy 1: Heuristic Baseline

### Before
```
Score: (purity × recovery × productivity) 
Pick top 5
```

### After
```
Score: (purity × recovery × productivity) / (variance + ε)
Pick top 5, document as exploitation-only baseline

NEW ADDITION:
- Explicit designation as "pure exploitation" strategy
- Serves as reference for comparison
- Helps interpret whether other strategies add value
```

**Why This Matters**: Strategy 1 is now explicitly understood as a null hypothesis. If any of the smarter strategies beat it, we know BO/agent reasoning provides value.

---

## Strategy 2: BO Baseline

### Before
```
1. Fit GP to screening data
2. Predict on all NCs: μ(NC)
3. Pick top 5 by predicted value μ

Problem: Pure exploitation (ignores σ)
         No exploration reasoning
         Uses μ but not uncertainty
```

### After
```
1. Fit GP to screening data
   └─ Kernel: Matérn(ν=2.5) ← Specified why
   └─ Hyperparameters: Optimize via marginal likelihood ← How to fit

2. Predict on all NCs: μ(NC), σ(NC)
   └─ Now compute both mean AND uncertainty

3. Rank by UCB-inspired score:
   acquisition(NC) = μ(NC) + small_β × σ(NC)
   └─ Exploitative (small β), but acknowledges uncertainty

4. Pick top 5, explain reasoning
   "These NCs combine high predicted performance 
    with confidence in prediction."
```

**What Changed**:
- ✅ Explicit kernel choice and why
- ✅ Uncertainty quantification (σ) now computed
- ✅ UCB-inspired acquisition logic (even if β is small)
- ✅ Reasoning about exploitation vs exploration

**Expected Improvement**: +1-2% over original (better baseline understanding of uncertainty)

---

## Strategy 3: Agent+LHS

### Before
```
Agent reads LHS results and scores each NC by:
  1. Heuristics: balance, stability, feasibility
  2. Direct metrics
  3. Some reasoning about good vs bad
  
Problem: Ad-hoc scoring
         No principled exploration/exploitation balance
         Heuristics not grounded in theory
         Agent doesn't explain uncertainty
```

### After
```
Agent reads LHS results and reasons:

1. DISTRIBUTION ANALYSIS
   For each NC, examine 100 seed results:
   - Success rate: % of seeds that are feasible
   - Variance: σ across successful seeds
   - Pattern recognition: clustered vs spread results
   
   Interpretation:
   ├─ High success + low variance → Exploited (well-understood)
   ├─ High success + high variance → Multimodal (interesting!)
   ├─ Low success + high variance → Unexplored potential!
   └─ Low success + low variance → Dead end

2. EXPLORATION POTENTIAL SCORING (BO-INSPIRED)
   exploration_potential(NC) = 
     √(success_variance + search_sparsity) 
     ────────────────────────────────────
               expected_value
   
   Theory: High variance = uncertain (explore!)
           Low success but some good = potential (explore!)
           
3. EXPLOITATION vs EXPLORATION BALANCE (BO-GROUNDED)
   Budget 5 NCs → allocate:
   - 2-3 to exploitation (safe, high performance)
   - 2-1 to exploration (potential despite uncertainty)
   
   Why this ratio: BO theory says explore 20-40% in early stages

4. DETAILED REASONING
   Agent explains EACH selection:
   "NC [2,1,2,3] selected for EXPLORATION because:
    - Only 40% seed success (vs 85% average)
    - High variance in successful seeds (0.089)
    - But best result is 0.78 (competitive)
    → Suggests: Under-optimized, high upside potential
    → Decision: Worth allocating resources to resolve uncertainty"
```

**What Changed**:
- ✅ Systematic analysis of seed distribution (not just summary stats)
- ✅ BO-inspired exploration potential scoring
- ✅ Principled exploitation/exploration balance
- ✅ Explicit uncertainty-driven reasoning
- ✅ Detailed explanations for each choice

**Expected Improvement**: +3-5% over Strategy 1 (better balance, discovers missed opportunities)

---

## Strategy 4: Agent+BO

### Before
```
1. Fit GP to screening data
2. Fit DNN for consensus
3. Agent reads both models
4. Agent selects top 5
   └─ Based on: model disagreement, heuristics, intuition

Problem: No explicit acquisition function
         BO framework loosely applied
         Doesn't quantify exploration vs exploitation
         Agent reasoning not grounded in BO math
```

### After
```
1. Fit Gaussian Process
   └─ Matérn(ν=2.5), optimize hyperparameters

2. Agent Computes Principled Acquisition Function
   
   For each NC, compute:
   
   A) EXPLOITATION (BO: Confidence Bound)
      ucb(NC) = μ(NC) + √(2 log(T)) × σ(NC)
      "How good could this NC be? (optimistic estimate)"
   
   B) DOMAIN KNOWLEDGE BONUS
      domain_bonus(NC) = 
        zone_balance(NC) * 0.05 +
        physical_intuition(NC) * 0.05 +
        feasibility_history(NC) * 0.03 +
        addresses_bottleneck(NC) * 0.07
      "Does physics support trying this NC?"
   
   C) EXPLORATION DIVERSITY
      diversity_bonus(NC) = σ(NC) / max(all_σ)
      "How much uncertainty needs resolving here?"
   
   D) FINAL SCORE (Principled Ensemble)
      final(NC) = 
        0.60 × ucb(NC) +           [Trust BO math]
        0.20 × domain_bonus(NC) +  [Leverage physics]
        0.15 × diversity_bonus +   [Explicit exploration]
        0.05 × heuristic_baseline   [Fallback consistency]

3. Portfolio Selection with Reasoning
   ├─ Rank 1: Exploitation leader (high μ, low σ)
   ├─ Rank 2-3: Exploitation backup (safety)
   ├─ Rank 4-5: Exploration opportunity (high σ, reasonable μ)
   └─ All decisions explained with multi-angle reasoning

4. Detailed Explanations for Each NC
   "NC [2,1,2,3] selected for EXPLORATION because:
    ├─ BO Acquisition (μ + β·σ): Score 0.798 (top 2)
    │  └─ Predicted mean: 0.682 (mid-range)
    │  └─ Uncertainty: 0.089 (high! relative to others)
    │  └─ Interpretation: Could be strong with better optimization
    │
    ├─ Domain Knowledge: Zone 2 is tight (risky)
    │  └─ Bonus: -0.01 (slightly cautious)
    │  └─ Interpretation: Requires precise tuning but possible
    │
    ├─ Exploration Value: 1.00 (MAXIMUM)
    │  └─ Interpretation: Highest uncertainty—most to learn
    │
    └─ Recommendation: Explore to resolve uncertainty
       Expected upside: 0.70-0.80 if optimized well"
```

**What Changed**:
- ✅ Explicit BO acquisition function (UCB)
- ✅ Domain knowledge integrated with weights (0.20 factor)
- ✅ Exploration diversity explicitly scored
- ✅ Principled ensemble of three components
- ✅ Detailed explanation of each decision component
- ✅ Exploration/exploitation ratio justified by BO theory
- ✅ Risk assessment included
- ✅ Portfolio approach (2-3 exploitation + 2 exploration)

**Expected Improvement**: +5-8% over Strategy 1 (best balance + BO + domain knowledge)

---

## Side-by-Side Comparison: Key Improvements

### Acquisition Function Sophistication

```
BEFORE:
├─ Strategy 1: Pure heuristic (no theory)
├─ Strategy 2: μ only (ignores σ)
├─ Strategy 3: Heuristic scoring (ad-hoc)
└─ Strategy 4: Agent intuition (informal)

AFTER:
├─ Strategy 1: Heuristic (labeled as exploitation-only)
├─ Strategy 2: UCB-inspired (explicit BO logic)
├─ Strategy 3: Exploration potential (BO-grounded)
└─ Strategy 4: Full BO acquisition + domain bonus (principled ensemble)
```

### Exploration vs Exploitation Reasoning

```
BEFORE:
├─ No explicit consideration
├─ No principled balance
├─ Agent intuition only
└─ No quantification

AFTER:
├─ Strategy 3: Explicit 60/40 or 70/30 balance
├─ Strategy 4: Acquisition function that auto-balances
├─ Both: Theoretical justification from BO
└─ Both: Ratio adapted to remaining budget
```

### Domain Knowledge Integration

```
BEFORE:
├─ Strategy 3: Informal heuristics
└─ Strategy 4: Vague consensus

AFTER:
├─ Strategy 3: Systematic analysis of zone balance, feasibility
├─ Strategy 4: Quantified domain bonus (0.20 weight in ensemble)
└─ Both: Explained component-by-component
```

### Uncertainty Quantification

```
BEFORE:
├─ Strategy 2: Computed but not used meaningfully
├─ Strategy 3: Not explicit
└─ Strategy 4: Agent intuition about uncertainty

AFTER:
├─ Strategy 2: σ used in UCB (explicit exploitation choice)
├─ Strategy 3: Variance analyzed as exploration signal
├─ Strategy 4: σ weighted in acquisition (diversity_bonus = 0.15)
└─ All: Uncertainty reasoning is transparent
```

### Transparency & Explainability

```
BEFORE:
├─ Strategy 1: "Top 5 by score" (no explanation)
├─ Strategy 2: "Highest predicted values" (surface-level)
├─ Strategy 3: Agent reasoning (not quantified)
└─ Strategy 4: Model consensus (black box)

AFTER:
├─ Strategy 1: Explicit exploitation baseline (interpretable)
├─ Strategy 2: UCB reasoning + component breakdown
├─ Strategy 3: Distribution analysis + exploration potential formula
└─ Strategy 4: Acquisition function + 3-way reasoning:
   ├─ Statistical (μ, σ)
   ├─ Domain (physics intuition)
   └─ Exploration (information value)
```

---

## Expected Performance Ranking

### Theoretical Prediction

```
Strategy 4 (Agent+BO) = BEST       ← 60% win probability
   Reason: Combines BO math + domain knowledge + exploration

Strategy 3 (Agent+LHS) = GOOD      ← 20% win probability
   Reason: Explores well, but no statistical model

Strategy 2 (BO Baseline) = DECENT  ← 15% win probability
   Reason: Statistical, but pure exploitation

Strategy 1 (Heuristic) = BASELINE  ← 5% win probability
   Reason: Simple, no exploration or statistics
```

### Why This Ranking?

**Strategy 4 Wins Because**:
1. BO math (UCB) is theoretically optimal for exploration/exploitation
2. Domain knowledge catches issues BO might miss
3. Portfolio approach (2-3 exploit + 2 explore) is balanced
4. Can leverage all 3200 Phase 2 points + physics

**Strategy 3 Could Win If**:
1. GP assumptions invalid (non-smooth function, weird kernel)
2. Domain knowledge dominates for this specific process
3. Exploration is more valuable than BO exploitation

**Strategy 2 Could Lose To All Because**:
1. Pure exploitation + weak uncertainty handling
2. No exploration mechanism
3. Ignores domain knowledge

**Strategy 1 Is Baseline Because**:
1. No learning across the 3200 data points
2. Pure exploitation
3. No domain integration beyond heuristics

---

## Specific BO Improvements Implemented

### 1. Kernel Selection (Strategy 2+4)
```
BEFORE: GP with default RBF kernel

AFTER:  GP with Matérn(ν=2.5)
        └─ Why: SMB process smoothness unknown
                Matérn less restrictive than RBF
                Handles slightly rough functions
```

### 2. Hyperparameter Optimization (Strategy 2+4)
```
BEFORE: Hyperparameters not specified

AFTER:  Optimize via marginal likelihood
        └─ Why: Automatic regularization
                Balances fit with complexity
                Prevents overfitting
```

### 3. Uncertainty-Driven Decisions (Strategy 3+4)
```
BEFORE: Strategy 2 computed σ but didn't use it
        Strategy 3 ignored it

AFTER:  Strategy 3: Variance = exploration signal
        Strategy 4: σ contributes 0.15 to acquisition
        └─ Why: High uncertainty = high information value
```

### 4. Principled Exploration/Exploitation (Strategy 3+4)
```
BEFORE: Implicit, ad-hoc

AFTER:  Strategy 3: 60/40 or 70/30 heuristic split
        Strategy 4: Automatic via √(2 log(T)) in UCB
        └─ Why: BO theory justifies this balance
```

### 5. Domain Knowledge Weight (Strategy 4)
```
BEFORE: Informal consensus

AFTER:  Explicit 0.20 weight in ensemble
        Components:
        - Zone balance (0.05)
        - Physical intuition (0.05)
        - Feasibility history (0.03)
        - Bottleneck fixing (0.07)
        
        Why: Quantifies domain contribution
             Can tune if needed (0.10-0.30 range)
```

---

## How to Validate These Improvements

### Test 1: Does Exploration Help?
```
Compare: Strategy 1 (pure exploit) vs Strategy 3/4 (explore)
If S3/S4 beat S1:
  ✓ Exploration is valuable for SMB
  ✓ BO reasoning is sound
Metric: Top 5 results better than best heuristic
```

### Test 2: Does BO Beat Domain Knowledge?
```
Compare: Strategy 3 (domain + heuristic) vs Strategy 2 (BO pure)
If S2 wins:
  ✓ Statistical learning dominates
  ✓ Domain heuristics are noise
If S3 wins:
  ✓ Domain knowledge matters more
  ✓ BO assumptions may not hold
```

### Test 3: Does Full Integration Win?
```
Compare: Strategy 4 (BO + domain) vs all others
If S4 wins:
  ✓ Synergy between BO and domain is real
  ✓ Principled ensemble approach works
  ✓ LLM agent effectively combines approaches
Metric: S4 achieves highest productivity in Phase 3
```

### Test 4: Is Exploration Balanced Right?
```
If best solution is in Strategy 4's "exploration" picks:
  ✓ Allocation 2-3 exploit + 2-1 explore was correct
  ✓ BO guidance on exploration/exploitation is accurate
If best is in exploit picks:
  ✓ Could reduce exploration budget next round
```

---

## Summary of Changes

| Aspect | Before | After | Impact |
|--------|--------|-------|--------|
| **Kernel choice** | Default | Matérn(2.5) | Better assumptions |
| **Hyperparameter fit** | Not specified | Marginal likelihood | Automatic regularization |
| **Exploitation logic** | Ad-hoc | UCB-inspired | Principled |
| **Exploration logic** | Implicit | Explicit (σ-driven) | Quantifiable |
| **Domain integration** | Informal | 0.20 weight ensemble | Transparent |
| **Uncertainty use** | Computed, ignored | Actively used | Better decisions |
| **Portfolio approach** | Top 5 scoring | 2-3 exploit + 2 explore | Balanced risk |
| **Explainability** | Low | Very high | More trustworthy |
| **BO grounding** | Loose | Principled | Theoretically sound |

---

## Next Steps

1. **Implement Strategy 4 with full BO logic** (in benchmarks/phase3_strategy4_agent_bo.py)
2. **Run all 4 strategies** on Phase 2 data
3. **Compare results** (which strategy found best NC?)
4. **Validate assumptions** (was BO reasoning correct?)
5. **Iterate** (refine weights, explore parameters if needed)

**Expected Outcome**: Strategy 4 should outperform others by 5-10% due to principled BO integration + domain knowledge synergy.

