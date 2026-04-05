#!/bin/bash
# Phase 3: Strategy Comparison Framework
# After Phase 2B screening, compare 4 optimization strategies:
# 1. Regular LHS: Screen → optimize top 5 distinct
# 2. BO Baseline: BO(GP) fitted to screening → optimize top BO predictions
# 3. Agent+LHS: Agent intelligently selects top 5 from screening
# 4. Agent+BO: Agent uses multi-BO predictions for intelligent selection

#SBATCH --job-name=smb-phase3-strategies
#SBATCH -A gts-sn73
#SBATCH --qos=inferno
#SBATCH -p cpu-container
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=04:00:00
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
export SMB_REFERENCE_GATE=0

LOG_DIR="${LOG_DIR:-$REPO_ROOT/logs}"
ARTIFACT_DIR="${ARTIFACT_DIR:-$REPO_ROOT/artifacts/phase3_strategy_comparison}"
mkdir -p "$LOG_DIR" "$ARTIFACT_DIR"

echo "═══════════════════════════════════════════════════════════════════════════"
echo "PHASE 3: STRATEGY COMPARISON"
echo "═══════════════════════════════════════════════════════════════════════════"
echo "Job: ${SLURM_JOB_ID:-local}"
echo "CPUs: ${SLURM_CPUS_PER_TASK:-8}"
echo "Memory: 32G"
echo "Time: 4 hours"
echo ""
echo "Purpose: Compare 4 optimization strategies after Phase 2B screening"
echo ""
echo "Strategies:"
echo "  1. Regular LHS: Screen all → optimize top 5 distinct by productivity"
echo "  2. BO Baseline: BO(GP) to screening → optimize top BO predictions"
echo "  3. Agent+LHS: Agent ranks screening data intelligently"
echo "  4. Agent+BO: Agent uses multi-BO predictions (GP/DNN/PINN)"
echo ""
echo "Goal: Demonstrate Agent+BO beats all alternatives"
echo ""
echo "Input: Phase 2B screening data (~300-350 feasible seeds)"
echo "Output: Best J achieved by each strategy"
echo ""

echo "Running Phase 3 Strategy Comparison..."
"${REPO_ROOT}/.venv/bin/python" -m benchmarks.phase3_strategy_comparison \
  --phase2b-dir "$REPO_ROOT/artifacts/phase2b_lhs_seeding" \
  --artifact-dir "$ARTIFACT_DIR" \
  --strategies 1 2 3 4

EXIT_CODE=$?

echo ""
echo "═══════════════════════════════════════════════════════════════════════════"
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ PHASE 3 STRATEGY COMPARISON COMPLETED"
else
    echo "❌ PHASE 3 FAILED (exit code: $EXIT_CODE)"
fi
echo "═══════════════════════════════════════════════════════════════════════════"
echo ""
echo "Results:"
echo "  Artifacts: $ARTIFACT_DIR"
echo "  Summary: $ARTIFACT_DIR/phase3_comparison_summary.json"
echo ""
echo "Pipeline Progress:"
echo "  Phase 2B: ✅ Complete (screening with 100 LHS seeds per NC)"
echo "  Phase 3: ✅ Complete (strategy comparison)"
echo "  Phase 4: ⏳ Ready (winner strategy full run with extended budget)"
echo "  Phase 5: ⏳ Ready (final validation with strict constraints)"
echo ""

exit $EXIT_CODE
