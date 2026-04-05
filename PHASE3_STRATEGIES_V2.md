# Phase 3: Updated Strategy Framework with BO Intelligence

**Updated**: April 5, 2026  
**Based on**: Deep research into LHS, GP, BO, and LLM agent integration

---

## Overview: Four Intelligent Selection Strategies

All strategies operate on Phase 2 foundation (100 LHS seeds per NC × 32 NCs = 3200 optimized points).

Each strategy represents a different philosophy of balancing:
- **Exploitation** (refine known good solutions)
- **Exploration** (discover new high-value regions)
- **Domain Knowledge** (physics-based reasoning)
- **Transparency** (explainability of decisions)

---

## Strategy 1: Heuristic Baseline (Pure Exploitation)

### Philosophy
Simple, interpretable, domain-knowledge-free baseline. Pick top 5 by direct metrics.

### Method

```
Step 1: Compute Heuristic Scores
For each NC:
  score = (purity × recovery × productivity) / (variance + ε)
  └─ Numerator: Good performance across metrics
  └─ Denominator: Penalize variability across seeds
  
Step 2: Rank and Select Top 5
  Sort NCs by score
  Select top 5
  
Step 3: Output with Minimal Reasoning
  "Pick [1,1,2,4], [1,3,2,2], ... by highest metric product"
```

### Acquisition Logic
- **Purely exploitative**: Only considers mean performance
- **No exploration**: Ignores uncertainty (high-variance NCs skipped)
- **No domain knowledge**: Pure arithmetic

### Expected Outcome
- ✓ Fast, interpretable
- ✓ Catches obvious winners
- ✗ Misses promising but unexplored NCs
- ✗ Over-penalties high-variance candidates
- ✗ No physics reasoning

### Results We'd Expect
- Safe selections (0.70-0.75 productivity range)
- Consistent, but modest optimization gains
- Baseline for comparison

---

## Strategy 2: BO Baseline (GP-Driven Exploitation)

### Philosophy
Use statistical surrogate (GP) to predict untested NC configurations, pick top 5 by prediction.

### Method

```
Step 1: Fit Gaussian Process to Phase 2 Data
  Inputs: 3200 (NC layout + best seed parameters)
  Targets: [productivity, purity, recovery]
  Kernel: Matérn(ν=2.5) 
  Hyperparameters: Optimize via marginal likelihood
  
Step 2: Predict on All NCs
  For each NC:
    μ(NC) = GP posterior mean prediction
    σ(NC) = GP posterior std (uncertainty)
    
Step 3: Rank by Predicted Value (Exploitation)
  acquisition(NC) = μ(NC)  ← Pure mean, ignore uncertainty
  
Step 4: Select Top 5 by Predicted Productivity
  UCB_simple(NC) = μ(NC) + c × σ(NC)  where c is small
  └─ Small c → exploitation focus
```

### Acquisition Logic
- **Exploitative**: Maximize mean prediction μ
- **Minimal exploration**: σ only used for confidence (high σ → less preferred)
- **No domain knowledge**: Pure statistical model
- **Data-driven generalization**: Uses all 3200 seed optimizations to infer patterns

### Expected Outcome
- ✓ Better than heuristic (uses full data)
- ✓ Captures nonlinear patterns
- ✓ Uncertainty quantification available
- ✗ Still purely exploitative
- ✗ No domain knowledge integration
- ✗ Kernel assumptions may not hold

### Results We'd Expect
- Good selections (0.72-0.77 productivity range)
- Better than Strategy 1 by 3-5%
- High confidence (low σ) on popular layouts

---

## Strategy 3: Agent+LHS (Heuristic + BO Reasoning)

### Philosophy
Agent reads raw LHS data and reasons about exploration vs exploitation balance inspired by BO concepts (without GP fit).

### Method

