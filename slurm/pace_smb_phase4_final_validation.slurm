#!/bin/bash
#SBATCH --job-name=phase4_final_ma97
#SBATCH -A gts-sn73
#SBATCH --qos=inferno
#SBATCH -p cpu-small
#SBATCH --time=01:00:00
#SBATCH --nodes=1
#SBATCH --cpus-per-task=24
#SBATCH --mem=32G
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err

set -e

# Setup environment
export IPOPT_STACK_ROOT="/storage/scratch1/4/qtran47/opt/ipopt-hsl-stack"
export IPOPT_BIN_DIR="$IPOPT_STACK_ROOT/bin"
export IPOPT_LIB_DIR="$IPOPT_STACK_ROOT/lib"
export OPENBLAS_LIBDIR="/usr/local/pace-apps/manual/packages/fenics/2018/linux-rhel9-cascadelake/gcc-9.4.0/openblas-0.3.28-cg7h4gbbmohnlrdesf4ykgipgza67why/lib"
export METIS_LIBDIR="/usr/local/pace-apps/manual/packages/fenics/2018/linux-rhel9-cascadelake/gcc-9.4.0/metis-5.1.0-hkeiflow76hhkltiep2ghivt3jagcryz/lib"
export PATH="$IPOPT_BIN_DIR:${PATH}"
export LD_LIBRARY_PATH="$IPOPT_LIB_DIR:$OPENBLAS_LIBDIR:$METIS_LIBDIR:${LD_LIBRARY_PATH:-}"
export OMP_NUM_THREADS=2
export PYTHONUNBUFFERED=1

cd /storage/home/hcoda1/4/qtran47/AutoResearch-SMB
source .venv/bin/activate

echo "================================================================================"
echo "PHASE 4 FINAL VALIDATION - PRODUCTION FIDELITY"
echo "================================================================================"
echo "Date: $(date)"
echo "Host: $(hostname)"
echo "CPUs: $SLURM_CPUS_PER_TASK"
echo "Memory: $SLURM_MEM_PER_NODE"
echo ""
echo "Configuration:"
echo "  NC: [2,1,3,2]"
echo "  Flows: Phase 2 reference (F1=3.085, Ffeed=2.328, Fdes=1.113, Fex=2.198, tstep=10.417)"
echo "  Fidelity: Production (nfex=10, nfet=5, ncp=2)"
echo "  Linear Solver: MA97 (sparse, efficient)"
echo "  Time Limit: 1800 seconds (30 min)"
echo ""

python -m benchmarks.run_stage \
  --stage reference-eval \
  --nc "2,1,3,2" \
  --f1 3.085 \
  --ffeed 2.328 \
  --fdes 1.113 \
  --fex 2.198 \
  --tstep 10.417 \
  --nfex 10 \
  --nfet 5 \
  --ncp 2 \
  --purity-min 0.05 \
  --recovery-ga-min 0.10 \
  --recovery-ma-min 0.15 \
  --max-solve-seconds 1800 \
  --linear-solver ma97 \
  --run-name "phase4_slurm_ma97_final" \
  --no-reference-gate

echo ""
echo "================================================================================"
echo "PHASE 4 COMPLETED"
echo "================================================================================"

# Extract and display results
python3 << 'PYEOF'
import json
from pathlib import Path

artifact = Path("artifacts/smb_stage_runs/reference-eval.local.phase4_slurm_ma97_final.json")

if artifact.exists():
    with open(artifact) as f:
        d = json.load(f)

    print()
    print("RESULTS:")
    print("-" * 80)

    if d.get('status') == 'ok':
        m = d.get('metrics', {})
        timing = d.get('timing', {})

        print(f"✅ STATUS: CONVERGED")
        print()
        print("Performance Metrics (Production Fidelity):")
        print(f"  Purity (MeOH-free): {m.get('purity_ex_meoh_free', 0):.6f}")
        print(f"  Recovery GA: {m.get('recovery_ex_GA', 0):.6f}")
        print(f"  Recovery MA: {m.get('recovery_ex_MA', 0):.6f}")
        print(f"  Productivity: {m.get('productivity_ex_ga_ma', 0):.6f}")
        print()
        print("Constraint Check:")
        print(f"  Purity ≥ 0.05: {'✅' if m.get('purity_ex_meoh_free', 0) >= 0.05 else '❌'}")
        print(f"  Recovery GA ≥ 0.10: {'✅' if m.get('recovery_ex_GA', 0) >= 0.10 else '❌'}")
        print(f"  Recovery MA ≥ 0.15: {'✅' if m.get('recovery_ex_MA', 0) >= 0.15 else '❌'}")
        print()
        print(f"Wall Time: {timing.get('wall_seconds', 0):.1f} seconds")
    else:
        print(f"❌ STATUS: {d.get('status')}")
        solver = d.get('solver', {})
        print(f"   Termination: {solver.get('termination_condition')}")
        print(f"   Error: {d.get('error')}")
        timing = d.get('timing', {})
        print(f"   Wall Time: {timing.get('wall_seconds', 0):.1f} seconds")

        # Check for provisional metrics
        if d.get('provisional', {}).get('metrics'):
            print()
            print("⚠️  Provisional metrics (infeasible solution):")
            m = d.get('provisional', {}).get('metrics', {})
            print(f"  Purity: {m.get('purity_ex_meoh_free', 0):.6f}")
            print(f"  Recovery GA: {m.get('recovery_ex_GA', 0):.6f}")
            print(f"  Recovery MA: {m.get('recovery_ex_MA', 0):.6f}")
else:
    print("❌ Artifact not found")
PYEOF
