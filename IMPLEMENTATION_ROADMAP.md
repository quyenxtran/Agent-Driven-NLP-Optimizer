# IMPLEMENTATION_ROADMAP.md

Archived roadmap note.

This file remains useful as design rationale, but it should be treated as **secondary historical planning material**, not the current canonical project plan.

## Current source of truth
- Read **`PLAN.md`** for the most up-to-date project plan.
- See `docs/ARCHITECTURE_AND_STATUS.md` for code/framing alignment.

## Why this file is archived
It describes an earlier roadmap for agent-enhanced BO integration under assumptions that may not match the current reconciled execution plan.

---

# Implementation Roadmap: Agent-Enhanced BO Loop for Phase 3

**Date**: April 5, 2026  
**Goal**: Implement LLM agent reasoning within Bayesian Optimization framework for intelligent NC selection

---

## Complete Picture: How Everything Fits Together

```
PHASE 2: LHS FOUNDATION
└─ Generate 100 LHS seeds per NC × 32 NCs = 3200 optimized points
└─ Data: NC configuration → optimal flow rates → metrics
└─ Output: phase2_summary.json

         ↓↓↓ TRANSITION ↓↓↓

PHASE 3: INTELLIGENT NC SELECTION (4 Parallel Strategies)
├─ All strategies read: phase2_summary.json + 3200 points
├─ All strategies reason about: which 5 NCs to refine
├─ All strategies serve as comparison/validation
└─ GOAL: Test if BO + Agent beats pure domain/statistics

STRATEGY 1: Heuristic Baseline
├─ Method: Score by (pu × re × pr) / variance
├─ Role: Control group (pure exploitation)
├─ Purpose: If we can't beat this, smarter methods don't help
└─ Agent: Minimal (just scoring)

STRATEGY 2: BO Baseline  
├─ Method: Fit GP, rank by μ + small·σ (weak exploration)
├─ Role: Show value of statistical modeling
├─ Purpose: Does GP generalization help?
└─ Agent: Minimal (just reading GP)

STRATEGY 3: Agent+LHS (BO-Inspired)
├─ Method: Agent analyzes LHS distribution + exploration potential
├─ Role: Show value of exploration reasoning
├─ Purpose: Can domain knowledge beat statistics?
├─ Agent: Full reasoning (interpret seed distribution)

STRATEGY 4: Agent+BO (Principled Synergy) ← EXPECTED WINNER
├─ Method: Agent computes UCB + domain bonus + diversity bonus
├─ Role: Show value of BO + domain integration
├─ Purpose: Can principled ensemble beat all?
├─ Agent: Full reasoning (acquisition function + domain knowledge)

         ↓↓↓ EVALUATION ↓↓↓

HIGH-FIDELITY OPTIMIZATION
└─ Each strategy's top 5 NCs evaluated at nfex=10, nfet=5, ncp=2
└─ Measure true performance (purity, recovery, productivity)
└─ Compare strategies

         ↓↓↓ RESULTS ↓↓↓

WINNER IDENTIFIED
└─ Which strategy picked the best NCs?
└─ Which had best portfolio balance?
└─ Which was most transparent?
```

---

## Agent's Journey Through BO Loop

### Step 1: Initialize from Phase 2 Data

```python
def agent_initialization():
    """Agent reads Phase 2 foundation."""
    
    # Load screening results
    screening_data = load_phase2_summary()  # 3200 points
    
    # Agent's first observation:
    agent_observation = """
    I have 3,200 optimized seed points across 32 NC layouts.
    Each NC has 100 seeds that were optimized at low fidelity.
    
    For each NC, I can see:
    - Success rate: % of seeds reaching feasibility
    - Performance range: best to worst productivity
    - Consistency: variance across seeds
    - Potential: if this NC could be better with fine-tuning
    
    My job: Use this data + physics intuition to rank 5 NCs
    for high-fidelity optimization.
    """
    return screening_data, agent_observation
```

### Step 2: Agent Analyzes Landscape