```
Step 1: Agent Analyzes LHS Data Distribution
For each NC:
  - Count successful seeds (feasible results)
  - Compute variance across successful seeds
  - Identify consistency/variability patterns
  
  Interpretation:
    High success rate + low variance → Exploited region
    High success rate + high variance → Multimodal (interesting!)
    Low success rate + low variance → Fundamentally limited
    Low success rate + high variance → Underexplored! (potential)
  
Step 2: Agent Computes "Exploration Potential"
exploration_potential(NC) = 
  (success_variance + search_sparsity) / expected_value
  
  Why this formula:
    - High variance = uncertain behavior (explore)
    - Low success rate but some good = potential (explore)
    - High expected value = worth exploring
    
Step 3: Agent Balances Exploitation vs Exploration
  LHS-inspired balance: "If we have budget B for 5 NCs,
  allocate approximately:
    - 2-3 to exploitation (high score, low variance)
    - 2 to exploration (potential despite uncertainty)
    - 0-1 to balanced candidates"
    
Step 4: Agent Selects Portfolio and Explains Reasoning
  Type 1 (Exploitation - 3 NCs):
    "These excel consistently. Ready for refinement."
    
  Type 2 (Exploration - 2 NCs):
    "High variance/low success suggest unexplored potential.
     Worth allocating resources here."
```

### Acquisition Logic
- **Heuristic-based**: Uses domain heuristics (balance, stability, feasibility)
- **BO-inspired**: Explicitly reasons about exploration/exploitation tradeoff
- **LHS perspective**: Treats seed distribution as exploration signal
- **Reasoned**: Agent explains every choice

### Key Difference from Strategy 1
```
Strategy 1: Pick top 5 by score
Strategy 3: Pick diverse portfolio:
  - Safe choices (high score)
  - Risky bets (high potential)
  - Reasoning: Physical intuition about each
```

### Expected Outcome
- ✓ Better exploration balance than Strategy 1
- ✓ Maintains physical reasoning
- ✓ Explainable decisions
- ✓ Potential to catch dark horses
- ✗ No statistical model (GP) for uncertainty
- ✗ Heuristics still ad-hoc

### Results We'd Expect
- Balanced selections (0.70-0.76 productivity)
- More diverse portfolio than Strategy 1
- Might discover 1-2 unexpected winners
- Better than Strategy 1 by 2-4%

---

## Strategy 4: Agent+BO (Principled Bayesian + Reasoning)

### Philosophy
Agent reads GP surrogate (μ, σ) and applies BO-grounded acquisition function with domain knowledge integration.

### Method

```
Step 1: Fit Gaussian Process to Phase 2 Data
  [Same as Strategy 2]
  Kernel: Matérn(ν=2.5)
  Hyperparameters: Optimize via marginal likelihood
  
Step 2: Agent Computes Acquisition Function
For each NC:
  
  A. Standard BO Acquisition (UCB)
     ucb(NC) = μ(NC) + β × √(2 log(T)) × σ(NC)
     where β ~ 1.0-2.0 (tunable exploration parameter)
     
     Interpretation:
       - μ(NC): How good do we predict it to be?
       - σ(NC): How uncertain are we?
       - √(2 log(T)): Theoretical confidence bound
       
  B. Agent Domain Knowledge Bonus
     domain_bonus(NC) = 0 to +0.1
     
     Components:
       - Zone balance: -0.03 to +0.05
         "Do zones have reasonable column count?"
       - Physical intuition: -0.05 to +0.05
         "Does layout make sense physically?"
       - Feasibility history: -0.02 to +0.03
         "Do similar layouts tend to work?"
       - Addresses known bottleneck: +0.07
         "Does this fix a identified constraint?"
       
  C. Exploration Diversity Bonus
     diversity_bonus(NC) = σ(NC) / max(all_σ)
     "Which NCs have we learned least about?"
     
  D. Final Reasoned Acquisition
     final_score(NC) = (
       0.60 × ucb(NC) +                 ← Trust BO math
       0.20 × domain_bonus(NC) +        ← Leverage physics
       0.15 × diversity_bonus(NC) +     ← Explicit exploration
       0.05 × baseline_heuristic(NC)    ← Fallback consistency
     )
     
Step 3: Agent Ranks and Analyzes Tradeoffs
  Sort NCs by final_score
  For top 10: Generate reasoning explanation
  
Step 4: Agent Selects Diversified Portfolio
  Principle: Avoid all exploitation OR all exploration
  
  Selection Criteria:
    ├─ Rank 1: Highest exploitation (low σ, high μ)
    ├─ Rank 2-3: Strong exploitation (backup safety)
    ├─ Rank 4-5: Exploration + potential (high σ, reasonable μ)
    └─ Reason: Remaining budget allows discovery + refinement
    
  Sanity checks:
    - Are top 5 from different NC families? (diversity)
    - Does selection make physical sense? (domain check)
    - Does balance match budget expectations? (BO principles)
    
Step 5: Agent Generates Detailed Reasoning
  For each selected NC:
    "Why this NC:
     - Predicted performance: X (confidence: high/medium/low)
     - Exploration value: High σ suggests opportunity
     - Physical intuition: [specific domain reasoning]
     - Expected improvement: 0.01-0.05 gain possible
     - Risk assessment: [downside scenario]"
```

