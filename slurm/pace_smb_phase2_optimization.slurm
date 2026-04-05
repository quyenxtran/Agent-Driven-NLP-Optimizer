#!/bin/bash
# Phase 2: Optimization on Top NCs (Real Constrained Optimization)
# After Phase 1 smoke tests identify promising NCs, optimize flows for each
# Constraints: purity ≥ 0.70, recovery_GA ≥ 0.90, recovery_MA ≥ 0.90
# Objective: maximize productivity

#SBATCH --job-name=smb-phase2-opt
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
ARTIFACT_DIR="${ARTIFACT_DIR:-$REPO_ROOT/artifacts/phase2_optimization}"
mkdir -p "$LOG_DIR" "$ARTIFACT_DIR"

echo "═══════════════════════════════════════════════════════════════════════════"
echo "PHASE 2: CONSTRAINED OPTIMIZATION (Real Optima Finder)"
echo "═══════════════════════════════════════════════════════════════════════════"
echo "Job: ${SLURM_JOB_ID:-local}"
echo "CPUs: ${SLURM_CPUS_PER_TASK:-8} (MA97 multi-threaded)"
echo "Memory: 32G"
echo "Time: 60 minutes"
echo ""
echo "Purpose: Optimize flow variables for each NC under constraints"
echo "Constraints:"
echo "  - Purity (extract, MeOH-free) ≥ 0.70"
echo "  - Recovery (GA) ≥ 0.90"
echo "  - Recovery (MA) ≥ 0.90"
echo "  - Max pump flow ≤ 3.0 ml/min"
echo ""
echo "Objective: Maximize productivity (J)"
echo ""
echo "Data collection for BO surrogates:"
echo "  - Collects (NC, flows) → (productivity, purity, recovery)"
echo "  - BO models will fit on these outputs"
echo ""

# Top NCs from Phase 1 (will be populated after smoke tests)
# Evaluate top 5-10 NCs with real optimization
TOP_NCS=(
  "[1,1,2,4]"
  "[2,2,2,2]"
  "[1,1,3,3]"
  "[1,2,2,3]"
  "[2,1,2,3]"
  "[1,3,2,2]"
  "[3,1,2,2]"
  "[2,3,1,2]"
  "[3,2,1,2]"
  "[4,1,1,2]"
)

echo "Evaluating ${#TOP_NCS[@]} top-ranked NCs with optimization..."
echo ""

RESULTS_DIR="${ARTIFACT_DIR}/optimization_runs"
mkdir -p "$RESULTS_DIR"

for i in "${!TOP_NCS[@]}"; do
  NC="${TOP_NCS[$i]}"
  ITER=$((i + 1))

  echo "[Phase 2 Iter ${ITER}/${#TOP_NCS[@]}] Optimizing NC=$NC"

  "${REPO_ROOT}/.venv/bin/python" -m benchmarks.run_stage \
    --stage optimize-layouts \
    --run-name "phase2_opt_nc_${NC}" \
    --artifact-dir "$RESULTS_DIR" \
    --nc "$NC" \
    --solver-name "auto" \
    --linear-solver "ma97" \
    --nfex 6 \
    --nfet 3 \
    --ncp 2 \
    --purity-min 0.70 \
    --recovery-ga-min 0.90 \
    --recovery-ma-min 0.90 \
    --max-pump-flow 3.0 \
    --tee 2>&1 | tail -20

  echo ""
done

echo "═══════════════════════════════════════════════════════════════════════════"
echo "✅ PHASE 2 OPTIMIZATION COMPLETE"
echo "═══════════════════════════════════════════════════════════════════════════"
echo ""
echo "Results:"
echo "  Artifacts: $RESULTS_DIR"
echo "  Optimized flows for ${#TOP_NCS[@]} NC configurations"
echo "  Data ready for BO surrogate training:"
echo "    - Productivity"
echo "    - Purity"
echo "    - Recovery"
echo ""
echo "Next: Train BO surrogates (GP, DNN, PINN) on collected data"
echo ""

exit 0