```python
def agent_landscape_analysis(screening_data):
    """Agent understands the terrain."""
    
    # For each NC
    analysis = {}
    for nc in all_ncs:
        seeds = screening_data[nc]
        
        # What does seed distribution tell us?
        exploration_status = {
            'success_rate': count_feasible(seeds) / 100,
            'variance': std(seeds),
            'best_found': max(seeds),
            'consistency': (max - min) / mean,
            'exploration_potential': variance / success_rate  # High = unexplored
        }
        
        # Agent's interpretation
        if success_rate > 0.8 and variance < 0.03:
            status = "EXPLOITED - Well understood, consistent"
        elif success_rate > 0.8 and variance > 0.07:
            status = "MULTIMODAL - Good but unstable, opportunity?"
        elif success_rate < 0.3 and variance > 0.05:
            status = "UNEXPLORED - Sparse sampling, hidden potential?"
        else:
            status = "DIFFICULT - Low success despite attempts"
        
        analysis[nc] = {
            'exploration_status': exploration_status,
            'agent_interpretation': status
        }
    
    return analysis
```

### Step 3: Strategy-Specific Reasoning

#### Strategy 4 (The Complete Loop)

```python
def agent_bo_reasoning(screening_data, gp_model, domain_knowledge):
    """
    Agent applies BO-grounded reasoning with domain knowledge.
    This is the full Bayesian Optimization loop with LLM guidance.
    """
    
    acquisition_scores = {}
    
    for nc in all_ncs:
        # PART A: Statistical (BO)
        mu = gp_model.predict_mean(nc)        # What's our best guess?
        sigma = gp_model.predict_std(nc)      # How uncertain?
        
        # UCB acquisition: optimistic estimate
        ucb = mu + sqrt(2 * log(iteration)) * sigma
        
        agent_ucb_reasoning = f"""
        NC {nc}:
        - Predicted performance (μ): {mu:.3f}
        - Confidence (σ): {sigma:.3f}
        - Optimistic estimate (UCB): {ucb:.3f}
        
        Interpretation: {interpret_ucb(mu, sigma)}
        """
        
        # PART B: Domain Knowledge
        domain_bonus = 0.0
        domain_reasoning = []
        
        if is_zone_balanced(nc):
            domain_bonus += 0.05
            domain_reasoning.append("✓ Zones balanced")
        else:
            domain_bonus -= 0.03
            domain_reasoning.append("✗ Zone imbalance detected")
        
        if aligns_with_physics(nc):
            domain_bonus += 0.05
            domain_reasoning.append("✓ Physically sound")
        else:
            domain_bonus -= 0.03
            domain_reasoning.append("✗ Conflicts with physics")
        
        if fixes_identified_bottleneck(nc):
            domain_bonus += 0.07
            domain_reasoning.append("✓ Addresses bottleneck")
        
        agent_domain_reasoning = f"""
        Domain Knowledge Assessment for NC {nc}:
        {chr(10).join(domain_reasoning)}
        Bonus adjustment: {domain_bonus:+.3f}
        """
        
        # PART C: Exploration Value
        exploration_value = sigma / max(all_sigmas)
        
        agent_exploration_reasoning = f"""
        Exploration Potential for NC {nc}:
        - Uncertainty relative to others: {exploration_value:.1%}
        - Information gain: {"HIGH" if exploration_value > 0.7 else "MODERATE" if exploration_value > 0.4 else "LOW"}
        - Justification: We've learned less about this NC
        """
        
        # PART D: Ensemble Score
        final_score = (
            0.60 * ucb +                    # Trust BO
            0.20 * (0.05 + domain_bonus) + # Domain knowledge
            0.15 * exploration_value +     # Exploration
            0.05 * baseline_heuristic(nc)  # Fallback
        )
        
        # FINAL REASONING
        if final_score > 0.50:
            tier = "STRONG"
        elif final_score > 0.40:
            tier = "MODERATE"
        else:
            tier = "WEAK"
        
        agent_final_recommendation = f"""
        RECOMMENDATION FOR NC {nc}:
        Tier: {tier}
        Final Score: {final_score:.3f}
        
        REASONING BREAKDOWN:
        1. Statistical Model (60% weight): {ucb:.3f}
           {agent_ucb_reasoning}
        
        2. Domain Knowledge (20% weight): {domain_bonus:+.3f}
           {agent_domain_reasoning}
        
        3. Exploration Value (15% weight): {exploration_value:.1%}
           {agent_exploration_reasoning}
        
        DECISION: {'PRIORITIZE' if final_score > 0.45 else 'DEFER'}
        """
        
        acquisition_scores[nc] = {
            'final_score': final_score,
            'components': {
                'ucb': ucb,
                'domain_bonus': domain_bonus,
                'exploration_value': exploration_value
            },
            'reasoning': agent_final_recommendation
        }
    
    # PORTFOLIO SELECTION
    ranked = sorted(acquisition_scores.items(), key=lambda x: x[1]['final_score'], reverse=True)
    
    top_5 = []
    exploit_count = 0
    explore_count = 0
    
    for rank, (nc, scores) in enumerate(ranked[:10]):  # Consider top 10
        sigma = scores['components']['ucb'] - scores['components']['ucb'] / 1.5  # Approximate
        
        if sigma < np.percentile(all_sigmas, 40) and exploit_count < 3:
            # Exploitation candidate
            top_5.append(nc)
            exploit_count += 1
        elif sigma > np.percentile(all_sigmas, 60) and explore_count < 2 and scores['final_score'] > 0.35:
            # Exploration candidate
            top_5.append(nc)
            explore_count += 1
        
        if len(top_5) == 5:
            break
    
    return top_5, acquisition_scores
```

