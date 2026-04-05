#!/bin/bash
# 27B BO+GP Baseline Benchmark (4 hours)
# Deterministic baseline without LLM - pure Bayesian Optimization
# For comparison against LHS + Agent and LHS + Agent approaches

#SBATCH --job-name=smb-qwen27b-bo-gp
#SBATCH -A gts-sn73
#SBATCH --qos=inferno
#SBATCH -p gpu-rtx6000
#SBATCH --gres=gpu:rtx_6000:1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=6
#SBATCH --mem=48G
#SBATCH --time=04:30:00
#SBATCH --mail-user=qtran47@gatech.edu
#SBATCH --mail-type=END,FAIL
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${SLURM_SUBMIT_DIR:-$SCRIPT_DIR}"
cd "$REPO_ROOT"

module load cuda/12.9.1 2>/dev/null || module load cuda/12.6.1 2>/dev/null || module load cuda/12.1.1 2>/dev/null || true
source .venv/bin/activate

export IPOPT_STACK_ROOT="${IPOPT_STACK_ROOT:-/storage/scratch1/4/qtran47/opt/ipopt-hsl-stack}"
export IPOPT_BIN_DIR="${IPOPT_BIN_DIR:-$IPOPT_STACK_ROOT/bin}"
export IPOPT_LIB_DIR="${IPOPT_LIB_DIR:-$IPOPT_STACK_ROOT/lib}"
export OPENBLAS_LIBDIR="${OPENBLAS_LIBDIR:-/usr/local/pace-apps/manual/packages/fenics/2018/linux-rhel9-cascadelake/gcc-9.4.0/openblas-0.3.28-cg7h4gbbmohnlrdesf4ykgipgza67why/lib}"
export METIS_LIBDIR="${METIS_LIBDIR:-/usr/local/pace-apps/manual/packages/fenics/2018/linux-rhel9-cascadelake/gcc-9.4.0/metis-5.1.0-hkeiflow76hhkltiep2ghivt3jagcryz/lib}"
export PATH="$IPOPT_BIN_DIR:${REPO_ROOT}/.venv/bin:${PATH}"
export LD_LIBRARY_PATH="$IPOPT_LIB_DIR:$OPENBLAS_LIBDIR:$METIS_LIBDIR:${LD_LIBRARY_PATH:-}"
export SMB_HSL_LIB="$IPOPT_LIB_DIR/libcoinhsl.so"

export OMP_NUM_THREADS="${OMP_NUM_THREADS:-${SLURM_CPUS_PER_TASK:-8}}"
export OMP_DYNAMIC=FALSE
export OMP_PROC_BIND=spread
export OMP_PLACES=cores
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export PYTHONUNBUFFERED=1

LOG_DIR="${LOG_DIR:-$REPO_ROOT/logs}"
ARTIFACT_DIR="${ARTIFACT_DIR:-$REPO_ROOT/artifacts/bo_gp_bench_27b}"
mkdir -p "$LOG_DIR" "$ARTIFACT_DIR"

echo "═══════════════════════════════════════════════════════════════════════════"
echo "BO+GP BASELINE: 27B Deterministic Optimization (4 hours)"
echo "═══════════════════════════════════════════════════════════════════════════"
echo "Job: ${SLURM_JOB_ID:-local}"
echo "GPU: RTX 6000"
echo "CPUs: ${SLURM_CPUS_PER_TASK:-8}"
echo "Time: 4 hours"
echo "Method: Bayesian Optimization + Gaussian Process"
echo "Config space: 31 valid (sum=8)"
echo ""
echo "Baseline for comparison against:"
echo "  - LHS + Agent (random)"
echo "  - LHS + Agent (physics-ranked)"
echo ""

echo "Running BO+GP baseline..."
"${REPO_ROOT}/.venv/bin/python" -m benchmarks.bo_gp_runner \
  --run-name "bo_gp_bench_27b" \
  --artifact-dir "$ARTIFACT_DIR" \
  --benchmark-hours 4.0 \
  --max-iterations 50 \
  --solver-name auto \
  --linear-solver ma97 \
  --verbose

EXIT_CODE=$?

echo ""
echo "═══════════════════════════════════════════════════════════════════════════"
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ BO+GP BASELINE COMPLETED SUCCESSFULLY"
else
    echo "❌ BO+GP BASELINE FAILED (exit code: $EXIT_CODE)"
fi
echo "═══════════════════════════════════════════════════════════════════════════"
echo ""
echo "Results:"
echo "  Artifacts: $ARTIFACT_DIR"
echo ""
echo "Comparison metrics:"
echo "  - Iterations completed"
echo "  - Best score found"
echo "  - Exploration coverage"
echo "  - Time efficiency"
echo ""

exit $EXIT_CODE
