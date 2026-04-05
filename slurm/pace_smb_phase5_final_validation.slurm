#!/bin/bash
# Phase 5: Final Validation (Strict Constraints)
# After Phase 1-4 exploration with loose constraints,
# validate best candidates with STRICT production constraints

#SBATCH --job-name=smb-phase5-valid
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
ARTIFACT_DIR="${ARTIFACT_DIR:-$REPO_ROOT/artifacts/phase5_final_validation}"
mkdir -p "$LOG_DIR" "$ARTIFACT_DIR"

echo "═══════════════════════════════════════════════════════════════════════════"
echo "PHASE 5: FINAL VALIDATION (Strict Production Constraints)"
echo "═══════════════════════════════════════════════════════════════════════════"
echo "Job: ${SLURM_JOB_ID:-local}"
echo "CPUs: ${SLURM_CPUS_PER_TASK:-8} (MA97 multi-threaded)"
echo "Memory: 32G"
echo "Time: 60 minutes"
echo ""
echo "Purpose: Validate Phase 4 best candidates with STRICT constraints"
echo "This is the final filter for true global optimum"
echo ""
echo "STRICT PRODUCTION Constraints:"
echo "  - Purity (extract, MeOH-free) ≥ 0.70"
echo "  - Recovery (GA) ≥ 0.90"
echo "  - Recovery (MA) ≥ 0.90"
echo "  - Max pump flow ≤ 3.0 ml/min"
echo ""
echo "Process:"
echo "  1. Extract best NC from Phase 4 (agent optimization)"
echo "  2. Run optimization with STRICT constraints"
echo "  3. Compare vs Phase 4 result (loose constraints)"
echo "  4. Report global optimum"
echo ""

# Top candidates from Phase 4 (to be populated after agent exploration)
# After Phase 4, extract best NC and flow settings
TOP_CANDIDATES=(
  "[2,2,2,2]"
  "[1,2,2,3]"
  "[2,1,2,3]"
)

echo "Validating ${#TOP_CANDIDATES[@]} best candidates under STRICT constraints..."
echo ""

RESULTS_DIR="${ARTIFACT_DIR}/strict_validation_runs"
mkdir -p "$RESULTS_DIR"

for i in "${!TOP_CANDIDATES[@]}"; do
  NC="${TOP_CANDIDATES[$i]}"
  ITER=$((i + 1))

  echo "[Phase 5 Iter ${ITER}/${#TOP_CANDIDATES[@]}] STRICT validation of NC=$NC"

  "${REPO_ROOT}/.venv/bin/python" -m benchmarks.run_stage \
    --stage optimize-layouts \
    --run-name "phase5_strict_valid_nc_${NC}" \
    --artifact-dir "$RESULTS_DIR" \
    --nc "$NC" \
    --solver-name "auto" \
    --linear-solver "ma97" \
    --nfex 10 \
    --nfet 5 \
    --ncp 2 \
    --purity-min 0.70 \
    --recovery-ga-min 0.90 \
    --recovery-ma-min 0.90 \
    --max-pump-flow 3.0 \
    --tee 2>&1 | tail -20

  echo ""
done

echo "═══════════════════════════════════════════════════════════════════════════"
echo "✅ PHASE 5 FINAL VALIDATION COMPLETE"
echo "═══════════════════════════════════════════════════════════════════════════"
echo ""
echo "Results:"
echo "  Artifacts: $RESULTS_DIR"
echo "  Validated ${#TOP_CANDIDATES[@]} candidates with STRICT constraints"
echo "  Fidelity: HIGH (nfex=10, nfet=5, ncp=2)"
echo ""
echo "Global Optimum: Best result under STRICT constraints"
echo "  (compare Phase 4 loose-constraint optimum vs Phase 5 strict validation)"
echo ""
echo "Summary:"
echo "  Phase 1: Baseline eval at fixed flows (loose)"
echo "  Phase 2: Optimization with loose constraints"
echo "  Phase 3: BO surrogates trained on loose data"
echo "  Phase 4: Agent exploration with loose constraints"
echo "  Phase 5: FINAL strict-constraint validation ← YOU ARE HERE"
echo ""

exit 0
