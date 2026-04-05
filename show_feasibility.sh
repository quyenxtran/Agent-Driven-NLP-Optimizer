#!/bin/bash
# Quick feasibility status display

echo "═══════════════════════════════════════════════════════════════════════"
echo "PHASE 2 REAL-TIME STATUS (Job 6284727)"
echo "═══════════════════════════════════════════════════════════════════════"
echo ""

# Job status
echo "📋 Job Status:"
squeue -j 6284727 --format="  %T %i %C %M" 2>/dev/null || echo "  Job not found in queue (may have completed)"

# IPOPT logs count
echo ""
echo "📊 Progress:"
TOTAL_LOGS=$(ls artifacts/phase2_lhs_seeding/ipopt_logs/*.log 2>/dev/null | wc -l)
echo "  IPOPT logs: $TOTAL_LOGS"
echo "  Expected total: ~96,000 (3,200 seeds × ~30 logs per seed)"

# Checkpoint status
echo ""
echo "✅ Checkpoint:"
if [ -f artifacts/phase2_lhs_seeding/phase2_checkpoint_stochastic.json ]; then
    COMPLETED=$(python3 -c "import json; c=json.load(open('artifacts/phase2_lhs_seeding/phase2_checkpoint_stochastic.json')); print(len(c.get('completed_pairs', [])))" 2>/dev/null || echo "?")
    echo "  Completed (NC, seed) pairs: $COMPLETED"
else
    echo "  Checkpoint not yet created"
fi

# Live feasibility analysis
echo ""
echo "📈 Real-Time Feasibility:"
python3 << 'PYTHON_EOF'
import re
from collections import defaultdict
from pathlib import Path

logs_dir = Path("artifacts/phase2_lhs_seeding/ipopt_logs")
if not logs_dir.exists():
    print("  No logs yet")
else:
    logs = list(logs_dir.glob("*.log"))
    feasible_count = 0
    infeasible_count = 0

    for log in logs[:500]:  # Sample first 500 for speed
        with open(log) as f:
            content = f.read()
        if "Optimal Solution Found" in content:
            feasible_count += 1
        elif "Converged to a point of local infeasibility" in content:
            infeasible_count += 1

    total = feasible_count + infeasible_count
    if total > 0:
        rate = 100 * feasible_count / total
        print(f"  Feasible (sampled): {feasible_count}/{total} ({rate:.1f}%)")
        if rate < 50:
            print(f"  ⚠️  Low feasibility detected - may need relaxed constraints")
    else:
        print("  Sampling in progress...")
PYTHON_EOF

echo ""
echo "═══════════════════════════════════════════════════════════════════════"
echo ""
echo "🔄 For live monitoring:"
echo "   python monitor_feasibility.py --watch --interval 10"
echo ""
echo "📊 For detailed analysis:"
echo "   python monitor_feasibility.py"
echo ""
