# Quick Reference: BO, LHS, GP for SMB Optimization

## One-Line Summaries

- **LHS (Latin Hypercube Sampling)**: Stratified sampling that guarantees uniform coverage of design space, reducing variance 40-60% vs random sampling
- **GP (Gaussian Process)**: Probabilistic nonparametric model providing both predictions AND uncertainty bounds for every point
- **BO (Bayesian Optimization)**: Sequential strategy that uses GP's uncertainty to intelligently decide where to sample next, achieving 10-100x efficiency vs grid/random search

---

## Quick Decision Matrix

```
GOAL                           → METHOD
─────────────────────────────────────────────────────────────
5D space, ~100 samples         → LHS (guaranteed uniform coverage)
20 expensive evals, unknown    → LHS init (5) + BO (15) 
When does BO beat random?      → After ~5-10 samples (then increasingly)
Unsure about function smooth?  → Matérn(ν=2.5) kernel
Fixed hyperparameters?         → LHS helps 10-20% more than random
Optimizing hyperparameters?    → LHS advantage shrinks, use OASI instead
```

---

## The Three Techniques in Your SMB Context

### LHS for Phase 2
- **What we're doing**: 100 LHS seeds per NC across 5D flow space
- **Why it works**: Stratified sampling ensures we don't miss corners of design space
- **Expected benefit**: More representative than random 100 samples, fewer "dead" optimizations
- **Time cost**: Same as random sampling, just better coverage

### GP for Phase 3 Strategies
- **Strategy 2 uses it explicitly**: Fits GP to screening data, predicts all 31 NCs
- **Strategy 4 uses it implicitly**: Agent consults GP predictions + uncertainty
- **Key insight**: GP's uncertainty (σ) drives where BO looks next
- **Why it matters**: Without uncertainty, we'd have no principled way to explore

### BO for Intelligent Search
- **Phase 3 Strategy 4**: Combines agent reasoning with BO-style acquisition
- **Balances**: Explores uncertain NCs (high σ) + exploits promising NCs (high μ)
- **Efficiency gain**: Avoids wasting budget on regions we've already learned about
- **Implementation**: Could replace random selection with UCB or EI acquisition

---

## Core Mechanics Cheat Sheet

### How LHS Works in One Sentence
"Divide each parameter into M intervals, randomly pick one value from each interval per parameter, combine such that no pairing repeats."

### How GP Works in One Sentence
"Train a probabilistic model on data such that similar inputs → similar outputs; get back both predictions μ and uncertainty σ everywhere."

### How BO Works in One Sentence
"Iteratively: fit GP to data → compute acquisition function using μ and σ → find best acquisition point → evaluate it → repeat."

### Acquisition Function One-Liners
- **EI**: "How much improvement could x give?" → Exploitative but smart
- **UCB**: "What's the optimistic estimate for x?" → Balance knob via β
- **PI**: "How likely is x to beat current best?" → Very conservative

---

## Kernel Selection Rules of Thumb

| Situation | Choose | Why |
|-----------|--------|-----|
| Unknown smoothness (SMB!) | Matérn(2.5) | Flexible, reasonable assumptions |
| Very smooth function | RBF | Fast, clean |
| Rough/noisy | Matérn(0.5) | Allows non-smoothness |
| Don't know anything | Matérn(2.5) | Safe default |

---

## Why LHS + GP + BO Synergize

```
     LHS                    GP                    BO
      ↓                     ↓                      ↓
Good coverage      Accurate surrogate     Smart next sample
   ensures         with uncertainty       decision
 unbiased GP       bounds everywhere      balances:
 training data                            explore|exploit
         ↑────────────────────────────────────────↑
              All three essential for efficiency
```

---

## Common Mistakes and How to Avoid Them

