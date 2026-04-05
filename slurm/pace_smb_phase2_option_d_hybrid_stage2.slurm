#!/bin/bash
# Phase 2 Option D (Stage 2): Hybrid Two-Stage - Higher Fidelity Refinement
# Objective: Refine Stage 1 results with higher fidelity and tighter constraints
#
# Prerequisites: Stage 1 must complete first
#  sbatch slurm/pace_smb_phase2_option_d_hybrid_stage1.slurm
#
# Stage 2 (this job): Refine promising regions at higher quality
#  - Uses stage1 results as baseline
#  - Increases fidelity: nfex 4→6, nfet 2→3, ncp 1→2
#  - Applies standard constraints: purity ≥ 0.15, recovery ≥ 0.15
#  - Expected feasibility: 60-75% at high quality
#  - Runtime: 12-15 hours
#
# Total time (Stage 1 + Stage 2): ~20 hours for publication-quality data
# Total cost: Same as Option C but with better feasibility region identification

#SBATCH --job-name=smb-phase2-opt-d-stage2
#SBATCH -A gts-sn73
#SBATCH --qos=inferno
#SBATCH -p cpu-container
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=24
#SBATCH --mem=64G
#SBATCH --time=18:00:00
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
ARTIFACT_DIR="${ARTIFACT_DIR:-$REPO_ROOT/artifacts/phase2_option_d_hybrid}"
mkdir -p "$LOG_DIR" "$ARTIFACT_DIR"

echo "═══════════════════════════════════════════════════════════════════════════"
echo "PHASE 2 OPTION D (STAGE 2): Hybrid Two-Stage - High Fidelity Refinement"
echo "═══════════════════════════════════════════════════════════════════════════"
echo "Job: ${SLURM_JOB_ID:-local}"
echo "CPUs: ${SLURM_CPUS_PER_TASK:-24} (12 workers × 2 threads)"
echo "Memory: 64G"
echo "Time: 18 hours"
echo ""
echo "Stage 2 Configuration:"
echo "  Purpose: Refine Stage 1 results with higher fidelity"
echo "  Constraints: purity ≥ 0.15, recovery ≥ 0.15 (STANDARD)"
echo "  Discretization: nfex=6, nfet=3, ncp=2 (MEDIUM fidelity)"
echo "  Expected feasibility: 60-75% at high quality"
echo "  Expected runtime: 12-15 hours"
echo ""
echo "Comparison to other options:"
echo "  Option B: 7-8 hours, low fidelity, 60-80% feasibility"
echo "  Option C: 20-25 hours, high fidelity, 50-70% feasibility"
echo "  Option D: 20 hours total, BOTH low + high fidelity, 60-75% quality"
echo ""
echo "Stage 1 artifacts (as baseline): $ARTIFACT_DIR"
echo ""

echo "Running Phase 2 Stage 2: HIGH FIDELITY REFINEMENT..."
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
    echo "✅ PHASE 2 OPTION D STAGE 2 COMPLETED SUCCESSFULLY"
    echo ""
    echo "HYBRID APPROACH COMPLETE!"
    echo ""
    echo "Summary:"
    echo "  Stage 1: Quick scan (5-6h) identified feasible regions"
    echo "  Stage 2: High-fidelity refinement (12-15h) optimized solutions"
    echo "  Total: ~20 hours for publication-quality results"
    echo ""
    echo "Results:"
    echo "  Artifacts: $ARTIFACT_DIR"
    echo "  Summary: $ARTIFACT_DIR/phase2_summary.json"
    echo ""
    echo "READY FOR PHASE 3: Comparative strategy evaluation"
else
    echo "❌ PHASE 2 OPTION D STAGE 2 FAILED (exit code: $EXIT_CODE)"
fi
echo "═══════════════════════════════════════════════════════════════════════════"
echo ""

exit $EXIT_CODE
