# Strategy 4: Agent-Orchestrated Bayesian Optimization with Progressive Tools

## Philosophy
**"Start simple, upgrade tools when data justifies it"**

Agent starts with GP (fast, good with small data). After ~100 iterations accumulates enough data to justify:
- DNN surrogate (flexible nonlinear modeling)
- PINN surrogate (physics-informed constraints)

Agent then:
1. Tests new tool against GP baseline
2. Decides: keep using GP, or switch to DNN/PINN?
3. Refines LHS ranking as confidence grows
4. Adapts strategy based on which tool is most accurate

---

## Progressive Tool Adoption Architecture

```
PHASE 1: Iterations 1-50 (SMALL DATA - GP ONLY)
┌─────────────────────────────────────────────────────────────────┐
│ Agent uses GP (fast, good with few observations)                │
│                                                                 │
│ Step 1: Random initial evals (3-5 configs)                     │
│ Step 2: Fit GP to observations                                 │
│ Step 3: Compute Expected Improvement                           │
│ Step 4: Select next config (exploit uncertainty)               │
│ Step 5: IPOPT solve → J value                                  │
│ Step 6: Loop                                                    │
│                                                                 │
│ Agent decisions:                                                │
│ • EI vs UCB? → EI (maximize improvement)                       │
│ • Explore vs exploit? → Balanced (EI does this)                │
│ • Refine LHS ranking? → Not yet (data too sparse)             │
│                                                                 │
│ Result: ~40-50 observations accumulated                         │
└─────────────────────────────────────────────────────────────────┘
                           ↓
PHASE 2: Iteration 50 - DECISION POINT
┌─────────────────────────────────────────────────────────────────┐
│ Agent: "I have 50 observations. Should I try DNN/PINN now?"     │
│                                                                 │
│ Check conditions:                                               │
│ • Observation count: 50 (starting to be enough)                │
│ • GP accuracy plateau? (how well is GP predicting?)            │
│ • Convergence rate: (improvement slowing?)                     │
│ • Time remaining: (do we have 20+ more iterations?)            │
│                                                                 │
│ Decision Logic:                                                 │
│ IF n_obs < 100:                                                │
│     STAY with GP (safe, proven)                                │
│ ELSE IF n_obs >= 100 AND time_remaining > 20 iters:           │
│     TRY DNN (flexible for nonlinear patterns)                  │
│ ELSE IF n_obs >= 200 AND time_remaining > 15 iters:           │
│     TRY PINN (physics constraints matter)                      │
│                                                                 │
│ Action: Train candidate tool, TEST it                          │
└─────────────────────────────────────────────────────────────────┘
                           ↓
PHASE 2B: Iteration 100+ (MEDIUM DATA - TOOL EVALUATION)
┌─────────────────────────────────────────────────────────────────┐
│ Agent tests new tool (DNN or PINN)                              │
│                                                                 │
│ Test Procedure:                                                 │
│ 1. Train DNN on first 100 observations                         │
│ 2. Validate DNN on last 20 observations (hold-out test)       │
│ 3. Compare: DNN predictions vs actual J values                 │
│ 4. Compute: DNN prediction error vs GP error                  │
│                                                                 │
│ Agent Decision:                                                 │
│ IF dnn_error < gp_error + tolerance:                           │
│     "DNN is better! Let's switch."                            │
│     USE DNN for next decisions                                 │
│ ELSE:                                                           │
│     "GP is still better. Keep using GP."                       │
│     STAY with GP                                               │
│                                                                 │
│ Benefit: Only train DNN once we have enough data               │
│ Savings: Avoid training DNN on first 50 observations           │
└─────────────────────────────────────────────────────────────────┘
                           ↓
PHASE 3: Iteration 200+ (LARGE DATA - BEST TOOL)
┌─────────────────────────────────────────────────────────────────┐
│ Agent may try PINN if DNN didn't work out                       │
│                                                                 │
│ Same test-and-decide approach:                                  │
│ 1. Train PINN on 200 observations                             │
│ 2. Validate on hold-out test set                              │
│ 3. Check: Do PINN predictions respect physics?                │
│ 4. Compare accuracy vs current best tool                       │
│                                                                 │
│ Agent Decision:                                                 │
│ USE best-performing tool for final iterations                 │
│                                                                 │
│ Bonus: Agent now understands problem                           │
│ → Can refine LHS ranking with high confidence                 │
│ → Can explain why certain configs are best                    │
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

## Tool Use Patterns: Data-Driven Adoption

### Pattern 1: Progressive Threshold-Based Tool Introduction

**Agent decides WHEN to try new tools based on data accumulation:**

```python
def should_try_new_tool(n_observations, current_tool, time_remaining):
    """
    Decide if it's time to test a new surrogate model
    """
    
    # DNN threshold: at least 100 observations
    if current_tool == 'GP' and n_observations >= 100 and time_remaining > 20:
        return True, 'DNN'  # Try DNN, we have enough data
    
    # PINN threshold: at least 200 observations  
    if current_tool in ['GP', 'DNN'] and n_observations >= 200 and time_remaining > 15:
        return True, 'PINN'  # Try PINN, we have a lot of data
    
    return False, None