### Step 4: Agent Generates Explanation

```python
def agent_generate_explanation(selected_ncs, acquisition_scores):
    """
    Agent writes narrative explaining selections.
    This is key for trust and interpretability.
    """
    
    explanation = """
    ╔════════════════════════════════════════════════════════════╗
    ║   PHASE 3 NC SELECTION: BAYESIAN OPTIMIZATION + REASONING  ║
    ╚════════════════════════════════════════════════════════════╝
    
    I analyzed 3,200 optimized seed points across 32 NC layouts
    using three reasoning mechanisms:
    
    1. STATISTICAL MODEL (Gaussian Process)
       - Fitted to all screening data
       - Kernel: Matérn(ν=2.5) for robustness
       - Provides: predicted performance (μ) + uncertainty (σ)
    
    2. BAYESIAN OPTIMIZATION LOGIC (UCB Acquisition)
       - Formula: μ(NC) + √(2·log(T))·σ(NC)
       - Interpretation: Optimistic performance estimate
       - Effect: Balances exploitation (high μ) vs exploration (high σ)
    
    3. DOMAIN KNOWLEDGE (Physics Intuition)
       - Zone balance assessment
       - Bottleneck identification
       - Feasibility history
       - Integration weight: 20% of final score
    
    ═══════════════════════════════════════════════════════════════
    
    TOP 5 SELECTIONS FOR HIGH-FIDELITY OPTIMIZATION:
    """
    
    for rank, nc in enumerate(selected_ncs, 1):
        scores = acquisition_scores[nc]
        reasoning = scores['reasoning']
        
        explanation += f"""
    {rank}. NC {nc}
    {'-' * 40}
    {reasoning}
    """
    
    explanation += """
    ═══════════════════════════════════════════════════════════════
    
    PORTFOLIO BALANCE:
    - Exploitation (safe, well-understood): 2-3 NCs
    - Exploration (potential, uncertain): 2 NCs
    
    Rationale: Remaining budget allows both refinement and discovery.
    BO theory suggests this 60/40 split for informed exploration.
    
    NEXT STEPS:
    1. Evaluate these 5 NCs at high fidelity (nfex=10, nfet=5)
    2. Compare with other strategies' selections
    3. Analyze which strategy found the best NC
    4. Validate BO reasoning against reality
    
    Confidence: Medium-High
    (Based on 3200 seed points and domain knowledge)
    """
    
    return explanation
```

### Step 5: Agent Learns & Reflects

