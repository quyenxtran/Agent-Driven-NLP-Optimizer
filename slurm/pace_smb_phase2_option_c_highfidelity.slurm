#!/bin/bash
# Phase 2 Option C: Higher Fidelity (Most Robust)
# Objective: Achieve 50-70% feasibility with better solution quality
#
# Changes from original:
#  - Discretization increased: nfex 4→6, nfet 2→3, ncp 1→2
#  - Constraints same: 0.15 (standard low-fidelity target)
#  - Expected feasibility: 50-70% at higher quality
#  - Runtime: 20-25 hours (longer due to finer discretization)
#  - Quality: Best solution quality, but slowest

#SBATCH --job-name=smb-phase2-opt-c-hifidelity
#SBATCH -A gts-sn73
#SBATCH --qos=inferno
#SBATCH -p cpu-container
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=24
#SBATCH --mem=64G
#SBATCH --time=28:00:00
#SBATCH --mail-user=qtran47@gatech.edu
#SBATCH --mail-type=END,FAIL
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${SLURM_SUBMIT_DIR:-$SCRIPT_DIR}"
cd "$REPO_ROOT"

source .venv/bin/activate

# IPOPT/MA97 Setup
export IPOPT_STACK_ROOT="${IPOPT_STACK_ROOT:-/storage/scratch1/4/qtran47/opt/ipopt-hsl-stack}"
export IPOPT_BIN_DIR="${IPOPT_BIN_DIR:-$IPOPT_STACK_ROOT/bin}"
export IPOPT_LIB_DIR="${IPOPT_LIB_DIR:-$IPOPT_STACK_ROOT/lib}"
export OPENBLAS_LIBDIR="${OPENBLAS_LIBDIR:-/usr/local/pace-apps/manual/packages/fenics/2018/linux-rhel9-cascadelake/gcc-9.4.0/openblas-0.3.28-cg7h4gbbmohnlrdesf4ykgipgza67why/lib}"
export METIS_LIBDIR="${METIS_LIBDIR:-/usr/local/pace-apps/manual/packages/fenics/2018/linux-rhel9-cascadelake/gcc-9.4.0/metis-5.1.0-hkeiflow76hhkltiep2ghivt3jagcryz/lib}"
export PATH="$IPOPT_BIN_DIR:${REPO_ROOT}/.venv/bin:${PATH}"
export LD_LIBRARY_PATH="$IPOPT_LIB_DIR:$OPENBLAS_LIBDIR:$METIS_LIBDIR:${LD_LIBRARY_PATH:-}"
export SMB_HSL_LIB="$IPOPT_LIB_DIR/libcoinhsl.so"

# Parallel configuration: 12 workers × 2 MA97 threads = 24 CPUs
export OMP_NUM_THREADS=2
export OMP_DYNAMIC=FALSE
export OMP_PROC_BIND=spread
export OMP_PLACES=cores
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export PYTHONUNBUFFERED=1

export SMB_REFERENCE_GATE=0

LOG_DIR="${LOG_DIR:-$REPO_ROOT/logs}"
ARTIFACT_DIR="${ARTIFACT_DIR:-$REPO_ROOT/artifacts/phase2_option_c_hifidelity}"
mkdir -p "$LOG_DIR" "$ARTIFACT_DIR"

echo "═══════════════════════════════════════════════════════════════════════════"
echo "PHASE 2 OPTION C: HIGHER FIDELITY (Most Robust)"
echo "═══════════════════════════════════════════════════════════════════════════"
echo "Job: ${SLURM_JOB_ID:-local}"
echo "CPUs: ${SLURM_CPUS_PER_TASK:-24} (12 workers × 2 threads)"
echo "Memory: 64G"
echo "Time: 28 hours (ample margin for 20-25 hour runtime)"
echo ""
echo "Configuration:"
echo "  Constraints: purity ≥ 0.15, recovery ≥ 0.15 (standard)"
echo "  Discretization: nfex=6, nfet=3, ncp=2 (MEDIUM fidelity)"
echo "  Expected feasibility: 50-70% at high quality"
echo "  Expected runtime: 20-25 hours (3-4 hours per NC)"
echo ""
echo "Purpose: Generate high-quality solutions by using finer discretization."
echo "Slower but captures solution details better."
echo ""

# Clean previous results
if [ -d "$ARTIFACT_DIR" ]; then
    echo "Clearing previous Phase 2 artifacts..."
    rm -rf "$ARTIFACT_DIR"
    mkdir -p "$ARTIFACT_DIR"
fi

echo "Running Phase 2 with HIGHER FIDELITY..."
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
  --timeout 180 \
  --n-workers 12 \
  --nfex 6 \
  --nfet 3 \
  --ncp 2 \
  --purity-min 0.15 \
  --recovery-min 0.15 \
  --verbose

EXIT_CODE=$?

echo ""
echo "═══════════════════════════════════════════════════════════════════════════"
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ PHASE 2 OPTION C (HIGH FIDELITY) COMPLETED SUCCESSFULLY"
else
    echo "❌ PHASE 2 OPTION C FAILED (exit code: $EXIT_CODE)"
fi
echo "═══════════════════════════════════════════════════════════════════════════"
echo ""
echo "Results:"
echo "  Artifacts: $ARTIFACT_DIR"
echo "  Summary: $ARTIFACT_DIR/phase2_summary.json"
echo ""

exit $EXIT_CODE
