#!/bin/bash
# Simple status script for use with 'watch' command
# Usage: watch -n 5 ./phase2_status.sh

JOB_ID="6285721"
ARTIFACT_DIR="artifacts/phase2_lhs_seeding"
IPOPT_DIR="$ARTIFACT_DIR/ipopt_logs"

echo "═══════════════════════════════════════════════════════════════════════════"
echo "PHASE 2 STATUS - $(date '+%Y-%m-%d %H:%M:%S')"
echo "═══════════════════════════════════════════════════════════════════════════"
echo ""

# Job status
echo "📋 JOB STATUS:"
squeue -j $JOB_ID --format="%T %i %C %M" -h 2>/dev/null | {
    read state jobid cpus elapsed
    if [ -n "$state" ]; then
        echo "   Job: $jobid | State: $state | CPUs: $cpus | Elapsed: $elapsed"
    else
        echo "   Job not in queue (may have completed or failed)"
    fi
}

echo ""
echo "📊 PROGRESS:"

# Count logs
TOTAL_LOGS=$(ls $IPOPT_DIR/*.log 2>/dev/null | wc -l)
echo "   IPOPT logs: $TOTAL_LOGS (~$(($TOTAL_LOGS / 30)) seeds processed)"

# Count completed pairs from checkpoint
if [ -f "$ARTIFACT_DIR/phase2_checkpoint_stochastic.json" ]; then
    COMPLETED=$(python3 -c "import json; c=json.load(open('$ARTIFACT_DIR/phase2_checkpoint_stochastic.json')); print(len(c.get('completed_pairs', [])))" 2>/dev/null)
    echo "   Completed (NC,seed) pairs: $COMPLETED / 3200"
else
    echo "   Completed (NC,seed) pairs: checking..."
fi

echo ""
echo "✅ FEASIBILITY:"

# Quick feasibility check from logs
python3 << 'EOF'
from pathlib import Path
import re

logs_dir = Path("artifacts/phase2_lhs_seeding/ipopt_logs")
if not logs_dir.exists():
    print("   No logs yet")
else:
    logs = list(logs_dir.glob("*.log"))
    if not logs:
        print("   No logs yet")
    else:
        feasible = 0
        infeasible = 0

        for log in logs:
            with open(log) as f:
                content = f.read()
            # Count both "Optimal Solution Found" and "Solved To Acceptable Level" as feasible
            if "Optimal Solution Found" in content or "Solved To Acceptable Level" in content:
                feasible += 1
            elif "Converged to a point of local infeasibility" in content:
                infeasible += 1

        total = feasible + infeasible
        if total > 0:
            rate = 100 * feasible / total
            bar_len = 30
            filled = int(bar_len * rate / 100)
            bar = "█" * filled + "░" * (bar_len - filled)
            print(f"   [{bar}] {rate:.1f}% ({feasible} feasible, {infeasible} infeasible)")
        else:
            print("   Analyzing...")
EOF

echo ""
echo "⚡ PERFORMANCE:"

# Get elapsed time and calculate throughput
ELAPSED=$(squeue -j $JOB_ID --format="%M" -h 2>/dev/null)
if [ -n "$ELAPSED" ]; then
    # Convert MM:SS to seconds
    MINS=$(echo $ELAPSED | cut -d: -f1)
    SECS=$(echo $ELAPSED | cut -d: -f2)
    # Remove leading zeros to avoid octal interpretation
    MINS=$((10#$MINS))
    SECS=$((10#$SECS))
    TOTAL_SECS=$((MINS * 60 + SECS))

    if [ $TOTAL_SECS -gt 0 ] && [ $TOTAL_LOGS -gt 0 ]; then
        LOGS_PER_MIN=$(echo "scale=1; $TOTAL_LOGS * 60 / $TOTAL_SECS" | bc)
        EST_TOTAL_LOGS=96000  # 3200 seeds * 30 logs/seed
        REMAINING=$((EST_TOTAL_LOGS - TOTAL_LOGS))
        ETA_MINS=$(echo "scale=0; $REMAINING / ($TOTAL_LOGS * 60 / $TOTAL_SECS)" | bc)

        echo "   Throughput: $LOGS_PER_MIN logs/min"
        echo "   ETA: ~$ETA_MINS minutes"
        echo "   Est. finish: $(date -d "+$ETA_MINS minutes" '+%H:%M:%S')"
    fi
fi

echo ""
echo "═══════════════════════════════════════════════════════════════════════════"