def test_new_tool(current_tool, candidate_tool, observations):
    """
    Test if new tool is better than current tool
    ONLY ONCE, when threshold is crossed
    """
    
    # Split data: train on first N, validate on last 20
    train_data = observations[:-20]
    test_data = observations[-20:]
    
    # Train candidate tool ONCE
    candidate = train_candidate_tool(train_data)
    
    # Compare accuracy
    current_error = evaluate_tool(current_tool, test_data)
    candidate_error = evaluate_tool(candidate_tool, test_data)
    
    # Agent decision
    if candidate_error < current_error * 1.1:  # Allow 10% tolerance
        agent_decision = agent_llm(
            f"New {candidate_tool} has error {candidate_error:.4f}, "
            f"current {current_tool} has {current_error:.4f}. "
            f"{candidate_tool} is {(current_error/candidate_error):.1%} better. "
            f"Should we switch?"
        )
        
        if agent_agrees:
            return candidate_tool  # Switch tools
    
    return current_tool  # Stick with current
```

### Pattern 2: Tool Validation (One-Time Decision)

**Agent tests each tool exactly ONCE when threshold reached:**

```python
class ProgressiveToolAdoption:
    def __init__(self):
        self.current_tool = 'GP'           # Always start with GP
        self.dnn_tested = False            # Track if we've tested DNN
        self.pinn_tested = False           # Track if we've tested PINN
        self.best_tool = 'GP'
    
    def decide_next_config(self, observations):
        n_obs = len(observations)
        
        # DECISION 1: Try DNN at 100 observations?
        if n_obs == 100 and not self.dnn_tested:
            self.best_tool = self.test_and_decide_dnn(observations)
            self.dnn_tested = True
        
        # DECISION 2: Try PINN at 200 observations?
        elif n_obs == 200 and not self.pinn_tested:
            self.best_tool = self.test_and_decide_pinn(observations)
            self.pinn_tested = True
        
        # Use best tool for prediction
        if self.best_tool == 'GP':
            return self.gp.predict_next_config(observations)
        elif self.best_tool == 'DNN':
            return self.dnn.predict_next_config(observations)
        else:
            return self.pinn.predict_next_config(observations)
```

### Pattern 3: LHS Ranking Refinement (Only After Learning)

**Agent refines LHS ranking only when it has learned enough:**

```python
def should_refine_lhs_ranking(n_observations, best_tool):
    """
    Only refine ranking when we have sufficient data AND a trusted model
    """
    # Need 100+ observations and a validated tool
    if n_observations < 100:
        return False, "Not enough data yet"
    
    if best_tool == 'GP':
        return True, "GP validated, can refine ranking"
    
    if n_observations >= 150 and best_tool in ['DNN', 'PINN']:
        return True, f"{best_tool} validated, can refine ranking"
    
    return False, "Waiting for better tool validation"

