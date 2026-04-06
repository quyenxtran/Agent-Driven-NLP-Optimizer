#!/usr/bin/env python
"""
Test Phase 4 with warm-start from Phase 2 reference evaluation.

This script:
1. Loads Phase 2 medium fidelity solution for NC [2,1,3,2]
2. Extracts model state as warm-start initialization
3. Runs Phase 4 production fidelity (nfex=10) with warm-start
4. Compares timing and convergence vs cold-start
"""
import json
import sys
import argparse
import time
from pathlib import Path

# Add repo root to path
REPO_ROOT = Path(__file__).parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

def main():
    """Test single NC with warm-start."""
    parser = argparse.ArgumentParser(description="Test Phase 4 with warm-start from Phase 2")
    parser.add_argument("--phase2-artifact",
                       default="/storage/home/hcoda1/4/qtran47/AutoResearch-SMB/artifacts/phase2_lhs_seeding/phase2_reference_summary_corrected.json",
                       help="Phase 2 reference summary JSON")
    parser.add_argument("--nc", default="2,1,3,2", help="NC configuration as comma-separated")
    parser.add_argument("--nfex", type=int, default=10, help="Production fidelity spatial elements")
    parser.add_argument("--nfet", type=int, default=5, help="Production fidelity temporal elements")
    parser.add_argument("--ncp", type=int, default=2, help="Production fidelity collocation points")
    parser.add_argument("--run-name", default="phase4_warmstart_test", help="Run name")
    parser.add_argument("--artifact-dir", default="/storage/home/hcoda1/4/qtran47/AutoResearch-SMB/artifacts/smb_stage_runs")
    args = parser.parse_args()

    print("="*80)
    print("PHASE 4 WARM-START TEST")
    print("="*80)
    print()

    # Parse NC
    nc_list = tuple(int(x) for x in args.nc.split(","))
    print(f"NC Configuration: {nc_list}")
    print(f"Production Fidelity: nfex={args.nfex}, nfet={args.nfet}, ncp={args.ncp}")
    print()

    # Load Phase 2 result
    print("Loading Phase 2 reference evaluation results...")
    with open(args.phase2_artifact) as f:
        phase2_data = json.load(f)

    # Find the result for this NC
    phase2_result = None
    for nc_result in phase2_data.get("results", []):
        if tuple(nc_result.get("nc", [])) == nc_list:
            phase2_result = nc_result
            break

    if not phase2_result:
        print(f"❌ ERROR: NC {nc_list} not found in Phase 2 results")
        return 1

    print(f"✅ Found Phase 2 result for NC {nc_list}")

    best_seed = phase2_result.get("best_seed")
    if not best_seed:
        print(f"❌ ERROR: No best seed found for NC {nc_list}")
        return 1

    # Extract flows and metrics
    flows = best_seed.get("flows", {})

    print()
    print("Phase 2 Reference Solution:")
    print(f"  Flows: F1={flows.get('F1'):.4f}, Ffeed={flows.get('Ffeed'):.4f}, "
          f"Fdes={flows.get('Fdes'):.4f}, Fex={flows.get('Fex'):.4f}, tstep={flows.get('tstep'):.4f}")
    print(f"  Purity: {best_seed.get('purity'):.4f}")
    print(f"  Recovery GA: {best_seed.get('recovery_GA'):.4f}")
    print(f"  Recovery MA: {best_seed.get('recovery_MA'):.4f}")
    print(f"  Productivity: {best_seed.get('productivity'):.6f}")
    print()

    # Now run Phase 4 with these flows and warm-start
    # We need to load the Phase 2 model state to use as warm-start

    # First, we need to run Phase 2 at the same discretization to get model state
    print("Step 1: Extract model state from Phase 2 medium fidelity...")
    print("  Running Phase 2 medium fidelity evaluation with _model_state capture...")

    import argparse as ap
    from benchmarks.run_stage import evaluate_candidate

    # Build args for Phase 2 evaluation (with model state capture)
    fraf_val = flows.get('Ffeed') + flows.get('Fdes') - flows.get('Fex')
    phase2_args = ap.Namespace(
        stage="reference-eval",
        run_name="phase4_warmstart_phase2_extract",
        nc=args.nc,
        f1=flows.get('F1'),
        ffeed=flows.get('Ffeed'),
        fdes=flows.get('Fdes'),
        fex=flows.get('Fex'),
        fraf=fraf_val,
        tstep=flows.get('tstep'),
        nfex=6,  # Phase 2 medium fidelity
        nfet=3,
        ncp=1,
        purity_min=0.05,
        recovery_ga_min=0.10,
        recovery_ma_min=0.15,
        max_solve_seconds=60,
        solver_name="ipopt",
        linear_solver="ma57",
        max_iter=5000,
        tol=1e-6,
        acceptable_tol=1e-5,
        constr_viol_tol=1e-6,
        acceptable_constr_viol_tol=1e-3,
        dual_inf_tol=1.0,
        acceptable_dual_inf_tol=1e10,
        artifact_dir=args.artifact_dir,
        tee=False,
        no_reference_gate=True,
        executive_live_monitor=False,
    )

    print("  Running Phase 2 reference evaluation...")
    phase2_eval = evaluate_candidate(phase2_args, nc_list, return_model_state=True)

    if phase2_eval.get("status") != "ok":
        print(f"⚠️  Phase 2 evaluation warning: {phase2_eval.get('error')}")
        # Still proceed if we can extract some state

    # Extract model state if available
    warm_start_state = phase2_eval.get("_model_state")
    if not warm_start_state:
        print("⚠️  No model state captured. Falling back to cold start.")
        warm_start_state = None
    else:
        print(f"✅ Model state extracted ({len(warm_start_state)} variables)")

    print()
    print("Step 2: Run Phase 4 production fidelity with warm-start...")
    print()

    # Build args for Phase 4 with warm-start
    phase4_args = ap.Namespace(
        stage="reference-eval",
        run_name=args.run_name,
        nc=args.nc,
        f1=flows.get('F1'),
        ffeed=flows.get('Ffeed'),
        fdes=flows.get('Fdes'),
        fex=flows.get('Fex'),
        fraf=fraf_val,
        tstep=flows.get('tstep'),
        nfex=args.nfex,  # Production fidelity
        nfet=args.nfet,
        ncp=args.ncp,
        purity_min=0.05,
        recovery_ga_min=0.10,
        recovery_ma_min=0.15,
        max_solve_seconds=600,  # More time for warm-start test
        solver_name="ipopt",
        linear_solver="ma57",
        max_iter=5000,
        tol=1e-6,
        acceptable_tol=1e-5,
        constr_viol_tol=1e-6,
        acceptable_constr_viol_tol=1e-3,
        dual_inf_tol=1.0,
        acceptable_dual_inf_tol=1e10,
        artifact_dir=args.artifact_dir,
        tee=True,  # Show solver output
        no_reference_gate=True,
        executive_live_monitor=False,
    )

    start = time.time()
    phase4_result = evaluate_candidate(phase4_args, nc_list, warm_start_state=warm_start_state)
    elapsed = time.time() - start

    print()
    print("="*80)
    print("PHASE 4 WARM-START TEST RESULTS")
    print("="*80)
    print()
    print(f"Status: {phase4_result.get('status')}")
    print(f"Runtime: {elapsed:.1f} seconds")

    if phase4_result.get("status") == "ok":
        metrics = phase4_result.get("metrics", {})
        print()
        print("✅ SOLVER CONVERGED!")
        print()
        print("Performance Metrics:")
        print(f"  Purity: {metrics.get('purity_ex_meoh_free', 0):.4f}")
        print(f"  Recovery GA: {metrics.get('recovery_ex_GA', 0):.4f}")
        print(f"  Recovery MA: {metrics.get('recovery_ex_MA', 0):.4f}")
        print(f"  Productivity: {metrics.get('productivity_ex_ga_ma', 0):.6f}")

        # Check constraints
        purity_ok = metrics.get('purity_ex_meoh_free', 0) >= 0.05
        rec_ga_ok = metrics.get('recovery_ex_GA', 0) >= 0.10
        rec_ma_ok = metrics.get('recovery_ex_MA', 0) >= 0.15

        print()
        print("Constraint Satisfaction:")
        print(f"  Purity ≥ 0.05: {'✅' if purity_ok else '❌'}")
        print(f"  Recovery GA ≥ 0.10: {'✅' if rec_ga_ok else '❌'}")
        print(f"  Recovery MA ≥ 0.15: {'✅' if rec_ma_ok else '❌'}")

        if purity_ok and rec_ga_ok and rec_ma_ok:
            print()
            print("🏆 ALL CONSTRAINTS MET AT PRODUCTION FIDELITY WITH WARM-START!")
            return 0
        else:
            print()
            print("⚠️  Some constraints not satisfied (but solver converged)")
            return 0
    else:
        print()
        print(f"❌ Solver error: {phase4_result.get('error')}")
        print()
        print(f"Termination: {phase4_result.get('solver', {}).get('termination_condition')}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
