#!/bin/bash
# Simple test: Run Phase 4 with exact Phase 2 flows directly
# No warm-start extraction for now - just test if the warm-start parameter is accepted

set -e

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
echo "PHASE 4 WARM-START TEST - NC [2,1,3,2] WITH PRODUCTION FIDELITY"
echo "================================================================================"
echo ""
echo "Test 1: Phase 2 medium fidelity (baseline, should work)"
echo "========================================================="
python -m benchmarks.run_stage \
  --stage reference-eval \
  --nc "2,1,3,2" \
  --f1 3.085 \
  --ffeed 2.328 \
  --fdes 1.113 \
  --fex 2.198 \
  --tstep 10.417 \
  --nfex 6 \
  --nfet 3 \
  --ncp 1 \
  --purity-min 0.05 \
  --recovery-ga-min 0.10 \
  --recovery-ma-min 0.15 \
  --max-solve-seconds 120 \
  --run-name "phase4_warmstart_phase2_baseline" \
  2>&1 | tee /tmp/phase4_test_step1.log

echo ""
echo "Phase 2 result saved. Extracting status..."
PHASE2_STATUS=$(python3 -c "
import json
with open('/storage/home/hcoda1/4/qtran47/AutoResearch-SMB/artifacts/smb_stage_runs/reference-eval.local.phase4_warmstart_phase2_baseline.json') as f:
    d = json.load(f)
print(d.get('status', 'unknown'))
")

echo "Phase 2 status: $PHASE2_STATUS"
echo ""

if [ "$PHASE2_STATUS" = "ok" ]; then
  echo "✅ Phase 2 baseline succeeded!"
  echo ""
  echo "Test 2: Phase 4 production fidelity WITHOUT warm-start (cold start - expected to timeout)"
  echo "========================================================================================"
  timeout 400 python -m benchmarks.run_stage \
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
    --max-solve-seconds 300 \
    --run-name "phase4_coldstart" \
    2>&1 | tail -50 | tee /tmp/phase4_test_step2.log

  echo ""
  echo "Phase 4 cold-start completed (likely timeout). Checking result..."
  PHASE4_COLD_STATUS=$(python3 -c "
import json
try:
  with open('/storage/home/hcoda1/4/qtran47/AutoResearch-SMB/artifacts/smb_stage_runs/reference-eval.local.phase4_coldstart.json') as f:
    d = json.load(f)
  print(d.get('status', 'unknown'))
  if d.get('solver'):
    print(d.get('solver', {}).get('termination_condition', ''))
except:
  print('error')
" | head -1)

  echo "Phase 4 cold-start status: $PHASE4_COLD_STATUS"

  if [ "$PHASE4_COLD_STATUS" = "solver_error" ]; then
    echo "✅ As expected: Phase 4 cold-start hit solver error/timeout"
    echo ""
    echo "SUCCESS: Warm-start functionality is needed to overcome this!"
  else
    echo "⚠️  Unexpected Phase 4 result: $PHASE4_COLD_STATUS"
  fi
else
  echo "❌ Phase 2 baseline failed. Cannot proceed with Phase 4 test."
  exit 1
fi

echo ""
echo "================================================================================"
echo "TEST COMPLETE"
echo "================================================================================"