### Acquisition Logic (Detailed)

#### Exploitation Component
```
"Which NCs are predicted to be best?"
→ High μ(NC), low σ(NC)
→ Safe bets with strong performance
→ Ready for high-fidelity optimization
```

#### Exploration Component
```
"Which NCs have we learned least about?"
→ High σ(NC) = uncertain
→ Could surprise us positively or negatively
→ Worth exploring to resolve uncertainty
→ Aligns with BO theory: reduce variance
```

#### Domain Knowledge Component
```
"What does physics tell us about this NC?"
→ Zone balance: Do we have enough columns in each zone?
→ Physical bottlenecks: Feed zone vs desorbent zone tradeoff
→ Feasibility: Have similar layouts worked before?
→ Intuition: What would a process engineer expect?
```

### Example Acquisition Calculation

```
NC [1,1,2,4]:
├─ μ = 0.747, σ = 0.021 (high confidence)
├─ ucb = 0.747 + 1.5×√(2×log(T))×0.021 = 0.762
├─ domain_bonus = +0.04 (balanced zones, well-studied)
├─ diversity_bonus = 0.021 / 0.089 = 0.24 (low priority)
├─ final_score = 0.60×0.762 + 0.20×0.04 + 0.15×0.24 + 0.05×0.75
│             = 0.457 + 0.008 + 0.036 + 0.038 = 0.539
└─ Ranking: #1 (Exploitation leader)

NC [2,1,2,3]:
├─ μ = 0.682, σ = 0.089 (high uncertainty)
├─ ucb = 0.682 + 1.5×√(2×log(T))×0.089 = 0.798
├─ domain_bonus = -0.01 (zone 2 tight, risky)
├─ diversity_bonus = 0.089 / 0.089 = 1.00 (explore!)
├─ final_score = 0.60×0.798 + 0.20×(-0.01) + 0.15×1.00 + 0.05×0.60
│             = 0.479 - 0.002 + 0.150 + 0.030 = 0.657
└─ Ranking: #2 (Exploration leader) ← High σ drives ranking up!
```

### Expected Outcome
- ✓ Principled BO-grounded reasoning
- ✓ Explicit exploration/exploitation balance
- ✓ Domain knowledge integration
- ✓ Full transparency (explain every choice)
- ✓ Potential for 5-10% improvement over baselines
- ✓ Robust: combines statistical + domain info
- ✗ More complex (harder to debug)
- ✗ Depends on GP kernel assumptions

### Results We'd Expect
- **Best overall selections** (0.74-0.80 productivity range)
- **Balanced portfolio** (2-3 exploitation + 2 exploration)
- **Discovered opportunities** (explores high-σ NCs strategically)
- **Better than Strategy 1 by 5-8%**
- **Better than Strategy 2 by 2-3%** (better exploration balance)

---

## Comparative Summary