```python
def agent_postanalysis(actual_results, predicted_results):
    """
    After high-fidelity evaluation, agent reflects on accuracy.
    """
    
    reflection = """
    POST-ANALYSIS: How Well Did BO Reasoning Work?
    
    PREDICTIONS vs REALITY:
    """
    
    for nc, (predicted_mu, actual_perf) in zip(selected_ncs, actual_results):
        error = actual_perf - predicted_mu
        
        if abs(error) < 0.02:
            accuracy = "✓ EXCELLENT prediction"
        elif abs(error) < 0.05:
            accuracy = "✓ GOOD prediction"
        elif abs(error) < 0.10:
            accuracy = "⚠ MODERATE error"
        else:
            accuracy = "✗ POOR prediction"
        
        reflection += f"""
        NC {nc}: Predicted {predicted_mu:.3f}, Actual {actual_perf:.3f}
        Error: {error:+.3f} {accuracy}
        """
    
    reflection += """
    
    INSIGHTS:
    - Which assumptions held up?
    - Where did BO reasoning fail?
    - What should be adjusted next time?
    - How well did domain knowledge help?
    """
    
    return reflection
```

---

## Code Implementation Structure

### Phase 3 Strategy 4 (Agent+BO)

**File**: `benchmarks/phase3_strategy4_agent_bo_v2.py`

```python
"""
Phase 3 Strategy 4: Agent+BO
Bayesian Optimization with LLM Reasoning Agent
"""

import json
import numpy as np
from pathlib import Path
from sembasmb import SMBConfig

class BayesianOptimizationAgent:
    """LLM agent applying BO-grounded reasoning."""
    
    def __init__(self, phase2_data, gp_model, domain_knowledge_base):
        self.data = phase2_data
        self.gp = gp_model
        self.domain_kb = domain_knowledge_base
        self.reasoning_log = []
    
    def analyze_landscape(self):
        """Step 1: Understand Phase 2 data."""
        # Implementation of step 2 above
        pass
    
    def compute_acquisition_function(self, nc):
        """
        Step 3A: Compute UCB acquisition score.
        
        UCB(NC) = μ(NC) + √(2·log(T))·σ(NC)
        """
        mu = self.gp.predict_mean(nc)
        sigma = self.gp.predict_std(nc)
        beta = np.sqrt(2 * np.log(self.iteration))
        
        return mu + beta * sigma
    
    def compute_domain_bonus(self, nc):
        """Step 3B: Quantify domain knowledge contribution."""
        bonus = 0.0
        
        # Zone balance
        if self.is_zone_balanced(nc):
            bonus += 0.05
        else:
            bonus -= 0.03
        
        # Physics alignment
        if self.aligns_with_physics(nc):
            bonus += 0.05
        else:
            bonus -= 0.03
        
        # Bottleneck addressing
        if self.fixes_bottleneck(nc):
            bonus += 0.07
        
        return bonus
    
    def compute_exploration_value(self, nc, all_sigmas):
        """Step 3C: Value of reducing uncertainty."""
        sigma = self.gp.predict_std(nc)
        return sigma / (np.max(all_sigmas) + 1e-10)
    
    def compute_final_score(self, nc, all_sigmas):
        """
        Step 3D: Principled ensemble score.
        
        final = 0.60·UCB + 0.20·domain + 0.15·exploration + 0.05·baseline
        """
        ucb = self.compute_acquisition_function(nc)
        domain = self.compute_domain_bonus(nc)
        exploration = self.compute_exploration_value(nc, all_sigmas)
        baseline = self.heuristic_score(nc)
        
        final = (
            0.60 * ucb +
            0.20 * (0.05 + domain) +  # 0.05 is baseline domain
            0.15 * exploration +
            0.05 * baseline
        )
        
        return final, {'ucb': ucb, 'domain': domain, 'exploration': exploration}
    
    def select_portfolio(self, top_k=10):
        """
        Step 4: Select 5 NCs balancing exploitation/exploration.
        """
        scores = {}
        all_sigmas = [self.gp.predict_std(nc) for nc in all_ncs]
        
        for nc in all_ncs:
            final, components = self.compute_final_score(nc, all_sigmas)
            scores[nc] = {'final': final, 'components': components}
        
        ranked = sorted(scores.items(), key=lambda x: x[1]['final'], reverse=True)
        
        # Portfolio selection
        selected = []
        exploit_count = 0
        explore_count = 0
        
        for nc, score_data in ranked[:top_k]:
            sigma = score_data['components']['exploration']
            
            if sigma < 0.4 and exploit_count < 3:
                selected.append(nc)
                exploit_count += 1
            elif sigma > 0.6 and explore_count < 2 and score_data['final'] > 0.35:
                selected.append(nc)
                explore_count += 1
            
            if len(selected) == 5:
                break
        
        return selected, scores
    
    def generate_explanation(self, selected_ncs, scores):
        """Step 5: Generate narrative explanation."""
        # Implementation of step 4 above
        pass

def run_strategy_4():
    """
    Main execution: Strategy 4 (Agent+BO)
    """
    # Load Phase 2 data
    phase2_data = load_phase2_summary()
    
    # Fit GP
    gp = fit_gaussian_process(
        phase2_data,
        kernel='matern',
        nu=2.5,
        optimize_hyperparameters=True
    )
    
    # Load domain knowledge
    domain_kb = load_domain_knowledge()
    
    # Create agent
    agent = BayesianOptimizationAgent(phase2_data, gp, domain_kb)
    
    # Run reasoning loop
    agent.analyze_landscape()
    selected_ncs, scores = agent.select_portfolio()
    explanation = agent.generate_explanation(selected_ncs, scores)
    
    # Output results
    results = {
        'strategy': 'strategy_4_agent_bo',
        'selected_ncs': selected_ncs,
        'scores': scores,
        'explanation': explanation,
        'metadata': {
            'gp_kernel': 'matern_2.5',
            'acq_function': 'ucb',
            'ensemble_weights': {
                'statistical': 0.60,
                'domain': 0.20,
                'exploration': 0.15,
                'baseline': 0.05
            }
        }
    }
    
    return results
```

