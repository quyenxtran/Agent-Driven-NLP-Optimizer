# Scientific Study: Phase 3 Comparative Analysis

**Publication-Quality Research Protocol for NC Selection Strategy Comparison**

---

## 📋 Study Overview

**Objective**: Compare three NC selection strategies using identical Phase 2 foundation data  
**Hypotheses**: Agent+Domain > BO+GP > Heuristic baseline  
**Design**: Randomized controlled comparative study  
**Duration**: 4 weeks (execution + analysis + manuscript)  
**Publication Target**: AIChE Journal, Computers & Chemical Engineering  

---

## 📚 Documentation Structure

### For Study Planning & Execution
1. **STUDY_EXEC_SUMMARY.md** ← START HERE
   - What study does, why it matters
   - Expected outcomes and interpretation guide
   - Timeline and success criteria
   - 30-minute read

2. **SCIENTIFIC_PROTOCOL.md**
   - Formal research protocol (pre-registration)
   - Hypotheses, design, statistical analysis plan
   - Publication framework and figures outline
   - Reproducibility checklist
   - 1-hour read

3. **MANUSCRIPT_METHODOLOGY.md**
   - Detailed methods for paper (publication-ready)
   - Strategy A, B, C specifications
   - Metrics and expected outcomes
   - Statistical rigor justification
   - 1-hour read

### For Background & Theory
4. **RESEARCH_QUICK_REFERENCE.md**
   - LHS, GP, BO cheat sheet
   - Decision matrices
   - Common mistakes
   - 30 minutes

5. **RESEARCH_BO_LHS_GP.md**
   - Complete theory and math
   - Kernel choices, acquisition functions
   - Implementation examples
   - 2-3 hours

### For Implementation
6. **IMPLEMENTATION_ROADMAP.md**
   - Agent reasoning loop walkthrough
   - Code structure with examples
   - Validation checklist
   - 2 hours

---

## 🚀 How to Use This Study Design

### For Planning (Week 1)
1. Read: STUDY_EXEC_SUMMARY.md (30 min)
2. Read: SCIENTIFIC_PROTOCOL.md sections 1-3 (1 hour)
3. Review: MANUSCRIPT_METHODOLOGY.md (1 hour)
4. **Action**: Finalize pre-registration document, validate Phase 2 data

### For Implementation (Week 2)
1. Reference: MANUSCRIPT_METHODOLOGY.md (strategies A, B, C)
2. Reference: IMPLEMENTATION_ROADMAP.md (code patterns)
3. Execute: All three strategies in parallel
4. Monitor: Progress logging, Phase 3 high-fidelity

### For Analysis (Week 3)
1. Reference: SCIENTIFIC_PROTOCOL.md sections 3-4 (metrics, statistical tests)
2. Run: Statistical analysis according to pre-registered plan
3. Generate: Figures and tables (Table 1, Figures 1-3)
4. Interpret: Results against hypotheses

### For Writing (Week 4)
1. Reference: SCIENTIFIC_PROTOCOL.md section 6 (manuscript structure)
2. Reference: MANUSCRIPT_METHODOLOGY.md (methods section)
3. Draft: Abstract, introduction, results, discussion
4. Submit: To target journal

---

## 📊 Three Strategies at a Glance

| Strategy | Method | Role | Expected |
|----------|--------|------|----------|
| **A: Heuristic** | Score: (pu×re×pr)/var | Baseline (no learning) | Beats baseline by 0% |
| **B: BO+GP** | Fit GP, rank by μ+0.5σ | Statistical learning | Beats A by 5-8% |
| **C: Agent+LHS** | Domain bonus + portfolio | Hybrid reasoning | Beats A by 8-12% |

**Key question**: Which approach selects NCs that perform best at high-fidelity?

---

## 📈 Primary Outcome

**Best Productivity Achieved**

```
J_best(strategy) = max(J_validated) across top 5 NCs × 3 runs

Statistical test: One-way ANOVA + Tukey HSD post-hoc
Significance: α=0.05, β=0.20 (detects 8-10% differences)
Effect size: Cohen's d between winning and baseline strategy
```

---

## 🔬 Experimental Workflow

### Phase 2 (Foundation) — Shared by All
```
3,200 low-fidelity optimizations (100 seeds × 32 NCs)
├─ Data: Phase 2 summary JSON
└─ Purpose: Fair comparison baseline
```

