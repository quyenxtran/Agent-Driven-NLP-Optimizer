# Phase 3: Comparative NC Selection Study

Publication-ready experimental framework comparing three NC selection strategies on a common Phase 2 foundation.

## Overview

This study answers: **Which NC selection strategy yields best SMB process performance?**

| Strategy | Approach | Expected Performance |
|----------|----------|----------------------|
| **A: Heuristic Baseline** | Pure exploitation: score = (pu × re × pr) / variance | Baseline |
| **B: Bayesian Optimization + GP** | Statistical surrogate: rank by μ + 0.5√σ | +5-10% vs A |
| **C: Agent + LHS + Domain** | Domain reasoning + exploration heuristics | +10-15% vs A |

**Study design**: 
- Common Phase 2 foundation: 3,200 seed optimizations (100 LHS per 32 NCs)
- Each strategy selects top 5 NCs independently
- High-fidelity validation: 5 NCs × 3 strategies × 3 runs = 45 optimizations
- Statistical comparison: One-way ANOVA + Tukey HSD post-hoc

---

## Quick Start

### Prerequisites
```bash
# Ensure Phase 2 data is ready
ls artifacts/phase2_lhs_seeding/phase2_summary.json

# Install dependencies (if not already done)
pip install -r requirements.txt
pip install scipy  # For statistical analysis
```

### Run All Strategies + Validation (Recommended)

Full orchestrator (runs everything):
```bash
cd /storage/home/hcoda1/4/qtran47/AutoResearch-SMB
python -m benchmarks.evaluate_phase3_strategies
```

Expected output:
- Strategy A results: `artifacts/phase3_results/strategy_a_selection.json`
- Strategy B results: `artifacts/phase3_results/strategy_b_selection.json`
- Strategy C results: `artifacts/phase3_results/strategy_c_selection.json`
- Summary report: `artifacts/phase3_results/study_summary.json`

**Total runtime**: ~36 hours
- Strategy selections: ~10 minutes
- High-fidelity validation: ~35 hours (45 optimizations × ~45 min each)

---

## Individual Strategy Execution

Run strategies independently (useful for debugging):

### Strategy A: Heuristic Baseline
```bash
python -m benchmarks.phase3_strategy_a_baseline
```

Output:
```json
{
  "strategy": "strategy_a_baseline",
  "selected_ncs": [[n1, n2, n3, n4], ...],  // top 5 NCs
  "rankings": { ... },                      // all NCs scored
  "method": { "name": "Heuristic Baseline", ... }
}
```

**Time**: <1 minute

### Strategy B: Bayesian Optimization + GP
```bash
python -m benchmarks.phase3_strategy_b_bo_gp
```

Output:
```json
{
  "strategy": "strategy_b_bo_gp",
  "selected_ncs": [[n1, n2, n3, n4], ...],
  "gp_diagnostics": {
    "n_training": 3200,
    "training_mean": X.XXX,
    "training_std": X.XXX
  },
  "method": { "name": "Bayesian Optimization + Gaussian Process", ... }
}
```

**Time**: 2-5 minutes (GP fitting is parallelized)

### Strategy C: Agent + LHS + Domain Knowledge
```bash
python -m benchmarks.phase3_strategy_c_agent_lhs
```

Output:
```json
{
  "strategy": "strategy_c_agent_lhs",
  "selected_ncs": [[n1, n2, n3, n4], ...],
  "portfolio_breakdown": {
    "exploitation": { "picks": [...], "rationale": "..." },
    "exploration": { "picks": [...], "rationale": "..." }
  },
  "nc_profiles": { ... },
  "method": { "name": "Agent-Guided LHS with Domain Knowledge", ... }
}
```

**Time**: 1-3 minutes

---

## Strategy Details

### Strategy A: Heuristic Baseline

**Control group**: Domain expertise without data-driven learning.

```python
score(NC) = (mean_purity × mean_recovery × mean_productivity) / (variance + 0.01)
```

**Rationale**: 
- Pure exploitation: uses best empirical results from Phase 2
- No learning across 3,200 seed results
- Establishes baseline for comparison

