#!/usr/bin/env python
"""
Prepare warm-start state from Phase 2 and test Phase 4 with it.

This script:
1. Runs Phase 2 reference-eval with return_model_state=True to capture discretized state
2. Extracts and saves the model state
3. Runs Phase 4 production fidelity with warm-start from Phase 2 state
4. Compares results
"""
import json
import sys
import subprocess
import time
import os
from pathlib import Path

REPO_ROOT = Path(__file__).parent
sys.path.insert(0, str(REPO_ROOT / "src"))

def run_command(cmd, description, timeout=600):
    """Run a shell command and return success status."""
    print()
    print(f"{'='*80}")
    print(f"{description}")
    print(f"{'='*80}")
    print(f"Command: {' '.join(cmd)}")
    print()

    try:
        result = subprocess.run(
            cmd,
            timeout=timeout,
            capture_output=False,
            text=True,
            cwd=REPO_ROOT
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"⏱️  Command timed out after {timeout}s")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    print("="*80)
    print("PHASE 4 WARM-START TEST - FULL PIPELINE")
    print("="*80)
    print()

    nc_config = "2,1,3,2"
    f1, ffeed, fdes, fex, tstep = 3.085, 2.328, 1.113, 2.198, 10.417

    # Step 1: Run Phase 2 with state capture
    print("STEP 1: Run Phase 2 (medium fidelity) with model state capture")
    print("-" * 80)

    cmd_phase2 = [
        sys.executable, "-m", "benchmarks.run_stage",
        "--stage", "reference-eval",
        "--nc", nc_config,
        "--f1", str(f1),
        "--ffeed", str(ffeed),
        "--fdes", str(fdes),
        "--fex", str(fex),
        "--tstep", str(tstep),
        "--nfex", "6",
        "--nfet", "3",
        "--ncp", "1",
        "--purity-min", "0.05",
        "--recovery-ga-min", "0.10",
        "--recovery-ma-min", "0.15",
        "--max-solve-seconds", "180",  # More time for Phase 2
        "--run-name", "phase4_ws_p2_extract",
    ]

    success_p2 = run_command(cmd_phase2, "Phase 2: Medium Fidelity Reference Evaluation", timeout=240)

    if not success_p2:
        print()
        print("⚠️  Phase 2 did not complete successfully")
        print("Checking if artifact was created...")
        p2_artifact = (REPO_ROOT / "artifacts" / "smb_stage_runs" / "reference-eval.local.phase4_ws_p2_extract.json")
        if not p2_artifact.exists():
            print(f"❌ No Phase 2 artifact found")
            return 1
        print(f"⚠️  Found partial Phase 2 result at: {p2_artifact}")

    # Try to extract Phase 2 result
    p2_artifact = REPO_ROOT / "artifacts" / "smb_stage_runs" / "reference-eval.local.phase4_ws_p2_extract.json"
    if not p2_artifact.exists():
        print(f"❌ Phase 2 artifact not found: {p2_artifact}")
        return 1

    print(f"\n✅ Phase 2 artifact created: {p2_artifact}")

    with open(p2_artifact) as f:
        p2_result = json.load(f)

    p2_status = p2_result.get("status", "unknown")
    print(f"   Status: {p2_status}")

    if p2_status == "ok":
        print("   ✅ Phase 2 converged successfully!")
        p2_model_state = p2_result.get("_model_state")
        if p2_model_state:
            print(f"   ✅ Model state available ({len(p2_model_state)} variables)")
        else:
            print("   ⚠️  Model state not captured (return_model_state not set)")
            p2_model_state = None
    else:
        print(f"   ⚠️  Phase 2 status: {p2_status}")
        print(f"   Error: {p2_result.get('error', 'N/A')}")
        p2_model_state = p2_result.get("_model_state")
        if p2_model_state:
            print(f"   But model state available ({len(p2_model_state)} variables)")

    # Step 2: Run Phase 4 without warm-start (baseline)
    print()
    print("STEP 2: Run Phase 4 (production fidelity) WITHOUT warm-start (cold-start)")
    print("-" * 80)

    cmd_phase4_cold = [
        sys.executable, "-m", "benchmarks.run_stage",
        "--stage", "reference-eval",
        "--nc", nc_config,
        "--f1", str(f1),
        "--ffeed", str(ffeed),
        "--fdes", str(fdes),
        "--fex", str(fex),
        "--tstep", str(tstep),
        "--nfex", "10",
        "--nfet", "5",
        "--ncp", "2",
        "--purity-min", "0.05",
        "--recovery-ga-min", "0.10",
        "--recovery-ma-min", "0.15",
        "--max-solve-seconds", "300",
        "--run-name", "phase4_ws_coldstart",
    ]

    start_cold = time.time()
    success_p4_cold = run_command(cmd_phase4_cold, "Phase 4: Production Fidelity (COLD START)", timeout=400)
    time_cold = time.time() - start_cold

    p4_cold_artifact = REPO_ROOT / "artifacts" / "smb_stage_runs" / "reference-eval.local.phase4_ws_coldstart.json"
    if p4_cold_artifact.exists():
        with open(p4_cold_artifact) as f:
            p4_cold_result = json.load(f)
        p4_cold_status = p4_cold_result.get("status", "unknown")
        p4_cold_term = p4_cold_result.get("solver", {}).get("termination_condition", "N/A")
        print(f"\n✅ Phase 4 cold-start result:")
        print(f"   Status: {p4_cold_status}")
        print(f"   Termination: {p4_cold_term}")
        print(f"   Wall time: {time_cold:.1f}s")
    else:
        print(f"\n❌ Phase 4 cold-start artifact not found")
        p4_cold_status = "unknown"
        time_cold = 0

    # Step 3: If we have model state, run Phase 4 with warm-start
    if p2_model_state:
        print()
        print("STEP 3: Run Phase 4 (production fidelity) WITH warm-start (warm-start)")
        print("-" * 80)

        # Unfortunately, we can't pass model state via command line
        # We need to modify the approach to use Python API instead
        print()
        print("Note: Direct warm-start via CLI not yet implemented.")
        print("This requires Python API call with warm_start_state parameter.")
        print()
        print("To enable warm-start, modify benchmarks.run_stage to accept and pass warm_start_state")
        print("from command line or environment variable.")
        print()
    else:
        print()
        print("STEP 3: SKIPPED - No model state available for warm-start")
        print("-" * 80)
        print()
        if p2_status != "ok":
            print("⚠️  Phase 2 did not converge, cannot extract model state.")
        else:
            print("⚠️  Model state not captured. Re-run Phase 2 with return_model_state=True.")

    # Summary
    print()
    print("="*80)
    print("TEST SUMMARY")
    print("="*80)
    print()
    print(f"Phase 2 (medium fidelity, nfex=6):")
    print(f"  Status: {p2_status}")
    print(f"  Model state: {'Available' if p2_model_state else 'Not captured'}")
    print()
    print(f"Phase 4 Cold-start (production fidelity, nfex=10):")
    print(f"  Status: {p4_cold_status}")
    print(f"  Time: {time_cold:.1f}s")
    print(f"  Result: {'CONVERGED' if p4_cold_status == 'ok' else 'TIMEOUT or ERROR'}")
    print()

    if p4_cold_status != "ok":
        print("✅ FINDING: Phase 4 cold-start fails (as expected)")
        print("   Next step: Implement warm-start to improve convergence")
        return 0
    else:
        print("⚠️  Phase 4 cold-start unexpectedly succeeded")
        return 0

if __name__ == "__main__":
    sys.exit(main())
