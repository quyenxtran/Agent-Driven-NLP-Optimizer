# Phase 3 NC Selection Strategies: Publication-Ready Methodology

## 1. Common Foundation (Phase 2)

All three strategies operate on identical Phase 2 data:
- **32 NC configurations**: Four-tuples (n₁, n₂, n₃, n₄) summing to 8 columns
- **3,200 optimized points**: 100 Latin Hypercube samples per NC
- **Discretization**: nfex=4, nfet=2, ncp=1 (low-fidelity)
- **Metrics per seed**: Productivity (J), purity, recovery (GA/MA)
- **Constraints**: Purity ≥ 0.15, recovery ≥ 0.15 (relaxed for coverage)

LHS ensures uniform 5D space coverage across all NCs (bounds: tstep∈[8,12], flows∈[0.5,5.0] mL/min).

---

## 2. Strategy A: Heuristic Baseline

**Objective**: Exploitation-only control group representing domain heuristics without statistical learning.

**Method**:
1. For each NC, compute best-achieved metrics from 100 seeds
2. Score: `S_A(NC) = (pu × re × pr) / (σ + ε)`
   - Numerator: Product of purity, recovery, productivity
   - Denominator: Penalize variance across successful seeds (ε=0.01)
3. Rank all 32 NCs by S_A
4. Select top 5 for Phase 3 high-fidelity optimization

**Rationale**: Pure exploitation based on empirical Phase 2 performance. No learning across 3,200 points.

**Expected behavior**: Consistent selection of obvious winners; misses unexplored high-potential NCs.

---

## 3. Strategy B: Bayesian Optimization with Gaussian Process

**Objective**: Statistical surrogate model with weak exploration using uncertainty quantification.

**Method**:

### Step B1: Gaussian Process Fitting
- **Input**: 3,200 (NC, flow parameters) → (J_validated, purity, recovery)
- **Kernel**: Matérn(ν=2.5) [chosen for moderate-smoothness assumption, fewer constraints than RBF]
- **Hyperparameter optimization**: Marginal likelihood maximization (Type II ML)
- **Output**: Posterior mean μ(NC) and variance σ²(NC) for each NC

### Step B2: Uncertainty-Guided Ranking
For each NC, compute:
```
S_B(NC) = μ(NC) + 0.5·√σ²(NC)
```
- First term: Predicted performance (exploitation)
- Second term: Weak exploration bonus (0.5 weighting intentionally conservative)

### Step B3: Selection
Rank by S_B, select top 5 NCs.

**Rationale**: GP generalizes across 3,200 seed optimizations. √σ² term encourages modest exploration of uncertain NCs while maintaining exploitation focus.

**Expected behavior**: Beats heuristic by leveraging all Phase 2 data. Predicts well in explored regions; may underexplore uncertain areas.

---

## 4. Strategy C: Agent-Guided LHS with Domain Knowledge

**Objective**: Reasoned integration of domain physics with data-driven exploration heuristics.

**Method**:

