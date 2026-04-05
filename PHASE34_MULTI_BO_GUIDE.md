# Phase 3-4: Multi-BO Agent Orchestration Guide

## Overview

After Phase 1 (baseline) and Phase 2B (LHS-seeded optimization), Phase 3-4 implements an agent-guided multi-BO exploration system where:

1. **Three BO calculators** (GP, DNN, PINN) make **independent predictions** of high-potential global optima
2. **Agent receives all predictions** and intelligently decides which to evaluate based on agreement level
3. **Progressive tool availability**: Tools unlock as data accumulates (GP→DNN→PINN)
4. **Learning cascade**: After each evaluation, all surrogates retrain and predict again

## Architecture

```
Phase 1 Results (31 points)
       ↓
Phase 2B Results (~80 points)
       ↓
Phase 3: Data Aggregation
   └─→ Unified training dataset (~111 points)
       ↓
Phase 3-4: Main Loop (×50 iterations)
   ├─ BO Calculators: Get predictions
   │  ├─ GP: Expected Improvement (always available)
   │  ├─ DNN: Aggressive nonlinear (after ≥100 points)
   │  └─ PINN: Physics-constrained (after ≥150 points)
   │
   ├─ Agent Analysis: Measure agreement
   │  ├─ High consensus (>67%) → Exploit
   │  ├─ High disagreement → Explore
   │  └─ Moderate → Risk-adjusted
   │
   ├─ Agent Decision: Choose config to evaluate
   │  └─ Returns chosen_config with reasoning
   │
   ├─ Execution: IPOPT evaluation
   │  └─ Loose constraints: purity≥0.20, recovery≥0.20
   │
   └─ Learning: Update all surrogates
      └─ Retrain GP, DNN (if available), PINN (if available)
       ↓
Phase 5: Final Validation (strict constraints)
   └─→ Validate best candidates with purity≥0.70, recovery≥0.90
```

## Progressive Tool Availability

### Stage 1: Initialization (Phase 3 aggregation)
- **Training data**: 31 (Phase 1) + ~80 (Phase 2B) = ~111 points
- **Available**: GP only
- **Status**: Ready to start Phase 3-4

### Stage 2: Early exploration (Phase 3-4, iterations 1-10)
- **Data accumulation**: ~111 + evaluations
- **Available**: GP + DNN (after ≥100 points → available immediately)
- **Status**: Agent can choose between GP (balanced) and DNN (aggressive)

### Stage 3: Mid-phase expansion (Phase 3-4, iterations 11-25)
- **Data accumulation**: ~140+ points
- **Available**: GP + DNN + PINN (after ≥150 points)
- **Status**: Full three-method ensemble available
- **Expected**: PINN unlocks around iteration 5-10

### Stage 4: Late optimization (Phase 3-4, iterations 26-50)
- **Data accumulation**: ~180+ points
- **Available**: GP + DNN + PINN (all three active)
- **Status**: Agent makes decisions with full ensemble

## Agent Decision Strategies

### Strategy 1: Consensus Exploitation (>67% agreement)

**Scenario**: All BO methods predict similar best config

```
GP says:   [1,2,3,2], J≈60.5 ± 1.2
DNN says:  [1,2,3,2], J≈61.0 ± 0.8
PINN says: [1,3,2,2], J≈59.8 ± 1.5

Agent decision:
  "Strong consensus on region [1,2,X,X]
   Agreement level: 66%
   Chosen: [1,2,3,2] (DNN, highest J)
   Confidence: 90%
   Risk: Low (all methods agree)"
```

**When to use**: 
- Early exploration (iterations 1-10)
- High improvement rate (still discovering good regions)

### Strategy 2: Disagreement Exploration (low/no consensus)

**Scenario**: BO methods predict very different configs

