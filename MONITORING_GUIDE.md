# Phase 2 Monitoring Guide

**Job ID:** 6284727 (Stochastic Phase 2)

---

## Quick Start: Three Ways to Monitor

### 1. **Live Dashboard** (Recommended) 📊
```bash
python monitor_dashboard.py --watch
```
- Real-time feasibility tracking
- Per-NC breakdown
- ETA estimation
- Updates every 10 seconds

### 2. **Quick Status Check** 🔍
```bash
bash show_feasibility.sh
```
- One-time snapshot
- Fast (2-3 seconds)
- Shows IPOPT logs, feasibility, job status

### 3. **Detailed Feasibility Report** 📈
```bash
python monitor_feasibility.py
```
- Complete feasibility analysis
- Success/fail rates by NC
- Checkpoint status
- Historical data

---

## Real-Time Monitoring Examples

### Watch with 5-second updates:
```bash
python monitor_dashboard.py --watch --interval 5
```

### Quick check every minute:
```bash
while true; do bash show_feasibility.sh; sleep 60; done
```

### See live job output:
```bash
tail -f logs/smb-phase2-stoch-32cpu-6284727.out
```

---

## Understanding the Output

### Dashboard Metrics

**Feasibility Rate:**
```
   [▓▓▓▓▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] 15.0%
```
- ▓ = Feasible seeds
- ░ = Infeasible seeds
- Target: ≥ 60% for publication quality

**IPOPT Logs:**
- Each seed generates ~30 logs (different solver iterations/components)
- 3,200 seeds × 30 = ~96,000 total expected logs
- Helps estimate progress without waiting for final results

**Throughput:**
- logs/min = Speed indicator
- ~3,000-4,000 logs/min is typical
- Slower = System under load / harder optimizations

### Per-NC Breakdown

Shows success rate for each NC:
```
[1,1,2,4]       95         5           95.0%    ← Good!
[1,1,3,3]       78         22          78.0%    ← Good
[1,2,1,4]       42         58          42.0%    ← Poor
```

- NC [1,1,2,4]: 95% success (95 feasible out of 100)
- NC [1,2,1,4]: 42% success (may need relaxed constraints)

---

## What to Expect

### Current Job Configuration
- **Constraints:** purity ≥ 0.15, recovery ≥ 0.15 (standard)
- **Fidelity:** nfex=4, nfet=2 (low, fast)
- **Expected feasibility:** ~50-70%

### Timeline
```
5 min:   First logs appear, ~5-10% of seeds started
10 min:  ~50 seeds processed
15 min:  ~75% complete, can see per-NC patterns
20 min:  Near completion, feasibility rate stabilizing
22-25 min: Complete
```

### If Feasibility Is Low
If you see < 30% success rate:
1. **Check constraints:** Are purity/recovery bounds too tight?
2. **Check discretization:** Is nfex=4 sufficient?
3. **Monitor specific NCs:** Some may be genuinely infeasible
4. **Wait for completion:** Final rate may differ from early results

---

## Interpreting Results

### Good Feasibility (≥ 60%)
```
Success Rate: 78.5% (2510/3200)
```
✅ Data is publication-ready  
✅ Proceed to Phase 3  
✅ No action needed

### Moderate Feasibility (30-60%)
```
Success Rate: 45.2% (1446/3200)
```
⚠️ Some NCs are challenging  
⚠️ May need relaxed constraints  
⚠️ Decision: Accept or re-run with options B/D

### Low Feasibility (< 30%)
```
Success Rate: 15.0% (480/3200)
```
❌ Constraints likely too tight  
❌ Consider rerunning with:
  - Option B: Relaxed constraints (0.05)
  - Option D: Two-stage approach
  - Hybrid: Increase fidelity (nfex=6)

---

## Checkpointing & Recovery

### View checkpoint:
```bash
python -c "import json; c=json.load(open('artifacts/phase2_lhs_seeding/phase2_checkpoint_stochastic.json')); print(f'Completed: {len(c[\"completed_pairs\"])} pairs')"
```

### If job is killed:
1. Resubmit with same command
2. Script automatically resumes from checkpoint
3. No data loss

