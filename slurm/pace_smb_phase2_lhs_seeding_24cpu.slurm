#!/bin/bash
# Phase 2: Optimization with LHS-Sampled Seeds (High-Performance: 24 CPUs)
# Uses Latin Hypercube Sampling to generate diverse seed points
# across the 5-D flow space for each NC (instead of fixed reference seeds)
#
# High-performance variant: 12 workers × 2 MA97 threads = 24 CPUs
# Expected speedup: 3x (47 hours → ~16 hours, realistic ~2.5-3 hours with good convergence)
# Checkpointing enabled: Resume from last completed NC if restarted

#SBATCH --job-name=smb-phase2-lhs-24cpu
#SBATCH -A gts-sn73
#SBATCH --qos=inferno
#SBATCH -p cpu-container
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=24
#SBATCH --mem=64G
#SBATCH --time=06:00:00
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
# Each worker runs seeds sequentially but 12 workers run in parallel
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
echo "PHASE 2: LHS-SEEDED OPTIMIZATION (High-Performance: 24 CPUs)"
echo "═══════════════════════════════════════════════════════════════════════════"
echo "Job: ${SLURM_JOB_ID:-local}"
echo "CPUs: ${SLURM_CPUS_PER_TASK:-24} (MA97 multi-threaded)"
echo "Memory: 64G"
echo "Time: 6 hours (360 minutes)"
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
echo "    • 12 workers in ProcessPoolExecutor (Python multiprocessing)"
echo "    • Each worker: OMP_NUM_THREADS=2 (2 CPUs per worker)"
echo "    • Result: 12 seeds optimize simultaneously"
echo "    • Total CPUs used: 12 workers × 2 threads = 24 CPUs"
echo ""
echo "  Checkpointing:"
echo "    • Results saved after each NC completes"
echo "    • Can resume from last completed NC if restarted"
echo "    • Checkpoint file: phase2_checkpoint.json"
echo ""
echo "Expected Output:"
echo "  • ~31 NCs × 100 seeds optimizations at low fidelity"
echo "  • Expected ~95%+ success rate"
echo "  • ~3,100 total seed results for Phase 3 strategies"
echo "  • Serves as foundation for all Phase 3 strategies"
echo "  • Estimated runtime: ~2.5-3 hours (3x speedup: 47 hours → 2.5-3 hours)"
echo ""

# Check if this is a resumption
if [ -f "$ARTIFACT_DIR/phase2_checkpoint.json" ]; then
    echo "📋 Checkpoint found - resuming from last completed NC..."
    echo "Running Phase 2 with PARALLEL seed optimization (RESUMING)..."
    RESUME_FLAG="--resume"
else
    echo "Starting Phase 2 with PARALLEL seed optimization..."
    RESUME_FLAG=""
fi

echo "Strategy: 12 workers in parallel, each with OMP_NUM_THREADS=2"
echo "Configuration: 12 seeds optimize simultaneously (12 × 2 threads = 24 CPUs)"
echo "Expected speedup: 3x (47 hours → ~2.5-3 hours)"
"${REPO_ROOT}/.venv/bin/python" -m benchmarks.phase2_parallel_seeds_checkpointed \
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
  --n-workers 12 \
  $RESUME_FLAG \
  --verbose

EXIT_CODE=$?

echo ""
echo "═══════════════════════════════════════════════════════════════════════════"
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ PHASE 2 LHS-SEEDED OPTIMIZATION COMPLETED SUCCESSFULLY"
else
    echo "❌ PHASE 2 FAILED (exit code: $EXIT_CODE)"
    echo "   Checkpoint saved - can resume with: sbatch slurm/pace_smb_phase2_lhs_seeding_24cpu.slurm"
fi
echo "═══════════════════════════════════════════════════════════════════════════"
echo ""
echo "Results:"
echo "  Artifacts: $ARTIFACT_DIR"
echo "  Summary: $ARTIFACT_DIR/phase2_summary.json"
echo "  Checkpoint: $ARTIFACT_DIR/phase2_checkpoint.json"
echo ""
echo "Next: Use Phase 2 results for Phase 3 strategy comparison"
echo ""

exit $EXIT_CODE