### Phase 3 (Selection & Validation)
```
Strategy A, B, C run in parallel (~10 hours total)
└─ Each selects top 5 NCs

Then high-fidelity validation:
5 NCs × 3 strategies × 3 runs = 45 optimizations (~24 hours)
├─ Discretization: nfex=10, nfet=5, ncp=2
├─ Constraints: purity≥0.60, recovery≥0.75 (strict)
└─ Record: J_validated, purity, recovery per run
```

### Analysis
```
1. Best J per strategy (primary)
2. ANOVA test for differences
3. Post-hoc pairwise comparisons
4. Effect sizes and confidence intervals
5. Secondary metrics (portfolio, efficiency)
```

---

## ✅ Pre-Execution Checklist

### Data & Infrastructure
- [ ] Phase 2 data complete (3,200 points validated)
- [ ] High-fidelity pipeline tested (trial run successful)
- [ ] Metrics computation verified (manual spot-checks)
- [ ] SLURM/compute resources confirmed

### Study Design
- [ ] Hypotheses finalized and written
- [ ] Statistical analysis plan registered
- [ ] Metrics specified (no post-hoc changes)
- [ ] Interpretation guide completed

### Code & Reproducibility
- [ ] Strategy A, B, C implemented
- [ ] Code reviewed (independent review)
- [ ] Evaluation script tested on mock data
- [ ] Git repository set up (clean, documented)

### Documentation
- [ ] Pre-registration document finalized
- [ ] Manuscript outline complete
- [ ] Target journal selected
- [ ] Author contributions defined

---

## 📖 Reading Order by Role

### If You're the Scientist (Designing/Running Study)
1. STUDY_EXEC_SUMMARY.md (30 min) — Understand what we're testing
2. SCIENTIFIC_PROTOCOL.md (1 hour) — Formal design and analysis plan
3. MANUSCRIPT_METHODOLOGY.md (1 hour) — Detailed method specs
4. → Ready to execute

### If You're the Programmer (Implementing Strategies)
1. STUDY_EXEC_SUMMARY.md sections on strategies (10 min)
2. MANUSCRIPT_METHODOLOGY.md sections 2, 3, 4 (1 hour)
3. IMPLEMENTATION_ROADMAP.md (2 hours)
4. → Ready to code

### If You're the Reviewer (Auditing Study)
1. SCIENTIFIC_PROTOCOL.md (1 hour) — Design quality
2. MANUSCRIPT_METHODOLOGY.md (1 hour) — Method rigor
3. Code repository (1 hour) — Implementation correctness
4. → Can assess reproducibility

### If You're Publishing This (Writing Paper)
1. SCIENTIFIC_PROTOCOL.md section 6 (30 min) — Manuscript structure
2. MANUSCRIPT_METHODOLOGY.md (full) (1 hour) — Methods section content
3. Results & figures → Draft → Revise → Submit

---

## 🎯 Expected Outcomes & Interpretation

### Scenario 1: C > B > A (Domain Wins)
- **Interpretation**: Physics intuition + exploration beat pure statistics
- **Message**: "Hybrid AI outperforms statistical learning"
- **Publication venue**: Strong AI + domain integration angle

### Scenario 2: B > C > A (Statistics Wins)
- **Interpretation**: Data-driven surrogate captures complexity better
- **Message**: "Data-driven methods superior to domain heuristics"
- **Publication venue**: Strong ML for process optimization angle

### Scenario 3: C ≈ B >> A (Both Beat Baseline)
- **Interpretation**: Learning matters; method-agnostic
- **Message**: "Data > no learning; choose based on needs"
- **Publication venue**: Practical guide angle

### Scenario 4: A ≥ Others (Unexpected)
- **Interpretation**: Methods misapplied or problem simpler than expected
- **Message**: "Cautionary tale: complexity isn't always better"
- **Publication venue**: Methodological rigor + honest science angle

---

## 📝 Manuscript at a Glance

```
Title:     [Depends on results—see SCIENTIFIC_PROTOCOL.md]
Abstract:  250 words (background, methods, results, implication)
Methods:   1,500 words (three strategies in detail)
Results:   1,500 words (outcomes and statistical analysis)
Discussion: 1,500 words (interpretation, implications, limitations)
Figures:   4-5 (NC comparison, predictions, exploration outcomes)
Tables:    2-3 (strategy comparison, ANOVA results)
```

**Expected length**: 6,000-7,000 words (standard journal format)