```
GP says:   [2,2,2,2], J≈60.2 ± 1.5
DNN says:  [4,1,1,2], J≈58.5 ± 0.4
PINN says: [1,3,2,2], J≈59.8 ± 1.2

Agent decision:
  "Methods strongly disagree!
   Agreement level: 0% (all different)
   Chosen: [4,1,1,2] (DNN, most different)
   Confidence: 50%
   Risk: Medium (disagreement = uncertainty)
   
   Reasoning: Disagreement reveals knowledge gaps.
   Evaluating DNN's choice explores the gap.
   High information value."
```

**When to use**:
- Mid-phase (iterations 10-30)
- Need to explore uncertain regions
- Convergence rate plateauing

### Strategy 3: Risk-Adjusted Trade-off (moderate disagreement)

**Scenario**: Methods suggest different strategies

```
Budget remaining: 10 iterations
DNN:  [3,2,1,2], J≈62.3 ± 0.5  (aggressive, high reward)
GP:   [2,2,2,2], J≈60.5 ± 1.0  (balanced, medium reward)
PINN: [1,2,2,3], J≈58.8 ± 0.8  (conservative, safe)

Agent decision (budget-based):
  "Low budget remaining. Play it safe.
   Chosen: [1,2,2,3] (PINN)
   Confidence: 85%
   Risk: Low (physics-constrained)
   
   Reasoning: 10 iterations left. Can't afford
   DNN's aggressive bet to fail. PINN's safe
   region is better bet."
```

**When to use**:
- Late optimization (iterations 35-50)
- Low remaining budget
- High risk of missing constraints

## Key Metrics

### Agreement Level
- **High (>67%)**: Consensus → exploit
- **Moderate (33-67%)**: Mixed signals → trade-off
- **Low (<33%)**: Disagreement → explore

### Prediction Spread
```
Method 1: J≈62.0
Method 2: J≈61.8
Method 3: J≈61.2
→ Spread = 0.8 → Low uncertainty → Trust predictions

vs.

Method 1: J≈65.0
Method 2: J≈58.0
Method 3: J≈62.0
→ Spread = 7.0 → High uncertainty → More risky
```

### Confidence Calculation
```
confidence = agreement_level × method_uncertainty_adjustment
           × budget_factor

High agreement (70%) + low uncertainty + medium budget (25 iters)
→ confidence = 0.70 × 0.95 × 0.85 ≈ 0.56 → Moderate-High

Low agreement (20%) + high uncertainty + low budget (5 iters)
→ confidence = 0.20 × 0.60 × 0.50 ≈ 0.06 → Low confidence
```

## Running Phase 3-4

### Prerequisites
- ✅ Phase 1 complete: `artifacts/phase1_lhs_only/phase1_lhs_only_summary.json`
- ✅ Phase 2B complete: `artifacts/phase2b_lhs_seeding/phase2b_summary.json`

### Submit job
```bash
sbatch slurm/pace_smb_phase34_multi_bo_agent.slurm
```

### Monitor progress
```bash
# Check job status
squeue -u qtran47

# Watch logs in real time
tail -f logs/smb-phase34-multiBO-JOBID.out

# Check accumulated results
jq '.evaluation_history | length' artifacts/phase34_multi_bo_agent/phase34_summary.json
```

### Expected output
```
artifacts/phase34_multi_bo_agent/
├── phase3_training_data.json          # Aggregated Phase 1+2B data
├── phase34_summary.json               # Final results and history
└── evaluations/
    ├── phase34_iter01_nc_1123
    ├── phase34_iter02_nc_2212
    └── ...
```

## Example Decision Log