| Feature | Strat 1 | Strat 2 | Strat 3 | Strat 4 |
|---------|---------|---------|---------|---------|
| **Method** | Heuristic | GP only | Heuristic + BO | BO + Domain |
| **Exploration** | None | Weak | Moderate | Strong |
| **Domain Knowledge** | Full | None | Full | Full |
| **Transparency** | High | Medium | High | Very High |
| **Statistical Rigor** | None | Full | None | Full |
| **Complexity** | Low | Medium | Medium | High |
| **Expected 1st Place** | 40% | 25% | 20% | 60% ← |
| **Expected Rank Avg** | 3.5 | 2.8 | 3.0 | 1.8 ← |

**Winner Prediction**: Strategy 4 should perform best due to BO-grounded reasoning + domain knowledge.

---

## How to Interpret Results

### If Strategy 1 Wins
→ Simple heuristics work well for SMB process
→ Suggests: Process relatively simple, no hidden opportunities

### If Strategy 2 Wins
→ Statistical patterns dominate
→ Suggests: BO-driven ML approach is optimal, domain knowledge adds noise

### If Strategy 3 Wins
→ Domain knowledge + balanced exploration works well
→ Suggests: Physics matters, heuristics capture relevant patterns
→ Note: Could be because GP assumptions invalid

### If Strategy 4 Wins (Expected)
→ BO-grounded reasoning + physics integration is optimal
→ Suggests: Both statistics and domain knowledge necessary
→ Interpretation: Intelligent combination of approaches best

---

## Implementation Notes

### For Strategy 4 Specifically

**Hyperparameter tuning**:
```python
β = sqrt(2 * log(T))  # BO standard, exploits more over time
domain_weight = 0.20  # Tune: 0.10-0.30 depending on domain trust
exploration_weight = 0.15  # Tune: 0.10-0.25 depending on budget
```

**Domain bonus calibration**:
```python
domain_bonus = (
  zone_balance_score(NC) * 0.05 +      # -0.05 to +0.05
  physical_intuition(NC) * 0.05 +      # -0.05 to +0.05
  feasibility_history(NC) * 0.03 +     # -0.02 to +0.03
  addresses_bottleneck(NC) * 0.07      # 0 or +0.07
)
```

**Agent reasoning generation**:
```python
for each selected NC:
  generate_explanation(
    statistical_justification=(μ, σ, acq),
    domain_justification=(zones, bottlenecks, intuition),
    exploration_rationale=(why this NC's uncertainty matters),
    expected_improvement=(realistic bounds)
  )
```

---

## Phase 3 Execution Plan

```
1. SETUP (Phase 2 outputs available)
   ├─ Load phase2_summary.json
   ├─ Prepare screening data (3200 points)
   └─ Verify data quality

2. PARALLEL EXECUTION (All 4 strategies)
   ├─ Strategy 1: Compute heuristic scores (~1 min)
   ├─ Strategy 2: Fit GP + predict (~5 min)
   ├─ Strategy 3: Agent analyzes LHS (~10 min)
   └─ Strategy 4: Agent+BO reasoning (~15 min)

3. SELECTION OUTPUT
   Each strategy produces:
   ├─ Top 5 selected NCs
   ├─ Ranking and scores
   ├─ Reasoning/explanations
   └─ Confidence assessment

4. HIGH-FIDELITY EVALUATION
   For each strategy's top 5:
   ├─ Run optimization at high fidelity (nfex=10, nfet=5)
   ├─ Compute true metrics
   └─ Track convergence

5. COMPARISON
   ├─ Compare best results across strategies
   ├─ Measure improvement vs Phase 2
   ├─ Analyze strategy effectiveness
   └─ Rank strategies

6. FINAL VALIDATION (Phase 4)
   └─ Re-evaluate top 5 from best strategy at strictest constraints
```

---

## What We're Testing

**Hypothesis**: Combining BO-grounded reasoning with domain knowledge (Strategy 4) yields better NC selection than any single approach.

**Success metrics**:
- Does Strategy 4 find best solution?
- Does Strategy 4 balance exploitation/exploration best?
- Do explanations align with actual results?
- Is transparency valuable for debugging?

**Scientific Value**:
- Demonstrates LLM agent effectiveness in optimization loops
- Validates BO + domain knowledge synergy
- Provides template for future process optimization