```bash
sbatch slurm/pace_smb_phase2_stochastic_32cpu.slurm
```

---

## Advanced Monitoring

### Count feasible vs infeasible by NC:
```bash
python monitor_feasibility.py | grep "%" | tail -15
```

### Watch just the success rate:
```bash
watch -n 5 'python monitor_feasibility.py | grep "Success Rate"'
```

### Stream log tail while monitoring:
```bash
# Terminal 1:
python monitor_dashboard.py --watch

# Terminal 2:
tail -f logs/smb-phase2-stoch-32cpu-*.out | grep -E "(Progress|✓|✗)"
```

---

## Understanding IPOPT Log Analysis

The monitoring scripts analyze IPOPT logs for two outcomes:

1. **"Optimal Solution Found"** = ✅ Feasible
   - Constraints satisfied
   - Valid optimization result
   - Counts toward success rate

2. **"Converged to a point of local infeasibility"** = ❌ Infeasible
   - Constraints not satisfied
   - Solver gave up, returned best infeasible point
   - Counts toward failure rate

3. **Other exits** = ⚠️ Error
   - Solver crashed, timeout, or other issues
   - Usually small percentage

---

## Expected Final Output

After job completes, check:
```bash
ls -lh artifacts/phase2_lhs_seeding/phase2_summary.json
```

Should see something like:
```
-rw-r--r-- 1 qtran47 pace-sn73 450K phase2_summary.json
```

View summary:
```bash
python -c "import json; s=json.load(open('artifacts/phase2_lhs_seeding/phase2_summary.json')); print(f'Success: {s[\"statistics\"][\"total_successful\"]}/{s[\"statistics\"][\"total_seeds\"]} ({100*s[\"statistics\"][\"total_successful\"]/s[\"statistics\"][\"total_seeds\"]:.1f}%)')"
```

---

## Next Steps

### When Phase 2 Completes:
```bash
# 1. Verify results
ls artifacts/phase2_lhs_seeding/phase2_summary.json

# 2. Check feasibility
python monitor_feasibility.py

# 3. If satisfied, start Phase 3
python -m benchmarks.evaluate_phase3_strategies \
  --phase2-results artifacts/phase2_lhs_seeding/phase2_summary.json \
  --output-dir artifacts/phase3_results
```

### If Feasibility Is Low:
```bash
# Option B: Quick re-run with relaxed constraints
sbatch slurm/pace_smb_phase2_option_b_relaxed.slurm

# Option D: Two-stage approach
sbatch slurm/pace_smb_phase2_option_d_hybrid_stage1.slurm
```

---

## Commands Cheat Sheet

```bash
# Start monitoring
python monitor_dashboard.py --watch

# One-time status
bash show_feasibility.sh

# View detailed report
python monitor_feasibility.py

# Watch with custom interval
python monitor_dashboard.py --watch --interval 5

# Live SLURM status
squeue -j 6284727 -l

# Live log tail
tail -f logs/smb-phase2-stoch-32cpu-*.out

# Check job is running
squeue -j 6284727

# Cancel if needed
scancel 6284727
```

---

## Troubleshooting

### "No logs yet" error?
- Job is still initializing, wait 1-2 minutes
- Check job status: `squeue -j 6284727`

### Monitoring script slow?
- Use `--watch --interval 30` for less frequent updates
- Or use simpler script: `bash show_feasibility.sh`

### Feasibility dropped mid-run?
- Normal - early results may be atypical
- Final rate more reliable after 50%+ complete

### Job shows 0% feasibility?
- Expected if constraints are too tight
- Consider Option B (relaxed constraints)
- Or hybrid Stage 1 (ultra-relaxed for exploration)

---

## Summary

**Job 6284727 Status:** ✅ Running

**How to monitor:**
1. **Live:** `python monitor_dashboard.py --watch`
2. **Quick:** `bash show_feasibility.sh`
3. **Detailed:** `python monitor_feasibility.py`

**Expected completion:** ~22-25 minutes from start

**Next step:** Run Phase 3 when feasibility rate is satisfactory (≥60%)

🚀 Job is running! Monitor feasibility in real-time and check back in ~20 minutes!
