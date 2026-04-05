#!/bin/bash
# BO+GP with Real IPOPT - Low Fidelity Smoke Test (30 min)
# Bayesian Optimization with GP and real IPOPT evaluation
# Tests refactored bo_gp_runner.py with actual solver

#SBATCH --job-name=smb-bo-gp-real
#SBATCH -A gts-sn73
#SBATCH --qos=inferno
#SBATCH -p cpu-container
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=00:40:00
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
ARTIFACT_DIR="${ARTIFACT_DIR:-$REPO_ROOT/artifacts/bo_gp_real_ipopt_smoke}"
mkdir -p "$LOG_DIR" "$ARTIFACT_DIR"

echo "═══════════════════════════════════════════════════════════════════════════"
echo "BO+GP WITH REAL IPOPT: Low Fidelity Smoke Test (30 min)"
echo "═══════════════════════════════════════════════════════════════════════════"
echo "Job: ${SLURM_JOB_ID:-local}"
echo "CPUs: ${SLURM_CPUS_PER_TASK:-8} (MA97 multi-threaded)"
echo "Memory: 32G"
echo "Time: 30 minutes"
echo "Method: Bayesian Optimization + Gaussian Process + real IPOPT"
echo "Fidelity: Low (nfex=5, nfet=2, ncp=1)"
echo "Config space: 31 valid (sum=8)"
echo ""
echo "Running BO+GP with real IPOPT smoke test..."

"${REPO_ROOT}/.venv/bin/python" -m benchmarks.bo_gp_runner \
  --run-name "bo_gp_real_ipopt_smoke" \
  --artifact-dir "$ARTIFACT_DIR" \
  --benchmark-hours 0.5 \
  --max-iterations 15 \
  --solver-name "auto" \
  --linear-solver "ma97" \
  --nfex 5 \
  --nfet 2 \
  --ncp 1 \
  --verbose

EXIT_CODE=$?

echo ""
echo "═══════════════════════════════════════════════════════════════════════════"
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ BO+GP REAL IPOPT SMOKE TEST COMPLETED SUCCESSFULLY"
else
    echo "❌ BO+GP REAL IPOPT SMOKE TEST FAILED (exit code: $EXIT_CODE)"
fi
echo "═══════════════════════════════════════════════════════════════════════════"
echo ""
echo "Results:"
echo "  Artifacts: $ARTIFACT_DIR"
echo "  Evaluated up to 15 configs with real IPOPT optimization"
echo ""

exit $EXIT_CODE