| Mistake | Why Bad | Fix |
|---------|---------|-----|
| Random sampling (no LHS) | Can cluster, miss corners | Use LHS for first 5-20% of budget |
| RBF kernel without checking | Too smooth assumption | Use Matérn(2.5) by default |
| Not normalizing inputs | Scales matter for kernels | Normalize to [0,1] before LHS/BO |
| Ignoring GP uncertainty | Acquisition based on mean only | Always use μ + β·σ in decisions |
| Fixed β in UCB | Only exploits or explores | Use β = √(2 log(t)) or adaptive |
| Optimizing hyperparameters on small data | Overfitting | Set hyperparameters manually initially |
| No parallelization | Sequential is slow | Use batch acquisition for parallel evals |

---

## Implementation Checklist

- [ ] Normalize all parameters to [0, 1]
- [ ] Generate LHS samples with seed for reproducibility
- [ ] Fit GP with Matérn(2.5) or RBF kernel
- [ ] Optimize hyperparameters via marginal likelihood
- [ ] Compute acquisition (EI or UCB with β=√(2log(t)))
- [ ] Optimize acquisition via local search + multistart
- [ ] Evaluate objective, add to data
- [ ] Refit GP, repeat
- [ ] Monitor: plot best objective vs iteration
- [ ] Consider warm-start from similar problems

---

## Computational Complexity Summary

```
LHS generation:        O(n log n)  ← Fast
GP fitting:            O(n³)       ← Slowest, becomes bottleneck at n>1000
GP prediction:         O(n²)       ← Per point, fast
Acquisition optimize:  O(m × n²)   ← m = candidates, usually manageable
```

**Bottom line**: For BO, n grows to ~100-200 before GP becomes slow. Each fit still beats expensive function evaluation.

---

## For Your Phase 3 Strategies

### Strategy 1 (Regular LHS + Direct Opt)
- Just pick top 5 by some heuristic (e.g., purity×recovery/productivity)
- Doesn't use surrogate, so no GP/BO
- Baseline strategy

### Strategy 2 (BO Baseline)
- Fit GP to screening data (100 seeds × 32 NCs = 3200 points)
- Predict at each NC's "best" latent location
- Rank by predicted value
- Optimize top 5

### Strategy 3 (Agent+LHS)
- Agent analyzes screening data characteristics
- Heuristics: balance, stability, feasibility
- Ranks NCs by agent scoring
- Picks top 5

### Strategy 4 (Agent+BO)
- Fit GP + DNN to screening data
- Agent sees both predictions
- Uses ensemble consensus + uncertainty
- Picks top 5 via acquisition-like scoring

---

## Why BO Beats Grid/Random

```
Function evaluations for 5D optimization:

Grid search:     5^5 = 3,125 points needed for systematic coverage
Random:          100-200 points, but many wasted on uninformative regions
BO (LHS+GP+EI):  20-30 points total, almost none wasted
                 └─ 5-10 LHS + 10-20 BO iterations
```

BO wins because each iteration is **informed** by prior data via GP's uncertainty.

---

## For Deep Dives

See `RESEARCH_BO_LHS_GP.md` for:
- Full mathematical formulations
- Detailed kernel derivations
- Posterior update equations
- Information-theoretic justifications
- Recent research on diversity tradeoffs
- Extensive practical examples

---

## Metrics to Track

When implementing BO for SMB:

1. **Convergence**: Plot best objective vs iteration number
   - Should see fast initial rise, then slow refinement
   
2. **Exploration vs Exploitation**: 
   - Track variance of predicted values (narrowing = exploiting)
   
3. **Acquisition efficiency**:
   - Compare random acquisition vs EI/UCB
   - Should see EI/UCB find better points with fewer evals

4. **Kernel quality**:
   - Monitor log marginal likelihood during fitting
   - Should increase monotonically

---

## Key Papers/Resources

- McKay et al. (1979) - Original LHS paper
- Rasmussen & Williams - Gaussian Processes for Machine Learning (free online)
- Brochu et al. - Tutorial on Bayesian Optimization
- Mockus - Bayesian Approach to Global Optimization
- Recent: arXiv papers on informed initialization (OASI)

