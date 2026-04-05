# Strategy 4: Agent-Orchestrated Bayesian Optimization with Tool Use

## Philosophy
**"LLM agent as intelligent orchestrator of computational tools"**

Give the agent access to surrogate model tools (GP, DNN, PINN) and Bayesian optimization machinery. The agent:
1. Decides which tool to use (refine LHS ranking, fit surrogate, compute acquisition)
2. Interprets surrogate predictions (what does the model think?)
3. Combines mathematical insights with domain knowledge
4. Refines the search strategy adaptively

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ AGENT-ORCHESTRATED BO FRAMEWORK                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  LLM Agent (Scientist_A)                                        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ "I have observations. Let me use tools to decide next."  │  │
│  │                                                          │  │
│  │ Available Tools:                                         │  │
│  │ • fit_gp_surrogate(observations) → model                │  │
│  │ • fit_dnn_surrogate(observations) → model               │  │
│  │ • fit_pinn_surrogate(observations) → model              │  │
│  │ • predict_j(model, config) → [mean, uncertainty]        │  │
│  │ • compute_expected_improvement(predictions) → ei_scores │  │
│  │ • refine_lhs_ranking(predictions) → new_ranking         │  │
│  │ • suggest_exploration_point() → config                  │  │
│  │ • suggest_exploitation_point() → config                 │  │
│  │                                                          │  │
│  │ Decision Logic:                                          │  │
│  │ 1. Check convergence (improvement rate slowing?)        │  │
│  │ 2. Fit best surrogate (GP vs DNN vs PINN)              │  │
│  │ 3. Analyze predictions (where are the optimum?)        │  │
│  │ 4. Compute acquisition scores (EI, UCB)                │  │
│  │ 5. Refine LHS ranking based on surrogate               │  │
│  │ 6. Decide: explore new region or exploit current best? │  │
│  │ 7. Output: next config to evaluate + reasoning          │  │
│  └──────────────────────────────────────────────────────────┘  │
│            ↓              ↓              ↓                      │
│  ┌────────────────┬──────────────┬──────────────────┐           │
│  │ TOOL: GP       │ TOOL: DNN    │ TOOL: PINN       │           │
│  │ Surrogate      │ Surrogate    │ Surrogate        │           │
│  ├────────────────┼──────────────┼──────────────────┤           │
│  │ ✅ Fast       │ ✅ Flexible  │ ✅ Physics-aware │           │
│  │ ✅ Uncertain  │ ✅ Scales    │ ✅ Constraints   │           │
│  │ ❌ Limited    │ ❌ Black-box │ ❌ Training time │           │
│  │    data       │              │                  │           │
│  └────────────────┴──────────────┴──────────────────┘           │
│            ↓              ↓              ↓                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ IPOPT Solver                                             │  │
│  │ (Agent-chosen config) → J value                          │  │
│  └──────────────────────────────────────────────────────────┘  │
│            ↓                                                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Learning Loop                                            │  │
│  │ • Update observation history                             │  │
│  │ • Refit surrogate models                                │  │
│  │ • Agent learns: "which tool was most accurate?"         │  │
│  │ • Adapt tool selection strategy                          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Three Tool Variants

### Tool 1: Agent-GP (Gaussian Process Orchestrated)

**Agent decides:**
- When to refit the GP (every iteration? every 3?)
- Which acquisition function (EI, UCB, LCB)
- Lengthscale parameter (explore vs exploit)
- How to interpret uncertainty

**Implementation:**
```python
class AgentGP:
    def __init__(self):
        self.gp = SimpleGPMean(lengthscale=2.0)
        self.observations = []
    
    def fit(self, obs):
        self.gp.fit(obs['configs'], obs['J_values'])
    
    def agent_decides_next(self, history, agent_reasoning):
        # Agent proposes:
        mean, std = self.gp.predict(all_configs)
        ei_scores = compute_ei(mean, std, max(obs['J_values']))
        
        # Agent reasoning: "Uncertainty is high in region X.
        # EI is highest for config Y. Should I explore or exploit?"
        
        agent_decision = agent_llm(
            f"GP says: best region is {np.argmax(mean)}, "
            f"most uncertain: {np.argmax(std)}, "
            f"highest EI: {np.argmax(ei_scores)}. "
            f"History shows: {convergence_pattern}. "
            f"What should we try next?"
        )
        
        return agent_decision['next_config']
```