---

## Validation Checklist

- [ ] Phase 2 data loads correctly (3200 seed points)
- [ ] GP fits with Matérn(2.5) kernel
- [ ] Hyperparameters optimize via marginal likelihood
- [ ] UCB acquisition function computes correctly
- [ ] Domain bonus calculation follows formula
- [ ] Exploration value (σ relative) calculated
- [ ] Final ensemble score weights to 1.0
- [ ] Portfolio balance (2-3 exploit + 2 explore)
- [ ] Agent generates explanation for each NC
- [ ] All 4 strategies run in parallel
- [ ] High-fidelity evaluation compares strategies
- [ ] Results logged and compared

---

## Expected Outcomes

### Best Case (Strategy 4 Wins)
```
✓ BO + Domain Knowledge is superior
✓ LLM agent effectively combines approaches
✓ 5-10% improvement over Strategy 1 baseline
✓ Agent explanations are insightful
✓ Validation shows exploration was valuable
```

### Learning Scenarios
```
If Strategy 1 wins: Domain heuristics are sufficient
If Strategy 2 wins: Statistical learning dominates
If Strategy 3 wins: Exploration more valuable than BO
If Strategy 4 wins: Synergy between BO + domain (EXPECTED)
```

### Next Steps Based on Results
```
Strategy 4 Wins:
→ Use Strategy 4 for Phase 4 validation
→ Validate best NC at strictest constraints
→ Consider BO as standard for future work

Any strategy underperforms:
→ Debug: Review selection reasoning
→ Analyze: What did we miss?
→ Iterate: Refine weights, assumptions
```

---

## Summary: Agent in BO Loop

| Phase | Agent Role | BO Component | Output |
|-------|-----------|--------------|--------|
| Initialize | Read data | - | Understanding landscape |
| Analyze | Interpret distribution | LHS perspective | Exploration potential |
| Acquire | Reason about tradeoffs | UCB + domain + diversity | Acquisition function |
| Select | Choose portfolio | Balanced exploitation/exploration | Top 5 NCs |
| Explain | Justify decisions | All three components | Transparent reasoning |
| Evaluate | Learn from results | Compare to predictions | Reflection |

**Key Insight**: The agent doesn't replace BO—it **enhances** it with reasoning, explanation, and domain knowledge, making it both smarter AND interpretable.