**Expected behavior**:
- Consistent picks (top performers repeat across runs)
- Misses underexplored NCs with hidden potential
- Provides reference point for statistical learning value

---

### Strategy B: Bayesian Optimization + Gaussian Process

**Statistical surrogate model** with principled acquisition function.

```
1. Fit GP (Matérn kernel) to 3,200 seed results
   - Input: NC configuration (4D)
   - Output: Productivity prediction
   
2. Predict μ(NC), σ(NC) for all NCs
   
3. Rank by acquisition function:
   acquisition(NC) = μ(NC) + 0.5 × √σ(NC)
   
   - First term: predicted performance (exploitation)
   - Second term: uncertainty bonus (weak exploration, β=0.5)
   
4. Select top 5 NCs
```

**Rationale**:
- Generalizes from 3,200 seed optimizations
- Conservative exploration (β=0.5) balances exploitation
- Uncertainty quantification enables principled decision-making

**Expected behavior**:
- Predicts well in explored regions
- May underexplore high-uncertainty areas
- Leverages statistical patterns in Phase 2 data
- Beats heuristic by 5-10% if GP assumptions valid

---

### Strategy C: Agent-Guided LHS + Domain Knowledge

**Hybrid reasoning** combining domain physics + exploration heuristics.

```
1. Landscape Interpretation (per NC):
   - success_rate: fraction of seeds with feasible results
   - variance: σ(productivity | feasible)
   - best_found: max observed productivity
   - classification: EXPLOITED | MULTIMODAL | UNDEREXPLORED | DIFFICULT

2. Physics-Based Scoring:
   domain_bonus = zone_balance_bonus (±0.05)
                + physics_alignment_bonus (±0.05)
                + bottleneck_addressing_bonus (±0.07)
   
   - Zone balance: Prefer [a, b, c, d] with similar values (throughput)
   - Physics alignment: n2 >= n3 (extract side >= raffinate)
   - Bottleneck: Avoid single-column desorbent (known limitation)

3. Exploration Potential:
   E(NC) = √(variance + search_sparsity) / success_rate
   
   High E → NC worth exploring (uncertain, sparse)

4. Portfolio Selection (3 exploit + 2 explore):
   - Exploitation picks: High empirical performance, favorable domain factors
   - Exploration picks: High variance/sparsity, reasonable baseline performance
   
   Balances refinement (exploit) with discovery (explore)
```

**Rationale**:
- Domain knowledge captures SMB-specific constraints
- Portfolio approach enables both exploitation and exploration
- Agent reasoning transparent and interpretable
- Discovers underexplored high-potential NCs

**Expected behavior**:
- Identifies both "safe" winners and risky candidates
- Portfolio diversity hedges against wrong assumptions
- May outperform GP if domain knowledge is accurate
- Beats heuristic by 10-15% through intelligent exploration

---

## Output Structure

### Selection Results
```
artifacts/phase3_results/
├── strategy_a_selection.json    # Heuristic baseline selections
├── strategy_b_selection.json    # BO+GP selections
├── strategy_c_selection.json    # Agent+LHS selections
└── study_summary.json           # Comparative statistics
```

### Validation Results
```
artifacts/phase3_validation/
├── phase3_s[a|b|c]_nc_*_run*.json  # Individual optimization results
└── (45 files total: 3 strategies × 5 NCs × 3 runs)
```

---

## Statistical Analysis

### Primary Metric: Best Productivity Achieved

```
J_best(strategy) = max(J_validated) across top 5 NCs and 3 runs
```

### Comparison Tests

**One-way ANOVA**:
```
H₀: J_best(A) = J_best(B) = J_best(C)  (all strategies equivalent)
H₁: At least one strategy differs (α=0.05)
```

**Post-hoc: Tukey HSD**:
```
Pairwise comparisons (Bonferroni-corrected):
- A vs B
- A vs C
- B vs C
```

**Effect Sizes**:
```
Cohen's d = (μ₁ - μ₂) / pooled_σ
- Small: d ≈ 0.2
- Medium: d ≈ 0.5
- Large: d ≈ 0.8
```