**Strengths:**
- Fast surrogate fitting
- Uncertainty quantification (agent knows what it's unsure about)
- Agent explains its reasoning (EI vs uncertainty vs mean)

**Weaknesses:**
- Limited by GP expressiveness
- Struggles with high-D continuous space
- Kernel choice matters

---

### Tool 2: Agent-DNN (Deep Neural Network Orchestrated)

**Agent decides:**
- Network architecture (how many layers, neurons)
- Training procedure (when to stop, regularization)
- Feature engineering (which transformations of configs)
- Confidence intervals (how to estimate uncertainty from NN)

**Implementation:**
```python
class AgentDNN:
    def __init__(self):
        self.dnn = DNNSurrogate(layers=[32, 64, 32], dropout=0.1)
        self.observations = []
    
    def agent_decides_architecture(self, n_observations, problem_complexity):
        # Agent reasoning: "We have N observations. 
        # The space seems complex (high variance). 
        # Should we use big network or small network?"
        
        agent_decision = agent_llm(
            f"We have {n_observations} observations. "
            f"Variance in J is {np.std(J_values):.2f}. "
            f"NC structure suggests {problem_complexity}. "
            f"What DNN architecture? Layers? Dropout?"
        )
        
        arch = parse_architecture(agent_decision['architecture'])
        return arch
    
    def agent_decides_next(self, history):
        # Fit DNN
        self.dnn.train(configs, J_values)
        
        # Get predictions with uncertainty (MC dropout)
        mean, std = self.dnn.predict_with_uncertainty(all_configs)
        
        # Agent interprets
        agent_decision = agent_llm(
            f"DNN predictions: best={mean[np.argmax(mean)]:.2f}, "
            f"most uncertain config={np.argmax(std)}, "
            f"training loss={self.dnn.loss:.4f}. "
            f"Is DNN confident? Should we trust it or explore blindly?"
        )
        
        return agent_decision['next_config']
```

**Strengths:**
- Flexible nonlinear modeling
- Can capture complex interactions
- Scales to larger datasets
- MC dropout gives uncertainty estimates

**Weaknesses:**
- Needs more data to train well
- Hyperparameter tuning (agent must decide)
- Risk of overfitting with small datasets
- Black-box (hard to interpret why NN says what)

---

### Tool 3: Agent-PINN (Physics-Informed Neural Network Orchestrated)

**Agent decides:**
- Physics constraints to encode (SMB flow balance, purity/recovery)
- Physics loss weight vs data loss weight
- Which differential equations matter
- When to update constraint strength

**Implementation:**
```python
class AgentPINN:
    def __init__(self):
        self.pinn = PINN(
            network_size=[32, 64, 32],
            physics_constraints=['mass_balance', 'purity_constraint'],
            physics_weight=0.5  # Agent can adjust this
        )
        self.observations = []
    
    def agent_decides_physics_weight(self, history):
        # Agent reasoning: "DNN predictions violate physics sometimes.
        # Should we enforce physics harder, or trust data?"
        
        violations = count_constraint_violations(history)
        
        agent_decision = agent_llm(
            f"We observed {violations} constraint violations. "
            f"Convergence rate is {convergence_rate:.3f}. "
            f"Should PINN enforce physics harder (weight=0.8) "
            f"or trust data more (weight=0.3)?"
        )
        
        new_weight = parse_weight(agent_decision['physics_weight'])
        self.pinn.set_physics_weight(new_weight)
    
    def agent_decides_next(self, history):
        # Fit PINN with physics constraints
        self.pinn.train(configs, J_values, constraint_violations)
        
        # PINN respects physics while fitting data
        mean, std = self.pinn.predict(all_configs)
        
        # Check if predictions respect constraints
        physics_violations = self.pinn.check_constraints(mean)
        
        agent_decision = agent_llm(
            f"PINN predictions respect physics: {100-physics_violations:.1f}%. "
            f"Best config by PINN: {np.argmax(mean)}. "
            f"Physics-respecting regions: {np.where(physics_violations < 5)}. "
            f"Should we explore physics-respecting region or push boundaries?"
        )
        
        return agent_decision['next_config']
```

**Strengths:**
- Enforces known physics constraints
- More sample-efficient (physics regularization)
- Predictions guaranteed feasible (mass balance, purity bounds)
- Agent can reason about constraint tradeoffs

**Weaknesses:**
- Requires hand-crafted physics constraints
- Training more complex (multi-loss optimization)
- Constraints might be overly restrictive
- Not all physics is easy to encode

---

## Tool Use Patterns

### Pattern 1: Tool Selection Strategy

**Agent decides which tool to use based on:**

```python
def agent_chooses_tool(history, observations):
    # Analyze data quality
    data_quality = {
        'n_observations': len(observations),
        'data_variance': np.std([o['J'] for o in observations]),
        'outliers': detect_outliers(observations),
        'noise_level': estimate_noise(observations),
    }
    
    # Analyze search progress
    convergence = {
        'improvement_rate': (best_J_now - best_J_prev) / time_elapsed,
        'exploration_coverage': n_unique_configs / 31,
        'constraint_violations': count_violations(observations),
    }
    
    # Agent decides
    decision = agent_llm(
        f"Data: {data_quality}. Progress: {convergence}. "
        f"Should we use GP (fast, uncertain), DNN (flexible, risky), "
        f"or PINN (physics-aware, constrained)? Why?"
    )
    
    selected_tool = decision['selected_tool']  # 'GP', 'DNN', or 'PINN'
    return selected_tool, decision['reasoning']
```

### Pattern 2: Ensemble Approach

**Agent uses multiple tools and combines:**

```python
def agent_ensemble_decision(history, observations):
    # Train all three tools
    gp = train_gp(observations)
    dnn = train_dnn(observations)
    pinn = train_pinn(observations)
    
    # Get predictions from all
    gp_pred = gp.predict(all_configs)
    dnn_pred = dnn.predict(all_configs)
    pinn_pred = pinn.predict(all_configs)
    
    # Agent reasons about disagreement
    disagreement = measure_disagreement(gp_pred, dnn_pred, pinn_pred)
    
    decision = agent_llm(
        f"Three models disagree on best config: "
        f"GP says {gp_best}, DNN says {dnn_best}, PINN says {pinn_best}. "
        f"Disagreement pattern: {disagreement_analysis}. "
        f"High disagreement means high uncertainty. "
        f"Should we: (a) trust majority? (b) explore disagreement region? "
        f"(c) run one more eval to disambiguate?"
    )
    
    return decision['next_config']
```

### Pattern 3: LHS Ranking Refinement

**Agent refines LHS physics ranking using surrogate insights:**

```python
def agent_refines_lhs_ranking(initial_lhs_ranking, surrogate_predictions):
    # Initial ranking: pure physics heuristics
    # Surrogate predicts: actual J values based on data
    
    # Compare
    correlation = np.corrcoef(lhs_rank_scores, surrogate_predictions)[0, 1]
    
    agent_decision = agent_llm(
        f"LHS physics ranking correlates {correlation:.3f} with "
        f"surrogate predictions. Mismatch: {rank_mismatches}. "
        f"Physics might be {['correct', 'partially correct', 'wrong'][???]}. "
        f"Should we: (a) trust LHS? (b) follow surrogate? "
        f"(c) hybrid (weight both)? Why?"
    )
    
    refined_ranking = combine_rankings(
        lhs_ranking, 
        surrogate_ranking,
        weights=agent_decision['weights']
    )
    
    return refined_ranking
```

---

## Complete Agent-BO Loop

```
Iteration 1-3: Random Initial Points (establish baseline)
    ↓
Agent: "Let me fit surrogate models and understand the landscape"
    ├─ fit_gp_surrogate()
    ├─ fit_dnn_surrogate()
    └─ fit_pinn_surrogate()
    ↓
Agent: "All three agree that region X is promising, region Y is poor"
    ├─ compute_expected_improvement()
    ├─ compute_uncertainty()
    └─ refine_lhs_ranking()
    ↓
Agent: "I should explore the disagreement region (DNN vs PINN) 
         because high uncertainty = potential discovery"
    ↓
Select next config based on agent reasoning
    ↓
Run IPOPT → get J value
    ↓
Update history, loop
    ↓
Iteration N: "Improvement rate slowing. Should we refine or restart?"
    ├─ Agent analyzes convergence
    ├─ Retrain surrogates
    └─ Decide: exploit current best or explore elsewhere
    ↓
Repeat until time budget exhausted
```

---

## Agent Reasoning Examples

### Example 1: Tool Selection

```
Agent: "I have 8 observations. Variance is high (std=8.5). 
         LHS ranking said [1,1,2,4] would be best, 
         but actual top performer is [2,2,2,2]. 
         
         Should I use:
         (a) GP: Fast, but might overfit with 8 points?
         (b) DNN: Flexible, but needs more data?
         (c) PINN: Enforces physics, helps with small data?
         
         Decision: Use PINN because:
         - Small sample size (PINN is data-efficient due to physics prior)
         - Physics constraints prevent wild overfitting
         - Top performer [2,2,2,2] is balanced (physically sensible)
         - PINN will enforce this pattern"
```

### Example 2: Disagreement Resolution

```
Agent: "Models predict differently:
         GP: Best is [1,1,3,3] (uncertainty=1.2)
         DNN: Best is [2,2,2,2] (uncertainty=0.8)
         PINN: Best is [1,2,3,2] (uncertainty=0.6)
         
         High disagreement (range=1.7) means deep uncertainty.
         
         Decision: Explore disagreement region [1,2,2,3] 
         because:
         - If I'm right, I find better config
         - If I'm wrong, I disambiguate models (train better next)
         - Disagreement is information"
```

### Example 3: Convergence Assessment

```
Agent: "Last 5 evaluations improved by: [+2.1, +0.5, +0.1, +0.0, -0.3]
         Improvement rate: 0.08 per iteration (declining)
         We're at iteration 20 of 40 (halfway)
         
         Convergence Analysis:
         - Exploitation is saturating (improvements < noise)
         - Unexplored configs: 12/31 (39% remain)
         - High-uncertainty regions: 3 clusters
         
         Decision: Restart aggressive exploration
         - Use ensemble disagreement to find high-uncertainty regions
         - Skip nearby configs (already evaluated)
         - Target regions where models disagree most"
```

---

## Advantages vs Pure BO+GP / BO+DNN / BO+PINN

| Feature | Pure BO+GP | Pure BO+DNN | Pure BO+PINN | Agent-Orchestrated |
|---------|-----------|-----------|-------------|------------------|
| **Tool adaptivity** | Fixed (GP only) | Fixed (DNN only) | Fixed (PINN only) | ✅ Chooses best tool |
| **Uncertainty-aware** | ✅ Natural | ⚠️ MC dropout | ✅ PINN uncertainty | ✅ All three + meta |
| **Reasoning** | ❌ Black-box | ❌ Black-box | ❌ Black-box | ✅ Agent explains |
| **Physics enforcement** | ❌ | ❌ | ✅ | ✅ Via PINN tool |
| **Ensemble** | ❌ | ❌ | ❌ | ✅ Ensemble method |
| **Adaptive strategy** | ❌ Fixed EI | ❌ Fixed loss | ❌ Fixed losses | ✅ Agent adjusts |
| **LHS refinement** | ❌ Ignores | ❌ Ignores | ❌ Ignores | ✅ Refines ranking |
| **Complexity** | Low | Medium | High | **Very High** |
| **Expected best J** | 50-60 | 52-62 | 54-64 | **56-66** |

---

## Implementation Requirements

### Core Modules Needed

```python
# New tools for agent
class GPSurrogate:
    def fit(self, configs, J_values)
    def predict(self, configs) -> (mean, std)
    def compute_ei(self, configs) -> scores

class DNNSurrogate:
    def fit(self, configs, J_values, architecture)
    def predict(self, configs) -> (mean, std)
    def compute_uncertainty(self) -> std

class PINNSurrogate:
    def fit(self, configs, J_values, physics_constraints, weight)
    def predict(self, configs) -> (mean, std)
    def check_feasibility(self, configs) -> bool_array

class AgentToolKit:
    def fit_gp(self, observations) -> tool
    def fit_dnn(self, observations) -> tool
    def fit_pinn(self, observations) -> tool
    def refine_lhs_ranking(self, lhs_scores, surrogate_preds) -> refined
    def compute_ensemble_disagreement(self, all_predictions) -> disagreement
```

### Agent Prompts

```python
# Tool selection prompt
TOOL_SELECTION_PROMPT = """
You have 3 surrogate models available:
- GP: Fast, good uncertainty, limited expressiveness
- DNN: Flexible, needs data, risk of overfitting
- PINN: Physics-aware, data-efficient, constrained

Current observations: {observations}
Data characteristics: {data_stats}
Progress so far: {convergence_stats}

Which tool should we use and why?
Respond: {"selected_tool": "GP|DNN|PINN", "reasoning": "..."}
"""

# LHS refinement prompt
LHS_REFINEMENT_PROMPT = """
Initial physics-based LHS ranking says configs are good in this order:
{lhs_ranking}

But surrogate model (trained on actual evaluations) predicts this order:
{surrogate_ranking}

Correlation: {correlation:.3f}
Disagreement: {disagreements}

Should we:
(a) Trust LHS (physics > empirics)
(b) Trust surrogate (empirics > physics)
(c) Hybrid (weight both)

Respond with refined ranking and rationale.
"""
```

---

## Comparison to Pure Strategies

### LHS+Agent vs Agent-Orchestrated BO

| Aspect | LHS+Agent | Agent-Orchestrated BO |
|--------|-----------|----------------------|
| **Initial info** | Physics ranking | None (learns from scratch) |
| **Decision basis** | Agent intuition | Agent + 3 surrogate models |
| **Tool ensemble** | No | Yes (GP+DNN+PINN) |
| **Uncertainty awareness** | Implicit | Explicit (3 models) |
| **Adaptivity** | Good (agent learns) | Excellent (tools + agent) |
| **Complexity** | High | **Very high** |
| **Expected best J** | 55-65 | **56-66** |

### Agent-Orchestrated BO vs Pure BO+GP/DNN/PINN

| Aspect | Pure BO+GP | Agent-Orchestrated |
|--------|-----------|-------------------|
| **Flexibility** | Fixed method | Chooses best method |
| **Reasoning** | None | Full agent reasoning |
| **Ensemble** | No | Yes (all 3) |
| **LHS integration** | Ignores | Refines ranking |
| **Failure modes** | GP limitation | Can switch tools |
| **Interpretability** | Black-box | Explainable (agent) |

---

## Risk Assessment

### High-Risk Aspects

⚠️ **Complexity**: Integrating 3 surrogate models + agent reasoning
⚠️ **Agent burden**: Agent must understand 3 different tools
⚠️ **Training cost**: Fitting DNN + PINN adds wall-clock time
⚠️ **Failure modes**: If agent makes wrong tool choice, wastes iterations

### Mitigation Strategies

✅ **Fallback**: If agent fails, default to best-performing tool
✅ **Validation**: Cross-validate tool predictions against actual evals
✅ **Monitoring**: Track which tool is most accurate over time
✅ **Simplification**: Start with GP+agent, add DNN/PINN later

---

## When to Use Agent-Orchestrated BO

### ✅ Use if:
- You have 11+ hours (time for tool training)
- Agent reasoning is valuable (interpretability needed)
- You want maximum performance (best of all approaches)
- You can afford higher complexity
- You want to learn which tool works best

### ❌ Avoid if:
- Time budget is tight (<4 hours)
- You need guaranteed determinism (agent adds randomness)
- You want simplicity (too many moving parts)
- You don't trust LLM reasoning
- You want to understand exactly what happened

---

## Proposed Implementation Timeline

```
Week 1: Basic scaffolding
  - GPSurrogate class
  - AgentToolKit interface
  - Tool selection prompt

Week 2: Agent integration
  - Agent learns to call tools
  - Tool selection logic
  - Ensemble disagreement detection

Week 3: Advanced features
  - LHS ranking refinement
  - Convergence-based tool switching
  - Ensemble prediction combination

Week 4: Testing & optimization
  - Smoke tests (15 min runs)
  - Medium fidelity (4h runs)
  - Benchmark vs pure strategies
```

---

## Expected Outcome

**If successful**: Agent-Orchestrated BO achieves **best J = 60-70** (vs 50-65 for baselines)

**Why?**
- Learns from data (BO aspect)
- Uses domain knowledge (physics initial + LHS refinement)
- Adapts strategy (agent tool selection)
- Ensemble redundancy (catches mistakes)
- Hybrid confidence (knows what to trust)

**Learning curve**: Better convergence with experience (agent improves tool usage)

