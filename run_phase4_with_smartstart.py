#!/usr/bin/env python
"""
Run Phase 4 with "smart start" - initialize from Phase 2 flows using reference profiles.

Instead of trying to extract full model state, this uses a simpler approach:
1. Loads Phase 2 reference solution flows
2. Initializes solver with those flows (which IPOPT can use as good starting point)
3. Runs Phase 4 with these better initial conditions

This is still more efficient than cold-start because the flows are good starting points.
"""
import json
import sys
import subprocess
from pathlib import Path

def main():
    """Test Phase 4 using Phase 2 reference flows."""
    REPO_ROOT = Path(__file__).parent

    print("="*80)
    print("PHASE 4 WITH SMART START - Using Phase 2 Reference Flows")
    print("="*80)
    print()

    # Load Phase 2 best solution for NC [2,1,3,2]
    print("Step 1: Load Phase 2 reference solution")
    print("-" * 80)

    p2_summary = REPO_ROOT / "artifacts" / "phase2_lhs_seeding" / "phase2_reference_summary_corrected.json"
    with open(p2_summary) as f:
        data = json.load(f)

    # Find NC [2,1,3,2]
    nc_result = None
    for r in data["results"]:
        if r.get("nc") == [2, 1, 3, 2]:
            nc_result = r
            break

    if not nc_result or not nc_result.get("best_seed"):
        print("❌ ERROR: Could not find Phase 2 result for NC [2,1,3,2]")
        return 1

    best_seed = nc_result["best_seed"]
    flows = best_seed["flows"]

    print(f"✅ Found Phase 2 solution:")
    print(f"   Flows: F1={flows['F1']:.4f}, Ffeed={flows['Ffeed']:.4f}, "
          f"Fdes={flows['Fdes']:.4f}, Fex={flows['Fex']:.4f}, tstep={flows['tstep']:.4f}")
    print(f"   Purity: {best_seed['purity']:.4f}")
    print(f"   Recovery GA: {best_seed['recovery_GA']:.4f}")
    print(f"   Recovery MA: {best_seed['recovery_MA']:.4f}")
    print(f"   Productivity: {best_seed['productivity']:.6f}")
    print()

    # Step 2: Run Phase 4 with Phase 2 flows
    print("Step 2: Run Phase 4 production fidelity with Phase 2 flows")
    print("-" * 80)
    print()

    cmd = [
        sys.executable, "-m", "benchmarks.run_stage",
        "--stage", "reference-eval",
        "--nc", "2,1,3,2",
        "--f1", str(flows["F1"]),
        "--ffeed", str(flows["Ffeed"]),
        "--fdes", str(flows["Fdes"]),
        "--fex", str(flows["Fex"]),
        "--tstep", str(flows["tstep"]),
        "--nfex", "10",
        "--nfet", "5",
        "--ncp", "2",
        "--purity-min", "0.05",
        "--recovery-ga-min", "0.10",
        "--recovery-ma-min", "0.15",
        "--max-solve-seconds", "300",
        "--run-name", "phase4_smartstart_test",
        "--no-reference-gate",  # Skip preliminary evals to save time
    ]

    print("Running Phase 4 production fidelity...")
    result = subprocess.run(cmd, cwd=REPO_ROOT)

    if result.returncode != 0:
        print("⚠️  Phase 4 execution reported non-zero exit")

    # Step 3: Check results
    print()
    print("Step 3: Analyze Phase 4 results")
    print("-" * 80)

    p4_artifact = (REPO_ROOT / "artifacts" / "smb_stage_runs" /
                   "reference-eval.local.phase4_smartstart_test.json")

    if not p4_artifact.exists():
        print(f"❌ Phase 4 artifact not found: {p4_artifact}")
        return 1

    with open(p4_artifact) as f:
        p4_result = json.load(f)

    print()
    print("="*80)
    print("PHASE 4 SMART-START RESULTS")
    print("="*80)
    print()

    status = p4_result.get("status", "unknown")
    print(f"Status: {status}")

    if status == "ok":
        print()
        print("✅ SOLVER CONVERGED AT PRODUCTION FIDELITY!")
        print()

        metrics = p4_result.get("metrics", {})
        print("Performance Metrics:")
        print(f"  Purity (MeOH-free): {metrics.get('purity_ex_meoh_free', 0):.4f}")
        print(f"  Recovery GA: {metrics.get('recovery_ex_GA', 0):.4f}")
        print(f"  Recovery MA: {metrics.get('recovery_ex_MA', 0):.4f}")
        print(f"  Productivity: {metrics.get('productivity_ex_ga_ma', 0):.6f}")

        # Check feasibility
        purity_ok = metrics.get('purity_ex_meoh_free', 0) >= 0.05
        rec_ga_ok = metrics.get('recovery_ex_GA', 0) >= 0.10
        rec_ma_ok = metrics.get('recovery_ex_MA', 0) >= 0.15

        print()
        print("Constraint Check:")
        print(f"  Purity ≥ 0.05: {'✅' if purity_ok else '❌'}")
        print(f"  Recovery GA ≥ 0.10: {'✅' if rec_ga_ok else '❌'}")
        print(f"  Recovery MA ≥ 0.15: {'✅' if rec_ma_ok else '❌'}")

        if purity_ok and rec_ga_ok and rec_ma_ok:
            print()
            print("🏆 ALL CONSTRAINTS SATISFIED AT PRODUCTION FIDELITY!")
            return 0
        else:
            print()
            print("⚠️  Some constraints not met, but solver converged")
            return 0
    else:
        print()
        print(f"❌ Solver error: {p4_result.get('error', 'N/A')}")

        solver_info = p4_result.get("solver", {})
        term_cond = solver_info.get("termination_condition", "N/A")
        message = solver_info.get("message", "")

        print(f"   Termination: {term_cond}")
        if message:
            print(f"   Message: {message}")

        # Check if we have provisional results
        prov = p4_result.get("provisional", {})
        if prov.get("metrics"):
            print()
            print("⚠️  Partial solution available (infeasible_last_iterate):")
            metrics = prov.get("metrics", {})
            print(f"    Purity: {metrics.get('purity_ex_meoh_free', 0):.4f}")
            print(f"    Recovery GA: {metrics.get('recovery_ex_GA', 0):.4f}")
            print(f"    Recovery MA: {metrics.get('recovery_ex_MA', 0):.4f}")

        return 1

if __name__ == "__main__":
    sys.exit(main())
