#!/bin/bash
# Phase 2: Optimization with LHS-Sampled Seeds
# Uses Latin Hypercube Sampling to generate diverse seed points
# across the 5-D flow space for each NC (instead of fixed reference seeds)

#SBATCH --job-name=smb-phase2-lhs
#SBATCH -A gts-sn73
#SBATCH --qos=inferno
#SBATCH -p cpu-container
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=20:00:00
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

# Disable reference gate: LHS seeds already provide search space coverage
# No need for extra baseline runs, just optimize from each LHS seed
export SMB_REFERENCE_GATE=0

LOG_DIR="${LOG_DIR:-$REPO_ROOT/logs}"
ARTIFACT_DIR="${ARTIFACT_DIR:-$REPO_ROOT/artifacts/phase2_lhs_seeding}"
mkdir -p "$LOG_DIR" "$ARTIFACT_DIR"

echo "═══════════════════════════════════════════════════════════════════════════"
echo "PHASE 2: LHS-SEEDED OPTIMIZATION (Foundation Data Generation)"
echo "═══════════════════════════════════════════════════════════════════════════"
echo "Job: ${SLURM_JOB_ID:-local}"
echo "CPUs: ${SLURM_CPUS_PER_TASK:-8} (MA97 multi-threaded)"
echo "Memory: 32G"
echo "Time: 20 hours (1200 minutes, includes Stage 1 + Stage 2)"
echo ""
echo "Purpose: Generate comprehensive screening data for Phase 3 strategy comparison"
echo ""
echo "Two-Stage Screening per NC (100 seeds for proper 5D coverage):"
echo "  Stage 1: Quick feasibility check (all seeds, ~10s each)"
echo "    • Ultra-low fidelity (nfex=3, nfet=1, ncp=1)"
echo "    • Very relaxed constraints (purity≥0.05) - just check if feasible"
echo "    • Filter out clearly infeasible seeds"
echo ""
echo "  Stage 2: Full optimization (only feasible seeds, ~50s each)"
echo "    • Standard low-fidelity (nfex=4, nfet=2, ncp=1)"
echo "    • Standard constraints (purity≥0.15, recovery≥0.15)"
echo "    • Keep all valid results for Phase 3"
echo ""
echo "Expected Output:"
echo "  • Stage 1: Filter 3100 seeds (~40-50% typically feasible)"
echo "  • Stage 2: Optimize ~1500-1850 feasible seeds"
echo "  • Expected ~95%+ success rate on feasible seeds"
echo "  • Serves as foundation for all Phase 3 strategies"
echo "  • Better space coverage with efficient computation"
echo "  • Estimated runtime: 18-22 hours (40-50% faster than full optimization)"
echo ""

echo "Running Phase 2 with TWO-STAGE screening..."
echo "Stage 1: Quick feasibility check on all seeds (~10s each)"
echo "Stage 2: Full optimization only on feasible seeds (~50s each)"
echo "Expected speedup: 40-50% vs full optimization"
"${REPO_ROOT}/.venv/bin/python" -m benchmarks.phase2_screening_two_stage \
  --ncs "[1,1,2,4]" "[1,1,3,3]" "[1,1,4,2]" "[1,2,1,4]" "[1,2,4,1]" \
         "[1,3,1,3]" "[1,3,2,2]" "[2,1,2,3]" "[2,2,1,3]" "[2,2,2,2]" \
         "[1,1,1,5]" "[1,1,5,1]" "[1,5,1,1]" "[5,1,1,1]" "[1,2,2,3]" \
         "[1,2,3,2]" "[1,3,2,1]" "[2,1,1,4]" "[2,1,3,2]" "[2,1,4,1]" \
         "[2,2,3,1]" "[2,3,1,2]" "[2,3,2,1]" "[3,1,1,3]" "[3,1,2,2]" \
         "[3,1,3,1]" "[3,2,1,2]" "[3,2,2,1]" "[3,3,1,1]" "[4,1,1,2]" \
         "[4,1,2,1]" "[4,2,1,1]" \
  --n-seeds 100 \
  --artifact-dir "$ARTIFACT_DIR" \
  --timeout 120 \
  --verbose

EXIT_CODE=$?

echo ""
echo "═══════════════════════════════════════════════════════════════════════════"
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ PHASE 2 LHS-SEEDED OPTIMIZATION COMPLETED SUCCESSFULLY"
else
    echo "❌ PHASE 2 FAILED (exit code: $EXIT_CODE)"
fi
echo "═══════════════════════════════════════════════════════════════════════════"
echo ""
echo "Results:"
echo "  Artifacts: $ARTIFACT_DIR"
echo "  Summary: $ARTIFACT_DIR/phase2_summary.json"
echo ""
echo "Next: Use Phase 2 results for Phase 3 strategy comparison"
echo ""

exit $EXIT_CODE
