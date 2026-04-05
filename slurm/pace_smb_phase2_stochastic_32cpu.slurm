#!/bin/bash
# Phase 2: Stochastic Parallel Optimization (32 CPUs, 16 Workers)
# Ultra-fast foundation data generation
#
# Key features:
#  - 16 workers × 2 MA97 threads = 32 CPUs total
#  - 3,200 (NC, seed) jobs randomly shuffled
#  - Each worker picks random jobs from pool
#  - No NC ordering dependency
#  - Better load balancing than sequential NC processing
#  - Expected speedup: ~16x (47 hours → ~3 hours)
#
# Advantages:
#  - Fast NCs don't idle waiting for slow ones
#  - Stochastic distribution reduces variance in timing
#  - Workers always have work as long as jobs remain
#  - Fine-grained checkpointing: can resume any missing (NC, seed) pair

#SBATCH --job-name=smb-phase2-stoch-32cpu
#SBATCH -A gts-sn73
#SBATCH --qos=inferno
#SBATCH -p cpu-container
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=24
#SBATCH --mem=64G
#SBATCH --time=05:00:00
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
# Each worker runs seeds in parallel but 12 workers run concurrently
export OMP_NUM_THREADS=2  # Each worker gets 2 threads for MA97
export OMP_DYNAMIC=FALSE
export OMP_PROC_BIND=spread
export OMP_PLACES=cores
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export PYTHONUNBUFFERED=1

# Disable reference gate: LHS seeds already provide search space coverage
export SMB_REFERENCE_GATE=0

LOG_DIR="${LOG_DIR:-$REPO_ROOT/logs}"
ARTIFACT_DIR="${ARTIFACT_DIR:-$REPO_ROOT/artifacts/phase2_lhs_seeding}"
mkdir -p "$LOG_DIR" "$ARTIFACT_DIR"

echo "═══════════════════════════════════════════════════════════════════════════"
echo "PHASE 2: STOCHASTIC PARALLEL OPTIMIZATION (32 CPUs, 16 Workers)"
echo "═══════════════════════════════════════════════════════════════════════════"
echo "Job: ${SLURM_JOB_ID:-local}"
echo "CPUs: ${SLURM_CPUS_PER_TASK:-24} (12 workers × 2 MA97 threads)"
echo "Memory: 96G"
echo "Time: 5 hours (ample margin)"
echo ""
echo "Strategy: Stochastic job distribution"
echo "  • Generate all 3,200 (NC, seed) combinations"
echo "  • Randomly shuffle job pool"
echo "  • 16 workers independently pick jobs from pool"
echo "  • No NC ordering dependency → better load balancing"
echo "  • Fast NCs don't idle; slow ones get multiple workers"
echo ""
echo "Configuration:"
echo "  Discretization: nfex=4, nfet=2, ncp=1 (low-fidelity)"
echo "  Constraints: purity ≥ 0.15, recovery ≥ 0.15"
echo "  Total jobs: 32 NCs × 100 seeds = 3,200"
echo "  Expected ~95%+ success rate"
echo ""
echo "Expected Output:"
echo "  • ~3,040+ total successful seed optimizations"
echo "  • Serves as foundation for Phase 3 strategies"
echo "  • Estimated runtime: 2.5-3.5 hours (47 hours → 3 hours, 16x speedup)"
echo ""
echo "Parallelization:"
echo "  • 12 workers in ProcessPoolExecutor (Python multiprocessing)"
echo "  • Each worker: OMP_NUM_THREADS=2 (2 CPUs per worker)"
echo "  • Result: 12 seeds optimize simultaneously (across any NCs)"
echo "  • Total CPUs used: 12 workers × 2 threads = 24 CPUs"
echo ""

echo "Running Phase 2 with STOCHASTIC parallel optimization..."
echo "Strategy: 12 workers in parallel, each with OMP_NUM_THREADS=2"
echo "Configuration: 12 seeds optimize simultaneously (12 × 2 threads = 24 CPUs)"
echo "Expected speedup: 12x (47 hours → ~4 hours)"
echo ""

"${REPO_ROOT}/.venv/bin/python" -m benchmarks.phase2_parallel_stochastic \
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
  --nfex 4 \
  --nfet 2 \
  --ncp 1 \
  --purity-min 0.15 \
  --recovery-min 0.15 \
  --verbose

EXIT_CODE=$?

echo ""
echo "═══════════════════════════════════════════════════════════════════════════"
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ PHASE 2 STOCHASTIC OPTIMIZATION COMPLETED SUCCESSFULLY"
else
    echo "❌ PHASE 2 FAILED (exit code: $EXIT_CODE)"
    echo "   Checkpoint saved - can resume with: sbatch slurm/pace_smb_phase2_stochastic_32cpu.slurm"
fi
echo "═══════════════════════════════════════════════════════════════════════════"
echo ""
echo "Results:"
echo "  Artifacts: $ARTIFACT_DIR"
echo "  Summary: $ARTIFACT_DIR/phase2_summary.json"
echo "  Checkpoint: $ARTIFACT_DIR/phase2_checkpoint_stochastic.json"
echo ""
echo "Next: Use Phase 2 results for Phase 3 strategy comparison"
echo ""

exit $EXIT_CODE