def refine_lhs_ranking(lhs_ranking, surrogate_predictions, best_tool):
    """
    Use best validated tool to refine initial physics ranking
    """
    
    correlation = np.corrcoef(lhs_ranking, surrogate_predictions)[0, 1]
    
    agent_decision = agent_llm(
        f"LHS physics ranking correlates {correlation:.3f} with "
        f"{best_tool} surrogate predictions. "
        f"Mismatch analysis: {analyze_mismatch(lhs_ranking, surrogate_predictions)}. "
        f"Should we: (a) trust LHS? (b) follow {best_tool}? (c) hybrid?"
    )
    
    if agent_decision == 'trust_lhs':
        return lhs_ranking  # Physics was right
    elif agent_decision == 'trust_surrogate':
        return surrogate_ranking  # Data says otherwise
    else:
        # Hybrid: weight both
        return 0.6 * lhs_ranking + 0.4 * surrogate_ranking
```

---

## Complete Progressive Tool Adoption Loop

```
EARLY PHASE (Iterations 1-100):
    ├─ Iteration 1-5: Random initial points
    │
    ├─ Iteration 6-100: Use GP Only
    │  ├─ Agent: "Fit GP to observations"
    │  ├─ Compute Expected Improvement
    │  ├─ Select config with highest EI
    │  └─ IPOPT solve → J value
    │
    └─ Iteration 100: DECISION POINT
       Agent: "I have 100 observations. Try DNN?"
       ├─ Train DNN on 100 obs (first time)
       ├─ Validate DNN on hold-out test set
       ├─ Compare: DNN accuracy vs GP accuracy
       └─ Decide: Switch to DNN or stay with GP?

MIDDLE PHASE (Iterations 101-200):
    ├─ If DNN won: Use DNN for EI computation
    │  ├─ DNN is more flexible (captures nonlinearity)
    │  ├─ Retrain DNN every 10 iterations with new data
    │  └─ IPOPT solve on DNN-suggested configs
    │
    ├─ If GP won: Continue with GP
    │  ├─ Agent may try PINN at iteration 200
    │  └─ Same test-and-decide procedure
    │
    └─ Agent learns: "Which tool is most accurate for this problem?"

LATE PHASE (Iterations 200+):
    ├─ Use best-proven tool
    │  (whatever won: GP, DNN, or PINN)
    │
    ├─ Agent now confident in its understanding
    │  ├─ Refine LHS ranking with high confidence
    │  ├─ Explain which NC families are best
    │  └─ Adjust exploration vs exploitation
    │
    └─ Final iterations: Exploit best region
       (or explore remaining unexplored configs if uncertainty high)

TOTAL: ~8-40 iterations in 11h budget
Tool cost: GP (~100 iterations), DNN (~100 iterations), PINN (~50 iterations)
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

## Advantages: Progressive Tool Adoption vs Fixed Tools

| Feature | Pure BO+GP | Pure BO+DNN | Pure BO+PINN | Agent-Progressive |
|---------|-----------|-----------|-------------|------------------|
| **Tool choice** | Fixed (GP) | Fixed (DNN) | Fixed (PINN) | ✅ Optimal per phase |
| **Training cost** | Low (fast) | High (slow) | Very high | ✅ Low (only when ready) |
| **Data efficiency** | Good (small) | Poor (needs >100 obs) | Poor (needs >200 obs) | ✅ Always adequate |
| **Reasoning** | ❌ Black-box | ❌ Black-box | ❌ Black-box | ✅ Agent explains |
| **Convergence** | Steady | Risky (overfitting <100) | Risky (insufficient data) | ✅ Safe then better |
| **LHS refinement** | ❌ Ignores | ❌ Ignores | ❌ Ignores | ✅ When confident |
| **Adaptivity** | Fixed | Fixed | Fixed | ✅ Tests → switches |
| **Complexity** | Low | Medium | High | **Medium** (adaptive) |
| **Wall-clock time** | Fast | Slowest | Slower | **Fast** (GP phase) then optimal |
| **Expected best J** | 50-60 | 52-62 | 54-64 | **55-65** (safer) |
| **Risk of failure** | Low | Medium (overfitting) | Medium (training) | **Very low** (fallback to GP) |

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

