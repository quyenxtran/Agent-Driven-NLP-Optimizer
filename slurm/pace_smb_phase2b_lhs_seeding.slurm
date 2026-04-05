#!/bin/bash
# Phase 2B: Optimization with LHS-Sampled Seeds
# Uses Latin Hypercube Sampling to generate diverse seed points
# across the 5-D flow space for each NC (instead of fixed reference seeds)

#SBATCH --job-name=smb-phase2b-lhs
#SBATCH -A gts-sn73
#SBATCH --qos=inferno
#SBATCH -p cpu-container
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
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

# OpenMP multi-threading for MA97
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-${SLURM_CPUS_PER_TASK:-8}}"
export OMP_DYNAMIC=FALSE
export OMP_PROC_BIND=spread
export OMP_PLACES=cores
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export PYTHONUNBUFFERED=1

LOG_DIR="${LOG_DIR:-$REPO_ROOT/logs}"
ARTIFACT_DIR="${ARTIFACT_DIR:-$REPO_ROOT/artifacts/phase2b_lhs_seeding}"
mkdir -p "$LOG_DIR" "$ARTIFACT_DIR"

echo "═══════════════════════════════════════════════════════════════════════════"
echo "PHASE 2B: LHS-SEEDED OPTIMIZATION (Better Phase 2 with Space Coverage)"
echo "═══════════════════════════════════════════════════════════════════════════"
echo "Job: ${SLURM_JOB_ID:-local}"
echo "CPUs: ${SLURM_CPUS_PER_TASK:-8} (MA97 multi-threaded)"
echo "Memory: 32G"
echo "Time: 60 minutes"
echo ""
echo "Improvement over Phase 2:"
echo "  Phase 2: Fixed reference seeds (NOTEBOOK_SEEDS)"
echo "  Phase 2B: LHS-sampled seeds → better space coverage"
echo ""
echo "Per NC:"
echo "  • Generate 8 LHS seed points across 5-D flow space"
echo "  • Bounds: tstep[8-12], ffeed[0.5-2.5], fdes[0.5-2.5], fex[0.5-2.5], f1[0.5-5.0]"
echo "  • Run IPOPT optimization from each seed"
echo "  • Keep best result (1 data point per NC)"
echo ""
echo "Expected:"
echo "  • Better coverage of flow space"
echo "  • Higher quality data for BO training"
echo "  • Time: ~40 minutes for 10 NCs × 8 seeds each"
echo ""

echo "Running Phase 2B with LHS seeding..."
"${REPO_ROOT}/.venv/bin/python" -m benchmarks.phase2b_lhs_seeding \
  --ncs "[1,1,2,4]" "[1,1,3,3]" "[1,1,4,2]" "[1,2,1,4]" "[1,2,4,1]" \
         "[1,3,1,3]" "[1,3,2,2]" "[2,1,2,3]" "[2,2,1,3]" "[2,2,2,2]" \
  --n-seeds 8 \
  --artifact-dir "$ARTIFACT_DIR" \
  --solver-name "auto" \
  --linear-solver "ma97" \
  --verbose

EXIT_CODE=$?

echo ""
echo "═══════════════════════════════════════════════════════════════════════════"
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ PHASE 2B LHS-SEEDED OPTIMIZATION COMPLETED SUCCESSFULLY"
else
    echo "❌ PHASE 2B FAILED (exit code: $EXIT_CODE)"
fi
echo "═══════════════════════════════════════════════════════════════════════════"
echo ""
echo "Results:"
echo "  Artifacts: $ARTIFACT_DIR"
echo "  Summary: $ARTIFACT_DIR/phase2b_summary.json"
echo ""
echo "Next: Use Phase 2B results to train BO surrogates"
echo ""

exit $EXIT_CODE