**Confidence Intervals**: 95% bootstrapped (10,000 resamples)

### Expected Outcomes

| Scenario | Probability | Interpretation |
|----------|-------------|-----------------|
| **C > B > A** | 60% | Domain + reasoning outperforms statistics outperforms baseline |
| **B > C > A** | 25% | Statistical learning dominates; domain heuristics are noise |
| **C ≈ B >> A** | 10% | Both sophisticated methods equivalent; domain/statistics equally valuable |
| **A ≥ B, A ≥ C** | 5% | Simple methods sufficient; complex methods not justified |

---

## Monitoring Progress

### Check Phase 2 data
```bash
ls -lh artifacts/phase2_lhs_seeding/phase2_summary.json
python -c "import json; d=json.load(open('artifacts/phase2_lhs_seeding/phase2_summary.json')); print(f\"NCs: {len(d['results'])}, Results: {sum(len(r.get('all_seed_results',[]))for r in d['results'])}\")"
```

### Monitor high-fidelity validation
```bash
ls -lh artifacts/phase3_validation/ | wc -l
# Count completed optimizations (should reach 45)
```

### Check final results
```bash
python -c "import json; d=json.load(open('artifacts/phase3_results/study_summary.json')); print(json.dumps(d['statistics'], indent=2))"
```

---

## Troubleshooting

### "Phase 2 data not found"
```bash
# Resubmit Phase 2 if needed
sbatch slurm/pace_smb_phase2_lhs_seeding.slurm

# Check status
squeue -u $USER
```

### Strategy selection fails
```bash
# Run individual strategy to diagnose
python -m benchmarks.phase3_strategy_a_baseline
python -m benchmarks.phase3_strategy_b_bo_gp
python -m benchmarks.phase3_strategy_c_agent_lhs
```

### High-fidelity optimizations timeout or fail
- Increase `--timeout` in `evaluate_phase3_strategies.py` (default: 900s)
- Check solver logs: `artifacts/phase3_validation/*.log`
- Reduce problem complexity: lower `--nfex` / `--nfet` (but reduces fidelity)

---

## Manuscript Sections

Generated results feed directly into publication:

### Abstract
- **Problem**: NC selection for SMB is expensive
- **Approach**: Compare three strategies (heuristic, BO+GP, agent+domain)
- **Results**: [Strategy X] achieved [Y%] improvement (p<0.05)
- **Conclusion**: [Domain knowledge / statistical learning / ensemble approach] most effective

### Methods
- **Section 3.1**: Phase 2 foundation (common LHS)
- **Section 3.2-3.4**: Three strategy specifications
- **Section 3.5**: High-fidelity validation protocol

### Results
- **Table 1**: Strategy comparison summary
- **Figure 1**: NC selection comparison (bar chart)
- **Figure 2**: Prediction accuracy (Phase 2 vs Phase 3 scatter)
- **Figure 3**: Portfolio composition (exploit vs explore)

### Discussion
- **Interpretation**: Which hypothesis did we confirm?
- **Comparison**: How do findings align with literature?
- **Limitations**: Generalizability, assumptions, future work

---

## Success Checklist

- [ ] Phase 2 data: `artifacts/phase2_lhs_seeding/phase2_summary.json` exists
- [ ] Strategy A: Runs and outputs selection JSON
- [ ] Strategy B: Runs and outputs selection JSON
- [ ] Strategy C: Runs and outputs selection JSON
- [ ] Orchestrator: Runs all strategies and validation
- [ ] Statistics: ANOVA, post-hoc, confidence intervals computed
- [ ] Results: All 45 high-fidelity optimizations completed
- [ ] Manuscript: Draft written with figures and tables

---

## Reference

**Protocol**: `SCIENTIFIC_PROTOCOL.md` — Pre-registration with hypotheses  
**Methodology**: `MANUSCRIPT_METHODOLOGY.md` — Publication-ready methods section  
**Summary**: `STUDY_EXEC_SUMMARY.md` — Executive summary with interpretation guide  
**Status**: `LIVE_STATUS.md` — Real-time progress tracking
