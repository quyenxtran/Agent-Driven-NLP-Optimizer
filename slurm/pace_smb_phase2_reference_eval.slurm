#!/bin/bash
# Phase 2: Reference Evaluation with 5D LHS Sampling
# Evaluates fixed flow points using reference-eval (no optimization)
# 5D Latin Hypercube sampling: [F1, ffeed, fdes, fex, tstep]
# Medium fidelity: nfex=6, nfet=3, ncp=1

#SBATCH --job-name=smb-phase2-ref
#SBATCH -A gts-sn73
#SBATCH --qos=inferno
#SBATCH -p cpu-small
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=24
#SBATCH --mem=32G
#SBATCH --time=01:00:00
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

# Parallel configuration: 12 workers × 2 MA97 threads each = 24 CPUs total
export OMP_NUM_THREADS=2  # Each worker gets 2 threads for MA97
export OMP_DYNAMIC=FALSE
export OMP_PROC_BIND=spread
export OMP_PLACES=cores
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export PYTHONUNBUFFERED=1

LOG_DIR="${LOG_DIR:-$REPO_ROOT/logs}"
ARTIFACT_DIR="${ARTIFACT_DIR:-$REPO_ROOT/artifacts/phase2_lhs_seeding}"
mkdir -p "$LOG_DIR" "$ARTIFACT_DIR"

echo "═══════════════════════════════════════════════════════════════════════════"
echo "PHASE 2: REFERENCE EVALUATION WITH 5D LHS SAMPLING"
echo "═══════════════════════════════════════════════════════════════════════════"
echo "Job: ${SLURM_JOB_ID:-local}"
echo "CPUs: ${SLURM_CPUS_PER_TASK:-24} (MA97 multi-threaded)"
echo "Memory: 32G"
echo "Time: 1 hour"
echo ""
echo "Purpose: Generate foundation reference data at LHS-sampled flow points"
echo ""
echo "5D LHS Reference Evaluation (25 seeds per NC, no optimization):"
echo "  Seeds:"
echo "    • Generate 25 5D LHS points: [F1, ffeed, fdes, fex, tstep]"
echo "    • Bounds: F1[0.5-5.0], ffeed[0.5-2.5], fdes[0.5-2.5], fex[0.5-2.5], tstep[8-12]"
echo "    • Derive Fraf from mass balance: Fraf = Ffeed + Fdes - Fex"
echo "    • Enforce Fraf bounds [0.5, 5.0]"
echo ""
echo "  Evaluation:"
echo "    • Use reference-eval stage (NOT optimize-layouts)"
echo "    • Evaluate at fixed flows with no optimization"
echo "    • Medium fidelity: nfex=6, nfet=3, ncp=1"
echo "    • Relaxed constraints: purity≥0.05, recovery_GA≥0.10, recovery_MA≥0.15"
echo ""
echo "  Parallelization:"
echo "    • 12 workers in ProcessPoolExecutor (Python multiprocessing)"
echo "    • Each worker: OMP_NUM_THREADS=2 (2 CPUs per worker)"
echo "    • Result: 12 seeds evaluate simultaneously"
echo "    • Total CPUs used: 12 workers × 2 threads = 24 CPUs"
echo ""
echo "Expected Output:"
echo "  • 32 NCs × 25 seeds = 800 total reference evaluations"
echo "  • Expected ~40-60% success rate with relaxed constraints (320-480 feasible solutions)"
echo "  • Deterministic results (fixed flows, no solver exploration)"
echo "  • Estimated runtime: ~10-15 minutes (12 workers = 3x speedup)"
echo ""

echo "Running Phase 2 Reference Evaluation with 5D LHS sampling..."
"${REPO_ROOT}/.venv/bin/python" -m benchmarks.phase2_reference_evaluation \
  --ncs "[1,1,2,4]" "[1,1,3,3]" "[1,1,4,2]" "[1,2,1,4]" "[1,2,4,1]" \
         "[1,3,1,3]" "[1,3,2,2]" "[2,1,2,3]" "[2,2,1,3]" "[2,2,2,2]" \
         "[1,1,1,5]" "[1,1,5,1]" "[1,5,1,1]" "[5,1,1,1]" "[1,2,2,3]" \
         "[1,2,3,2]" "[1,3,2,1]" "[2,1,1,4]" "[2,1,3,2]" "[2,1,4,1]" \
         "[2,2,3,1]" "[2,3,1,2]" "[2,3,2,1]" "[3,1,1,3]" "[3,1,2,2]" \
         "[3,1,3,1]" "[3,2,1,2]" "[3,2,2,1]" "[3,3,1,1]" "[4,1,1,2]" \
         "[4,1,2,1]" "[4,2,1,1]" \
  --n-seeds 25 \
  --artifact-dir "$ARTIFACT_DIR" \
  --timeout 120 \
  --n-workers 12 \
  --nfex 6 \
  --nfet 3 \
  --ncp 1 \
  --purity-min 0.05 \
  --recovery-ga-min 0.10 \
  --recovery-ma-min 0.15 \
  --verbose

EXIT_CODE=$?

echo ""
echo "═══════════════════════════════════════════════════════════════════════════"
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ PHASE 2 REFERENCE EVALUATION COMPLETED SUCCESSFULLY"
else
    echo "❌ PHASE 2 FAILED (exit code: $EXIT_CODE)"
fi
echo "═══════════════════════════════════════════════════════════════════════════"
echo ""
echo "Results:"
echo "  Artifacts: $ARTIFACT_DIR"
echo "  Summary: $ARTIFACT_DIR/phase2_reference_summary.json"
echo ""
echo "Next: Use Phase 2 reference data for Phase 3 strategy comparison"
echo ""

exit $EXIT_CODE