```
═════════════════════════════════════════════════════════════════════
AGENT DECISION (Iteration 5)
═════════════════════════════════════════════════════════════════════
Strategy: explore_disagreement
Chosen Config: [4,1,1,2]
Source Method: dnn
Predicted J: 58.52
Confidence: 50%
Expected Value: 29.26

HIGH DISAGREEMENT EXPLORATION (unique configs=3)
  BO methods strongly disagree on best config.

  Decision: Evaluate [4,1,1,2] from DNN

  Analysis:
    • 3 methods disagree (each predicts different config)
    • Disagreement = high model uncertainty = knowledge gap
    • Method 'DNN' is most aggressive/explorative
    • High information value: learning why methods disagree
    • Predicted J = 58.52 ± 0.42

  Risk/Reward:
    • High reward potential (DNN sees opportunities others miss)
    • Medium risk (might not meet consensus expectations)
    • Learning value: high (will clarify disagreement)

  Expected outcome: 50% chance J>58.52, 50% chance J<56.68
  Iterations remaining: 46

═════════════════════════════════════════════════════════════════════

✓ Evaluation successful
  Productivity: 57.23
  Purity: 0.28
  Recovery GA: 0.22
  Recovery MA: 0.21

Retraining BO surrogates...
  ✓ GP trained on 112 points (J: 58.34±2.14)
  ✓ DNN trained on 112 points (J: 58.91±1.87)
  ⏳ PINN: Waiting for 150 points (have 112)
```

## Comparison: Single-BO vs Multi-BO+Agent

### Single BO+GP
- Commits to GP's prediction
- Misses nonlinear patterns (DNN's strength)
- Conservative uncertainty
- Expected best J: 55-58

### Single BO+DNN  
- Commits to DNN's prediction
- May overfit or miss physics constraints
- Overconfident uncertainty
- Expected best J: 57-60

### Multi-BO + Agent
- ✅ Consensus → uses GP's principled approach
- ✅ Disagreement → explores via DNN's nonlinearity
- ✅ Trade-off → uses PINN's physics awareness
- ✅ Adapts strategy to budget and convergence
- Expected best J: **59-63** (higher than single methods)

## Success Metrics

To validate this approach:

1. **Best J achieved** > each single method alone
2. **Agreement metrics** show meaningful consensus/disagreement patterns
3. **Agent decisions** are interpretable and justified
4. **Disagreement exploitation** finds configs single methods miss
5. **Convergence speed** faster than random selection

## Common Issues

### Issue: "DNN not available yet"
```
⏳ DNN: Waiting for 100 points (have 112)
```
- Expected: DNN available immediately after Phase 2B (~111 total points)
- If not: Check Phase 2B output includes all_seed_results (not just best)

### Issue: "PINN waiting too long"
```
⏳ PINN: Waiting for 150 points (have 145)
```
- Normal: PINN unlocks after ~10-15 Phase 3-4 iterations
- It's OK to run Phase 3-4 with just GP+DNN while waiting

### Issue: "No improvement for N iterations"
- **Expected**: Normal convergence pattern
- **Action**: Switch to `risk_adjusted` strategy (prioritize PINN for safety)
- Agent automatically adapts based on remaining budget

## Next Steps

After Phase 3-4 completes:

1. **Review results**:
   ```bash
   jq '.best_j' artifacts/phase34_multi_bo_agent/phase34_summary.json
   ```

2. **Compare vs baselines**:
   - Phase 1 best: from `phase1_lhs_only_summary.json`
   - Phase 2B best: from `phase2b_lhs_seeding/phase2b_summary.json`
   - Phase 3-4 best: from `phase34_multi_bo_agent/phase34_summary.json`

3. **Run Phase 5** (final validation with strict constraints):
   ```bash
   sbatch slurm/pace_smb_phase5_final_validation.slurm
   ```
   - Takes best 3-5 configs from Phase 3-4
   - Uses STRICT constraints: purity≥0.70, recovery≥0.90
   - Returns TRUE GLOBAL OPTIMUM under production requirements

## References

- `AGENT_BO_CALCULATOR.md` - Detailed strategy and decision patterns
- `PHASE_PIPELINE.md` - Complete 5-phase pipeline architecture
- `benchmarks/phase3_*.py` - Implementation code
- `slurm/pace_smb_phase34_multi_bo_agent.slurm` - SLURM submission script
