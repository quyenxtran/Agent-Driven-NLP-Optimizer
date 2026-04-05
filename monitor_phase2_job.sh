#!/bin/bash
# Monitor Phase 2 job progress and prepare for continuation if needed

ARTIFACT_DIR="artifacts/phase2_lhs_seeding"
JOB_ID="6282883"

while true; do
    echo "═══════════════════════════════════════════════════════════════"
    date
    echo "═══════════════════════════════════════════════════════════════"

    # Check if job is running
    JOB_STATE=$(squeue -j $JOB_ID --format=%T --noheader 2>/dev/null | tr -d ' ')

    if [ -z "$JOB_STATE" ]; then
        echo "❌ Job $JOB_ID not found in queue (may have completed or failed)"

        # Check for summary
        if [ -f "$ARTIFACT_DIR/phase2_summary.json" ]; then
            echo "✅ Found phase2_summary.json - job completed successfully"
            echo ""
            echo "Summary statistics:"
            python3 -c "import json; d=json.load(open('$ARTIFACT_DIR/phase2_summary.json')); print(f\"  Total seeds: {d['statistics']['total_seeds']}\"); print(f\"  Successful: {d['statistics']['total_successful']}\"); print(f\"  Success rate: {100*d['statistics']['total_successful']/d['statistics']['total_seeds']:.1f}%\")"
        else
            echo "⚠️  Job appears to have crashed before writing summary"
            echo "   Check logs: tail -100 logs/smb-phase2-lhs-$JOB_ID.out"
        fi
        break
    fi

    echo "Job Status: $JOB_STATE"

    # Count current progress
    TOTAL_LOGS=$(ls $ARTIFACT_DIR/ipopt_logs/*.log 2>/dev/null | wc -l)
    UNIQUE_SEEDS=$(ls $ARTIFACT_DIR/ipopt_logs/*.log 2>/dev/null | sed 's/.*seed_//' | sed 's/_nc_.*//' | sort -u | wc -l)

    if [ "$UNIQUE_SEEDS" -gt 0 ]; then
        MAX_SEED=$(ls $ARTIFACT_DIR/ipopt_logs/*.log 2>/dev/null | sed 's/.*seed_//' | sed 's/_nc_.*//' | sort -n | tail -1)
        echo "IPOPT logs: $TOTAL_LOGS"
        echo "Progress: Seed $((MAX_SEED + 1)) / 100 on first NC"

        # Estimate remaining time
        ELAPSED_MIN=$(sstat -j $JOB_ID --format=ElapsedRaw --noheader 2>/dev/null | tail -1 || echo "0")
        if [ -n "$ELAPSED_MIN" ] && [ "$ELAPSED_MIN" != "0" ]; then
            ELAPSED_SEC=$((ELAPSED_MIN))
            SEEDS_PER_SEC=$(echo "scale=4; $UNIQUE_SEEDS / $ELAPSED_SEC" | bc)
            TOTAL_SEEDS_NEEDED=3100
            SEEDS_REMAINING=$((TOTAL_SEEDS_NEEDED - UNIQUE_SEEDS))
            REMAINING_SEC=$(echo "scale=0; $SEEDS_REMAINING / $SEEDS_PER_SEC" | bc)
            REMAINING_HOURS=$(echo "scale=1; $REMAINING_SEC / 3600" | bc)
            echo "Est. remaining: $REMAINING_HOURS hours (~$((REMAINING_SEC / 60)) minutes)"
        fi
    fi

    echo ""
    squeue -j $JOB_ID --format="State JobID NNodes CPUs Memory TimeLimit Elapsed" 2>/dev/null | tail -1

    echo ""
    echo "Waiting 5 minutes before next check..."
    sleep 300
done
