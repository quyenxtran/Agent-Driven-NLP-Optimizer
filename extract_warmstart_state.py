#!/usr/bin/env python
"""
Extract model state from a Phase 2 reference evaluation result.
This state can be used as warm-start input for Phase 4 production fidelity.

Usage:
    python extract_warmstart_state.py --nc "2,1,3,2" --output /tmp/warmstart_state.json
"""
import json
import sys
import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Extract warm-start state from Phase 2 reference evaluation")
    parser.add_argument("--phase2-artifact",
                       default="/storage/home/hcoda1/4/qtran47/AutoResearch-SMB/artifacts/phase2_lhs_seeding/phase2_reference_summary_corrected.json",
                       help="Phase 2 reference summary JSON")
    parser.add_argument("--nc", required=True, help="NC configuration as comma-separated")
    parser.add_argument("--output", help="Output file for warm-start state JSON")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    # Parse NC
    nc_list = tuple(int(x) for x in args.nc.split(","))

    if args.verbose:
        print(f"Loading Phase 2 results from: {args.phase2_artifact}")
        print(f"Searching for NC: {nc_list}")

    # Load Phase 2 results
    with open(args.phase2_artifact) as f:
        phase2_data = json.load(f)

    # Find NC result
    phase2_result = None
    for nc_result in phase2_data.get("results", []):
        if tuple(nc_result.get("nc", [])) == nc_list:
            phase2_result = nc_result
            break

    if not phase2_result:
        print(f"❌ ERROR: NC {nc_list} not found in Phase 2 results", file=sys.stderr)
        return 1

    best_seed = phase2_result.get("best_seed")
    if not best_seed:
        print(f"❌ ERROR: No best seed found for NC {nc_list}", file=sys.stderr)
        return 1

    # Extract flows
    flows = best_seed.get("flows", {})

    if args.verbose:
        print()
        print(f"✅ Found Phase 2 result for NC {nc_list}")
        print(f"  Flows: F1={flows.get('F1'):.4f}, Ffeed={flows.get('Ffeed'):.4f}, "
              f"Fdes={flows.get('Fdes'):.4f}, Fex={flows.get('Fex'):.4f}, tstep={flows.get('tstep'):.4f}")
        print(f"  Purity: {best_seed.get('purity'):.4f}")
        print(f"  Recovery GA: {best_seed.get('recovery_GA'):.4f}")
        print(f"  Recovery MA: {best_seed.get('recovery_MA'):.4f}")
        print(f"  Productivity: {best_seed.get('productivity'):.6f}")

    # The warm-start state object stores the solution
    # Note: Phase 2 results don't include the full _model_state from discretization
    # We would need to run Phase 2 with return_model_state=True to get the actual
    # C, Q, Cp, U, UF, UD, UE, UR variables
    # For now, we'll output metadata about what flows to use

    warm_start_info = {
        "nc": list(nc_list),
        "flows": {
            "F1": flows.get('F1'),
            "Ffeed": flows.get('Ffeed'),
            "Fdes": flows.get('Fdes'),
            "Fex": flows.get('Fex'),
            "Fraf": flows.get('Fraf'),
            "tstep": flows.get('tstep'),
        },
        "metrics": {
            "purity": best_seed.get('purity'),
            "recovery_GA": best_seed.get('recovery_GA'),
            "recovery_MA": best_seed.get('recovery_MA'),
            "productivity": best_seed.get('productivity'),
            "feasible": best_seed.get('feasible'),
        },
        "phase2_seed_idx": best_seed.get('seed_idx'),
        "note": "This contains flows and metadata. To get full model state (C, Q, Cp, U),  "
                "run Phase 2 reference-eval with return_model_state=True."
    }

    if args.output:
        Path(args.output).write_text(json.dumps(warm_start_info, indent=2))
        if args.verbose:
            print(f"\n✅ Warm-start info saved to: {args.output}")
        print(json.dumps(warm_start_info, indent=2))
    else:
        print(json.dumps(warm_start_info, indent=2))

    return 0

if __name__ == "__main__":
    sys.exit(main())