### Step C1: Landscape Interpretation
For each NC's 100 seed results, compute:
- `success_rate` = (# feasible seeds) / 100
- `variance` = σ(J | feasible)
- `best_found` = max(J | feasible)

**Agent classification**:
```
High success + low variance  → EXPLOITED (well-optimized)
High success + high variance → MULTIMODAL (opportunity?)
Low success + high variance  → UNDEREXPLORED (hidden potential)
Low success + low variance   → DIFFICULT (structural limitation)
```

### Step C2: Physics-Based Scoring

For each NC, compute bonus:
```
domain_bonus(NC) = b_zone + b_physics + b_bottleneck

where:
  b_zone = +0.05 if (# cols per zone) balanced, else -0.03
  b_physics = +0.05 if layout aligns with SMB theory, else -0.03
  b_bottleneck = +0.07 if addresses known constraint, else 0
```

**Physical intuition**:
- Zone imbalance (e.g., 1 column in desorbent zone) limits throughput
- Column distribution affects feed vs extract separation efficiency
- Addresses problems identified in prior SMB literature

### Step C3: Exploration-Exploitation Balance

Define exploration potential:
```
E(NC) = √(variance + search_sparsity) / success_rate
```
High E indicates NC with variance (uncertain behavior) worth investigating.

### Step C4: Portfolio Selection

Sort NCs by combined score:
```
S_C(NC) = (best_found / best_possible) + (domain_bonus × 0.3) + (E / max(E) × 0.2)
```

Select portfolio strategy:
- Top 3 picks: High base performance + favorable domain factors (EXPLOITATION)
- Next 2 picks: High exploration potential + reasonable baseline (EXPLORATION)

Rationale: Remaining evaluation budget (5 NCs) allows both refinement and discovery.

**Expected behavior**: Discovers underexplored NCs with hidden potential. May overweight domain heuristics if they conflict with data.

---

## 5. Phase 3: High-Fidelity Validation

For each strategy's top-5 NC selection:

**Optimization Setup**:
- Discretization: nfex=10, nfet=5, ncp=2 (high-fidelity)
- Constraints: purity ≥ 0.60, recovery ≥ 0.75 (strict, production-intent)
- Budget: 200 IPOPT iterations max
- Repeats: 3 independent runs per NC (different random seeds)

**Metrics**:
- **Primary**: J_validated (productivity) at convergence
- **Secondary**: Purity, recovery (GA & MA) at convergence
- **Tertiary**: Computational time, convergence rate

**Statistical Analysis**:
1. Best J achieved across top-5 picks per strategy
2. One-way ANOVA: H₀ = all strategies equivalent
3. Post-hoc: Tukey HSD pairwise comparisons (α=0.05)
4. Effect size: Cohen's d between winning and baseline strategy
5. Confidence intervals: 95% bootstrapped (n=10,000)

---

## 6. Comparison Metrics

### 6.1 Primary Metric: Best Productivity

```
J_best(strategy) = max(J_validated) across top 5 NCs and 3 runs
```
Direct measure of strategy effectiveness: which identifies highest-performing NC?

### 6.2 Portfolio Quality

**Exploitation reliability**:
```
J_exploit = mean(J | top 3 picks, all runs)
σ_exploit = std(J | top 3 picks, all runs)
```
Consistency of "safe" picks.

**Exploration success**:
```
J_explore = mean(J | picks 4-5, all runs)
Δ_explore = J_explore - J_exploit
```
Did exploration picks outperform exploitation? By how much?

### 6.3 Data Utilization Efficiency

```
E_BO = J_best / (3200 + T_GP)
E_Agent = J_best / (3200 + T_Agent)
E_Heuristic = J_best / 100
```
Productivity gain per data point and computational time. (Lower denominator = higher efficiency)

### 6.4 Prediction Accuracy (Strategy B only)

Correlation between Phase 2 GP predictions (μ_B) and Phase 3 high-fidelity results:
```
r_Pearson = corr(μ_B, J_actual)
MAE = mean(|μ_B - J_actual|)
```
Validates GP generalization quality.

---

## 7. Expected Outcomes

### Hypothesis 1 (C > B > A): Domain + Reasoning Wins
- **Interpretation**: Physics intuition + exploration heuristics beat pure statistics
- **Mechanism**: Agent identifies underexplored high-potential NCs; GP misses due to smoothness assumptions
- **Publication angle**: "Hybrid AI outperforms pure machine learning in process optimization"
- **Implication**: Domain knowledge valuable; ensemble methods promising

### Hypothesis 2 (B > C > A): Statistics Dominates
- **Interpretation**: GP generalizes better than domain heuristics; statistical patterns stronger
- **Mechanism**: 3,200-point surrogate captures SMB complexity; domain rules are noise
- **Publication angle**: "Data-driven surrogate modeling superior to domain expertise for NC selection"
- **Implication**: Focus on high-quality data, not heuristics

### Hypothesis 3 (A ≈ C ≈ B): All Equivalent
- **Interpretation**: Problem simple; all approaches sufficient
- **Mechanism**: SMB landscape well-behaved; heuristic coverage adequate
- **Publication angle**: "Efficiency comparison: simple methods rival sophisticated approaches"
- **Implication**: Principle of parsimony; complex methods not justified

---

## 8. Reproducibility

**Code Repository**: All strategies implemented in `benchmarks/phase3_strategy_*.py`
- Strategy A: ~50 lines (simple heuristic)
- Strategy B: ~150 lines (GP fitting + ranking)
- Strategy C: ~100 lines (domain bonus + portfolio selection)

**Evaluation Script**: `benchmarks/evaluate_phase3_strategies.py`
- Loads phase2_summary.json
- Runs all three strategies in parallel
- Executes Phase 3 high-fidelity for each
- Computes all metrics and statistical tests
- Generates manuscript figures

**Data**: All raw results logged as CSV (strategy decisions, Phase 3 outcomes)

**Reproducibility**: Single command runs entire experiment end-to-end

---

## 9. Statistical Power & Sample Size

**Design**:
- 3 strategies (treatment groups)
- 5 top NCs per strategy
- 3 independent runs per NC
- Total high-fidelity evaluations: 45

**Power analysis**:
- Effect size needed to detect (α=0.05, β=0.20): d ≥ 0.85
- Corresponds to ~8-10% difference in J_best
- One-way ANOVA: adequate power for large effects; detect smaller effects only if consistent

**Interpretation**: Study designed to detect meaningful (~5-10%) strategy differences with reasonable confidence.

---

## 10. Limitations & Controls

**Limitations**:
1. Single process (SMB) → generalizability uncertain
2. Relatively coarse Phase 2 discretization → GP may not capture nonlinearities
3. Domain bonus weights (0.3, 0.2) are subjective → sensitivity analysis needed
4. Three runs per NC may be insufficient for high-variance regions

**Controls**:
1. All strategies use identical Phase 2 data → fair comparison
2. Same Phase 3 discretization & constraints → controlled evaluation
3. Blind high-fidelity evaluation (no strategy labels during Phase 3)
4. Statistical significance testing with multiple comparison correction

---

## Summary

Three distinct selection strategies tested on common foundation:
1. **A (Heuristic)**: Baseline exploitation; no learning
2. **B (BO+GP)**: Statistical surrogate; weak exploration
3. **C (Agent+LHS)**: Domain reasoning; balanced exploration

**Key difference**: A uses ~100 data points (per NC best); B and C use all 3,200. If both beat A, we quantify statistical learning value. If C beats B, we demonstrate synergy between domain + exploration.

**Publication-ready**: Protocol defined a priori, metrics specified, analysis plan documented. Results interpreted according to pre-registered hypotheses.

