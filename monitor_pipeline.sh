#!/bin/bash
# Monitor Pipeline: Track Phase 2 and Phase 3 Strategy Jobs

echo "═══════════════════════════════════════════════════════════════════════════"
echo "PIPELINE STATUS MONITOR - $(date)"
echo "═══════════════════════════════════════════════════════════════════════════"
echo ""

# Check SLURM jobs
echo "📊 SLURM JOBS:"
echo "────────────────────────────────────────────────────────────────────────────"
squeue -u qtran47 --format="%.18i %.20j %.2t %.10M %.6C %.10m %.20N" 2>/dev/null || echo "No jobs running"
echo ""

# Check Phase 2 status
echo "🔍 PHASE 2 STATUS:"
echo "────────────────────────────────────────────────────────────────────────────"
if [ -f "artifacts/phase2_lhs_seeding/phase2_summary.json" ]; then
    echo "✅ PHASE 2 COMPLETE"
    SCREENING_COUNT=$(jq '.results | length' artifacts/phase2_lhs_seeding/phase2_summary.json 2>/dev/null || echo "?")
    echo "   NCs processed: $SCREENING_COUNT"
    echo ""
    echo "🚀 ACTION: Ready to submit Phase 3 strategies:"
    echo "   sbatch slurm/pace_smb_phase3_strategy1.slurm"
    echo "   sbatch slurm/pace_smb_phase3_strategy2.slurm"
    echo "   sbatch slurm/pace_smb_phase3_strategy3.slurm"
    echo "   sbatch slurm/pace_smb_phase3_strategy4.slurm"
else
    echo "⏳ Phase 2 still running..."
    if [ -f "logs/smb-phase2-lhs-6279224.out" ]; then
        LAST_NC=$(grep "^NC \[" logs/smb-phase2-lhs-6279224.out | tail -1)
        echo "   Last: $LAST_NC"
        FEASIBLE_COUNT=$(grep "✓ feasible" logs/smb-phase2-lhs-6279224.out | wc -l)
        echo "   Feasible seeds found: $FEASIBLE_COUNT"
    fi
fi
echo ""

# Check Phase 3 strategies
echo "🎯 PHASE 3 STRATEGIES:"
echo "────────────────────────────────────────────────────────────────────────────"

for i in 1 2 3 4; do
    if [ -f "artifacts/phase3_strategy$i/strategy${i}_result.json" ]; then
        STATUS=$(jq -r '.strategy' artifacts/phase3_strategy$i/strategy${i}_result.json 2>/dev/null || echo "unknown")
        BEST_J=$(jq -r '.best_j' artifacts/phase3_strategy$i/strategy${i}_result.json 2>/dev/null || echo "?")
        echo "✅ Strategy $i ($STATUS): best_j=$BEST_J"
    elif [ -d "artifacts/phase3_strategy$i" ]; then
        echo "⏳ Strategy $i: Running..."
    else
        echo "⏹️  Strategy $i: Not submitted"
    fi
done
echo ""

echo "═══════════════════════════════════════════════════════════════════════════"
