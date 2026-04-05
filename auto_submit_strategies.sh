#!/bin/bash
# Auto-submit Phase 3 strategies once Phase 2 completes

PHASE2_COMPLETE="artifacts/phase2_lhs_seeding/phase2_summary.json"
STRATEGY_SUBMITTED_FILE=".phase3_strategies_submitted"

echo "Auto-submission monitor started: $(date)"

# Check if Phase 2 is complete
if [ -f "$PHASE2_COMPLETE" ]; then
    echo "✅ Phase 2 is COMPLETE"

    # Check if we've already submitted strategies
    if [ -f "$STRATEGY_SUBMITTED_FILE" ]; then
        echo "✓ Strategies already submitted"
        exit 0
    fi

    echo ""
    echo "🚀 Submitting Phase 3 strategies..."
    echo "════════════════════════════════════════════════════════════════"

    # Submit all 4 strategies
    JOB1=$(sbatch slurm/pace_smb_phase3_strategy1.slurm | awk '{print $NF}')
    echo "Strategy 1 submitted: Job $JOB1"

    JOB2=$(sbatch slurm/pace_smb_phase3_strategy2.slurm | awk '{print $NF}')
    echo "Strategy 2 submitted: Job $JOB2"

    JOB3=$(sbatch slurm/pace_smb_phase3_strategy3.slurm | awk '{print $NF}')
    echo "Strategy 3 submitted: Job $JOB3"

    JOB4=$(sbatch slurm/pace_smb_phase3_strategy4.slurm | awk '{print $NF}')
    echo "Strategy 4 submitted: Job $JOB4"

    echo "════════════════════════════════════════════════════════════════"
    echo ""
    echo "All strategies submitted. Job IDs: $JOB1 $JOB2 $JOB3 $JOB4"

    # Mark as submitted
    touch "$STRATEGY_SUBMITTED_FILE"
    echo "$JOB1 $JOB2 $JOB3 $JOB4" > "$STRATEGY_SUBMITTED_FILE"

else
    echo "⏳ Phase 2 still running..."
    echo "   Phase 2 summary file: $PHASE2_COMPLETE"
    echo "   Waiting for completion..."

fi