---

## 🔄 Study Flow Diagram

```
┌─────────────────────────────────────┐
│ PHASE 2: Foundation (3,200 points) │
└──────────────┬──────────────────────┘
               │
      ┌────────┴────────┐
      │                 │
      ▼                 ▼
┌──────────────┐  ┌──────────────────────┐
│  Strategy A  │  │  Strategies B & C    │
│  (Heuristic) │  │  (Statistical+Agent) │
│   Top 5      │  │       Top 5          │
└──────────────┘  └──────────────────────┘
      │                 │
      └────────┬────────┘
               │
               ▼
    ┌──────────────────────┐
    │ PHASE 3: Validation  │
    │ High-fidelity × 3    │
    │ runs per NC          │
    │ 45 total evals       │
    └──────────────────────┘
               │
               ▼
    ┌──────────────────────┐
    │ Analysis & Results   │
    │ ANOVA, post-hoc,     │
    │ effect sizes         │
    └──────────────────────┘
               │
               ▼
    ┌──────────────────────┐
    │ Manuscript & Submit  │
    │ to target journal    │
    └──────────────────────┘
```

---

## 📚 Key References in Documentation

**For methodological questions**, see:
- Statistical design → SCIENTIFIC_PROTOCOL.md section 4
- Strategy specifications → MANUSCRIPT_METHODOLOGY.md sections 2-4
- Metrics definitions → MANUSCRIPT_METHODOLOGY.md section 6

**For implementation questions**, see:
- Code structure → IMPLEMENTATION_ROADMAP.md section 6
- Agent reasoning → AGENT_IN_BO_LOOP.md
- Reproducibility → SCIENTIFIC_PROTOCOL.md section 11

**For theoretical background**, see:
- LHS explanation → RESEARCH_QUICK_REFERENCE.md + RESEARCH_BO_LHS_GP.md
- BO concepts → RESEARCH_BO_LHS_GP.md section 3
- Acquisition functions → AGENT_IN_BO_LOOP.md section 2

---

## ⏱️ Timeline Summary

| Week | Task | Duration | Deliverable |
|------|------|----------|-------------|
| 1 | Planning & validation | 5 days | Pre-registered protocol |
| 2 | Execution (A, B, C + validation) | 2-3 days | Raw results |
| 3 | Analysis & figures | 3 days | Statistical summary |
| 4 | Writing & revision | 3-4 days | Manuscript draft |

**Critical path**: High-fidelity validation (24 hours) is longest single step.

---

## ✨ Success Criteria

**For Publication**:
- [x] Pre-registered hypothesis
- [x] Controlled comparison
- [x] Reproducible methods
- [x] Statistical rigor
- [x] Honest limitations

**For High-Impact Journal**:
- [ ] Novel findings (surprising or strong effect)
- [ ] Practical significance (>5-10% improvement)
- [ ] Generalizable insights
- [ ] Well-executed study

---

## 🔗 Quick Links in Repo

```
AutoResearch-SMB/
├── STUDY_EXEC_SUMMARY.md           ← START HERE
├── SCIENTIFIC_PROTOCOL.md           ← Formal design
├── MANUSCRIPT_METHODOLOGY.md        ← Methods detail
├── SCIENTIFIC_STUDY_README.md       ← This file
│
├── RESEARCH_QUICK_REFERENCE.md     ← Background
├── RESEARCH_BO_LHS_GP.md           ← Theory
├── AGENT_IN_BO_LOOP.md             ← Implementation context
│
├── benchmarks/
│   ├── phase3_strategy_a.py         ← Strategy A code
│   ├── phase3_strategy_b.py         ← Strategy B code
│   ├── phase3_strategy_c.py         ← Strategy C code
│   └── evaluate_phase3_strategies.py ← Orchestrator
│
├── analysis/
│   └── statistical_analysis.py      ← ANOVA, plots
│
└── artifacts/
    ├── phase2_lhs_seeding/          ← Phase 2 data
    └── phase3_results/              ← Phase 3 outputs
```

---

## 🚀 Next Step

**→ Read: STUDY_EXEC_SUMMARY.md (30 minutes)**

Then decide: Are you ready to execute?

If yes: → SCIENTIFIC_PROTOCOL.md for formal pre-registration  
If no: → RESEARCH_QUICK_REFERENCE.md for background

---

**Last updated**: April 5, 2026  
**Status**: Ready for publication-quality execution
