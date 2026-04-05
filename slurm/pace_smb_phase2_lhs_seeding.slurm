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

# Parallel configuration: 4 workers × 2 MA97 threads each = 8 CPUs total
# Each worker runs seeds sequentially but 4 workers run in parallel
export OMP_NUM_THREADS=2  # Each worker gets 2 threads for MA97
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
echo "Parallel Low-Fidelity Optimization (100 seeds per NC, 5D coverage):"
echo "  Process:"
echo "    • Generate 100 LHS seeds across 5-D flow space"
echo "    • Bounds: tstep[8-12], ffeed[0.5-2.5], fdes[0.5-2.5], fex[0.5-2.5], f1[0.5-5.0]"
echo "    • Run low-fidelity optimization (nfex=4, nfet=2, ncp=1)"
echo "    • Constraints: purity≥0.15, recovery≥0.15"
echo ""
echo "  Parallelization:"
echo "    • 4 workers in ProcessPoolExecutor (Python multiprocessing)"
echo "    • Each worker: OMP_NUM_THREADS=2 (2 CPUs per worker)"
echo "    • Result: 4 seeds optimize simultaneously"
echo "    • Total CPUs used: 4 workers × 2 threads = 8 CPUs"
echo ""
echo "Expected Output:"
echo "  • ~31 NCs × 100 seeds optimizations at low fidelity"
echo "  • Expected ~95%+ success rate"
echo "  • ~3,100 total seed results for Phase 3 strategies"
echo "  • Serves as foundation for all Phase 3 strategies"
echo "  • Estimated runtime: ~12 hours (4x speedup: 47 hours → 12 hours)"
echo ""

echo "Running Phase 2 with PARALLEL seed optimization..."
echo "Strategy: 4 workers in parallel, each with OMP_NUM_THREADS=2"
echo "Configuration: 4 seeds optimize simultaneously (4 × 2 threads = 8 CPUs)"
echo "Expected speedup: 4x (47 hours → ~12 hours)"
"${REPO_ROOT}/.venv/bin/python" -m benchmarks.phase2_parallel_seeds \
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
  --n-workers 4 \
  --nfex 4 \
  --nfet 2 \
  --ncp 1 \
  --purity-min 0.15 \
  --recovery-ga-min 0.15 \
  --recovery-ma-min 0.15 \
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
