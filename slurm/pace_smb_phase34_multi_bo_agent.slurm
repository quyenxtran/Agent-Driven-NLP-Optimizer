#!/bin/bash
# Phase 3-4: Multi-BO Agent Orchestration
# After Phase 1 baseline + Phase 2B LHS seeding, train BO surrogates and run agent-guided exploration

#SBATCH --job-name=smb-phase34-multiBO
#SBATCH -A gts-sn73
#SBATCH --qos=inferno
#SBATCH -p cpu-container
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=12:00:00
#SBATCH --mail-user=qtran47@gatech.edu
#SBATCH --mail-type=END,FAIL
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${SLURM_SUBMIT_DIR:-$SCRIPT_DIR}"
cd "$REPO_ROOT"

source .venv/bin/activate

# IPOPT/MA97 Setup (CPU multi-threaded)
export IPOPT_STACK_ROOT="${IPOPT_STACK_ROOT:-/storage/scratch1/4/qtran47/opt/ipopt-hsl-stack}"
export IPOPT_BIN_DIR="${IPOPT_BIN_DIR:-$IPOPT_STACK_ROOT/bin}"
export IPOPT_LIB_DIR="${IPOPT_LIB_DIR:-$IPOPT_STACK_ROOT/lib}"
export OPENBLAS_LIBDIR="${OPENBLAS_LIBDIR:-/usr/local/pace-apps/manual/packages/fenics/2018/linux-rhel9-cascadelake/gcc-9.4.0/openblas-0.3.28-cg7h4gbbmohnlrdesf4ykgipgza67why/lib}"
export METIS_LIBDIR="${METIS_LIBDIR:-/usr/local/pace-apps/manual/packages/fenics/2018/linux-rhel9-cascadelake/gcc-9.4.0/metis-5.1.0-hkeiflow76hhkltiep2ghivt3jagcryz/lib}"
export PATH="$IPOPT_BIN_DIR:${REPO_ROOT}/.venv/bin:${PATH}"
export LD_LIBRARY_PATH="$IPOPT_LIB_DIR:$OPENBLAS_LIBDIR:$METIS_LIBDIR:${LD_LIBRARY_PATH:-}"
export SMB_HSL_LIB="$IPOPT_LIB_DIR/libcoinhsl.so"

# OpenMP multi-threading for MA97
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-${SLURM_CPUS_PER_TASK:-8}}"
export OMP_DYNAMIC=FALSE
export OMP_PROC_BIND=spread
export OMP_PLACES=cores
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export PYTHONUNBUFFERED=1

# Disable reference gate: Agent uses BO predictions for warm-start
# No need for extra baseline runs, evaluate agent's selected configs directly
export SMB_REFERENCE_GATE=0

LOG_DIR="${LOG_DIR:-$REPO_ROOT/logs}"
ARTIFACT_DIR="${ARTIFACT_DIR:-$REPO_ROOT/artifacts/phase34_multi_bo_agent}"
mkdir -p "$LOG_DIR" "$ARTIFACT_DIR"

echo "═══════════════════════════════════════════════════════════════════════════"
echo "PHASE 3-4: MULTI-BO AGENT ORCHESTRATION"
echo "═══════════════════════════════════════════════════════════════════════════"
echo "Job: ${SLURM_JOB_ID:-local}"
echo "CPUs: ${SLURM_CPUS_PER_TASK:-8} (MA97 multi-threaded)"
echo "Memory: 64G"
echo "Time: 12 hours"
echo ""
echo "Purpose: Train BO surrogates (GP, DNN, PINN) on Phase 1+2B data"
echo "         Then run agent-guided exploration with intelligent prioritization"
echo ""
echo "Progressive Tool Availability:"
echo "  ✓ GP: Available from start (needs ≥1 point)"
echo "  ⏳ DNN: Available after ≥100 points (Phase 1 + Phase 2B start)"
echo "  ⏳ PINN: Available after ≥150 points (Phase 2B expansion)"
echo ""
echo "Expected Data Accumulation:"
echo "  Phase 1: 31 baseline points"
echo "  Phase 2B: ~80 optimized points"
echo "  Total: ~111 points → GP + DNN ready immediately"
echo "  After some Phase 34 exploration: ~150+ → PINN ready"
echo ""
echo "Agent Decision Strategies:"
echo "  • Consensus (>67% agreement) → Exploit best prediction"
echo "  • Disagreement (all different) → Explore gap (high information value)"
echo "  • Trade-off (moderate) → Risk-adjusted based on remaining budget"
echo ""
echo "Constraint Strategy:"
echo "  Phase 3-4 uses LOOSE constraints for BO development:"
echo "    - Purity ≥ 0.20 (vs strict 0.70)"
echo "    - Recovery ≥ 0.20 (vs strict 0.90)"
echo "    - Allows broad exploration of design space"
echo ""
echo "Next: After Phase 3-4, use Phase 5 for final validation with STRICT constraints"
echo ""

echo "Running Phase 3-4 Multi-BO Agent Orchestration..."
"${REPO_ROOT}/.venv/bin/python" -m benchmarks.phase34_multi_bo_agent \
  --max-iterations 50 \
  --artifact-dir "$ARTIFACT_DIR" \
  --phase1-dir "$REPO_ROOT/artifacts/phase1_lhs_only" \
  --phase2b-dir "$REPO_ROOT/artifacts/phase2b_lhs_seeding" \
  --risk-tolerance 0.5

EXIT_CODE=$?

echo ""
echo "═══════════════════════════════════════════════════════════════════════════"
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ PHASE 3-4 MULTI-BO AGENT ORCHESTRATION COMPLETED SUCCESSFULLY"
else
    echo "❌ PHASE 3-4 FAILED (exit code: $EXIT_CODE)"
fi
echo "═══════════════════════════════════════════════════════════════════════════"
echo ""
echo "Results:"
echo "  Artifacts: $ARTIFACT_DIR"
echo "  Summary: $ARTIFACT_DIR/phase34_summary.json"
echo "  Training data: $ARTIFACT_DIR/phase3_training_data.json"
echo ""
echo "Pipeline Progress:"
echo "  Phase 1: ✅ Complete (baseline evaluation)"
echo "  Phase 2B: ✅ Complete (LHS-seeded optimization)"
echo "  Phase 3-4: ✅ Complete (multi-BO agent exploration)"
echo "  Phase 5: ⏳ Ready (final validation with strict constraints)"
echo ""
echo "Next: Run Phase 5 to validate best candidates with STRICT production constraints"
echo ""

exit $EXIT_CODE
