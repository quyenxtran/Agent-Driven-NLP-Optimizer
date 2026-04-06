# Phase 3 Publication Plan

_Last revised: 2026-04-06 01:10 EDT_

## Executive summary

Phase 3 is a **publication-quality comparison of NC selection strategies**, but the validation design should avoid wasting compute on identical deterministic repeats.

The revised design is:

1. **Each strategy selects top 5 NCs** from the common Phase 2 dataset.
2. **Run one high-fidelity optimization per selected NC**.
3. **For each strategy, promote the single best NC** from those five.
4. **Run multi-start high-fidelity validation only on that single promoted winner**.

This preserves fair strategy comparison while using compute on the uncertainty that actually matters: **selection quality first, optimization robustness second**.

---

## Why this revision is better

### What we are avoiding
We are explicitly avoiding the old design of:
- 5 NCs per strategy
- 3 repeated high-fidelity runs per NC
- 45 total high-fidelity runs

That older design only makes sense if repeated runs measure meaningful stochasticity.

### Why blind repetition is weak here
For SMB high-fidelity optimization with the same:
- NC,
- discretization,
- solver settings,
- initialization,
- and deterministic code path,

repeating the exact same run usually adds little scientific value.

### What uncertainty actually matters
The more important uncertainties are:
1. **Which NCs each strategy chooses**
2. **Whether the chosen winner is robust to initialization / local optima**

So the revised design spends compute on:
- breadth across **5 distinct NCs** first
- depth only on the **single best promoted NC** afterward

---

## Revised Phase 3 design

## Common input
All strategies consume the same Phase 2 foundation dataset.

Current practical note:
- the active Phase 2 source is the **reference-eval artifact set**
- Phase 3 readers may use an adapted / normalized summary built from raw `reference-eval.*.json` seed files

---

## Strategy-level workflow

For each strategy (S1, S2, S3):

### Stage A — Selection
- rank NCs using that strategy's logic
- output **top 5 NCs**

### Stage B — High-fidelity promotion run
- run **1 high-fidelity optimization per selected NC**
- total: **5 runs per strategy**

### Stage C — Finalist promotion
- choose the **single best NC** among those 5 high-fidelity results
- this is the strategy's promoted finalist

### Stage D — Finalist robustness via multi-start
- run **3 multi-start high-fidelity optimizations** on the promoted finalist
- starts must differ intentionally (initialization / seed / warm-start choice)
- this is **not** blind repetition

### Per-strategy compute budget
- 5 high-fidelity promotion runs
- 3 finalist multi-start runs
- **8 total high-fidelity runs per strategy**

Across 3 strategies:
- **24 total high-fidelity runs**

This is much more efficient than the old 45-run plan.

---

## Strategy definitions in this revised plan

### Strategy 1 — Regular LHS / heuristic baseline
Purpose:
- control / baseline
- pure exploitation from Phase 2 evidence

Question answered:
- can a simple heuristic choose strong top-5 NCs?
- is its single best promoted winner robust?

### Strategy 2 — BO / GP baseline
Purpose:
- statistical surrogate baseline

Question answered:
- does statistical learning choose better top-5 NCs than the baseline?
- is its promoted winner stronger or more robust?

### Strategy 3 — Agent + LHS / domain-guided reasoning
Purpose:
- domain-informed selection strategy

Question answered:
- does domain-guided reasoning improve top-5 quality or finalist robustness?

---

## Scientific interpretation

## Primary comparison axis
The main comparison is still across **strategies**.

But the evidence is now split into two cleaner levels:

### 1. Selection quality
Measured by the **five one-shot high-fidelity promotion runs** per strategy.

Questions:
- Did the strategy's top 5 contain strong NCs?
- How good was the best promoted candidate?
- How much depth is there in the strategy's candidate set?

### 2. Finalist robustness
Measured by the **multi-start runs on the single promoted winner**.

Questions:
- Is the winner robust to initialization?
- Is it consistently recoverable?
- Is the winner brittle or stable?

This is scientifically stronger than treating blind deterministic repeats as “replicates.”

---

## Recommended reporting for the paper

For each strategy, report:

### Selection-stage metrics
- top 5 selected NCs
- high-fidelity result for each of the 5 NCs
- best promoted NC
- best one-shot high-fidelity productivity
- mean / median over the 5 promoted candidates

### Finalist robustness metrics
- 3 multi-start results for the promoted winner
- best result
- mean result
- spread / standard deviation
- convergence / feasibility rate across starts

---

## Recommended paper framing

### Strong claim this design supports
"We compared three NC selection strategies on a common Phase 2 foundation. Each strategy promoted five candidates to high fidelity, after which the best promoted candidate underwent targeted multi-start robustness validation."

### Claim this design avoids making
It avoids pretending that three identical deterministic reruns of the same solve are independent experimental replicates.

---

## Statistical posture

This revised design is still publication-quality, but the statistics should match what is actually being measured.

### Reasonable comparisons
- compare **best promoted one-shot result** across strategies
- compare **distribution of 5 promoted candidates** across strategies
- compare **multi-start robustness of each strategy's finalist**

### Be careful with
- treating 3 multi-start runs as generic replicates for full ANOVA over all strategies without explaining they are multi-start robustness checks, not identical repeats

### Better language
- use terms like **promotion stage**, **finalist**, and **multi-start robustness validation**
- avoid overselling replicate count if runs are deterministic apart from initialization choice

---

## Operational workflow to execute

### Step 1 — finish / consolidate Phase 2
- ensure the active reference-eval dataset is complete and canonical
- normalize raw artifacts if necessary

### Step 2 — run each strategy's top-5 promotion campaign
For each strategy:
- generate ranked top 5 NCs
- run one high-fidelity optimization per selected NC
- write summary JSON

### Step 3 — run finalist multi-start
For each strategy:
- identify winner from Step 2
- run 3 intentionally different high-fidelity starts on that winner
- write robustness summary JSON

### Step 4 — compare strategies
- which strategy found the strongest promoted candidate?
- which strategy produced the most robust finalist?
- how much overlap exists between strategies?

---

## Files that should drive this plan

### Primary execution files
- `benchmarks/phase3_strategy1_regular_lhs.py`
- `benchmarks/phase3_strategy2_bo_baseline.py`
- `benchmarks/phase3_strategy3_agent_lhs.py`
- strategy-specific Slurm launchers in `slurm/`

### Planning docs
- `PLAN.md`
- `PHASE3_PUBLICATION_PLAN.md` ← this file

---

## Practical decision rule

If compute is tight:
- do **5 one-shot high-fidelity runs per strategy**
- then **3 multi-start runs only on each strategy's single winner**

If compute becomes very tight:
- keep the top 5 one-shot design
- reduce finalist multi-start from 3 to 2

If compute is abundant later:
- deepen robustness only after the first comparison is complete

---

## Bottom line

**Phase 3 should compare strategies by their ability to promote strong top-5 candidates, then assess robustness only on the single best promoted NC per strategy via multi-start high-fidelity runs.**
