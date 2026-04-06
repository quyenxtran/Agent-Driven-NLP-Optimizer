#!/bin/bash
# Phase 3 Strategy 1: Regular LHS
# Baseline: select top 5 → one high-fidelity run each → multi-start on finalist
# Expected: Lowest best J (baseline for comparison)

#SBATCH --job-name=smb-phase3-s1
#SBATCH -A gts-sn73
#SBATCH --qos=inferno
#SBATCH -p cpu-container
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=04:00:00
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

export OMP_NUM_THREADS="${OMP_NUM_THREADS:-${SLURM_CPUS_PER_TASK:-8}}"
export OMP_DYNAMIC=FALSE
export OMP_PROC_BIND=spread
export OMP_PLACES=cores
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export PYTHONUNBUFFERED=1
export SMB_REFERENCE_GATE=0

LOG_DIR="${LOG_DIR:-$REPO_ROOT/logs}"
ARTIFACT_DIR="${ARTIFACT_DIR:-$REPO_ROOT/artifacts/phase3_strategy1}"
mkdir -p "$LOG_DIR" "$ARTIFACT_DIR"

echo "═══════════════════════════════════════════════════════════════════════════"
echo "PHASE 3 STRATEGY 1: Regular LHS (Baseline)"
echo "═══════════════════════════════════════════════════════════════════════════"
echo ""
echo "Approach:"
echo "  1. Load Phase 2B screening data (~300-350 feasible seeds)"
echo "  2. Rank all NCs by screening productivity"
echo "  3. Select top 5 DISTINCT NCs"
echo "  4. Run one HIGH-fidelity optimization for each selected NC"
echo "  5. Promote the single best NC"
echo "  6. Run 3 multi-start high-fidelity validations on that finalist"
echo ""
echo "Purpose: Baseline (no intelligence) for comparison"
echo ""

echo "Running Phase 3 Strategy 1..."
"${REPO_ROOT}/.venv/bin/python" -m benchmarks.phase3_strategy1_regular_lhs \
  --phase2-dir "$REPO_ROOT/artifacts/phase2_lhs_seeding" \
  --artifact-dir "$ARTIFACT_DIR"

EXIT_CODE=$?

echo ""
echo "═══════════════════════════════════════════════════════════════════════════"
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ PHASE 3 STRATEGY 1 COMPLETED"
else
    echo "❌ PHASE 3 STRATEGY 1 FAILED (exit code: $EXIT_CODE)"
fi
echo "═══════════════════════════════════════════════════════════════════════════"
echo ""
echo "Result: $ARTIFACT_DIR/strategy1_result.json"
echo ""

exit $EXIT_CODE
