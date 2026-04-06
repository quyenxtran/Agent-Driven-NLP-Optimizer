#!/usr/bin/env python3
"""
Phase 3 Strategy 1: Regular LHS

Baseline approach: Screen all → select top 5 distinct → optimize high fidelity
No intelligence, purely productivity-based ranking.

Expected: Lowest best J (baseline)
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Dict

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "benchmarks"))

from benchmarks.phase3_multistart_utils import run_high_fidelity_once, summarize_multistart


def run_strategy1(screening_data: List[Dict], artifact_dir: str) -> Dict:
    """
    Strategy 1: Regular LHS

    Process:
      1. Rank all feasible NCs by screening productivity
      2. Select top 5 DISTINCT NCs
      3. Optimize each with high fidelity
      4. Return best result
    """

    print(f"\n{'='*70}")
    print("STRATEGY 1: Regular LHS (Baseline)")
    print(f"{'='*70}")

    # Find best NC by screening productivity
    nc_best = {}
    for point in screening_data:
        if not point.get("feasible"):
            continue
        nc = tuple(point["nc"])
        metrics = point.get("metrics", {})
        prod = metrics.get("productivity") or metrics.get("productivity_ex_ga_ma")
        if prod and (nc not in nc_best or prod > nc_best[nc]):
            nc_best[nc] = prod

    # Sort by productivity, pick top 5
    top_5_ncs = sorted(nc_best.items(), key=lambda x: -x[1])[:5]

    print(f"\nAnalysis:")
    print(f"  Found {len(nc_best)} feasible NCs in screening data")
    print(f"  Top 5 by productivity:")
    for i, (nc, prod) in enumerate(top_5_ncs, 1):
        print(f"    {i}. NC {list(nc)}: J≈{prod:.2f}")

    # Optimize each with high fidelity
    print(f"\nOptimizing top 5 with high fidelity (nfex=10, nfet=5; relaxed promotion thresholds)...")
    results = []
    for i, (nc, screen_prod) in enumerate(top_5_ncs):
        nc_list = list(nc)
        run_name = f"phase3_s1_nc_{nc_list[0]}{nc_list[1]}{nc_list[2]}{nc_list[3]}"

        print(f"  [{i+1}/5] NC {nc_list}...", end=" ", flush=True)

        result = run_high_fidelity_once(nc_list, run_name, artifact_dir, start_index=0)
        results.append(result)

        if result["status"] == "ok":
            opt_prod = result.get("productivity", 0)
            improvement = ((opt_prod - screen_prod) / screen_prod * 100) if screen_prod else 0
            print(f"✓ J={opt_prod:.2f} (screen: {screen_prod:.2f}, +{improvement:.1f}%)")
        else:
            detail = result.get("termination_condition") or result.get("solver_message") or result.get("error") or result['status']
            print(f"✗ {result['status']} ({str(detail)[:120]})")

    # Find best
    valid_results = [r for r in results if r["status"] == "ok"]
    if valid_results:
        best = max(valid_results, key=lambda r: r.get("productivity", -float('inf')))
        print(f"\n{'='*70}")
        print(f"STRATEGY 1 RESULT:")
        print(f"{'='*70}")
        print(f"Best NC: {best['nc']}")
        print(f"Best J: {best['productivity']:.4f}")
        print(f"Purity: {best['purity']:.4f}")
        print(f"Recovery GA: {best['recovery_ga']:.4f}")

        finalist = best["nc"]
        print(f"\nRunning 3 multi-start high-fidelity validations on finalist {finalist}...")
        multistart_results = []
        for start_idx in range(3):
            ms_name = f"phase3_s1_finalist_{finalist[0]}{finalist[1]}{finalist[2]}{finalist[3]}_ms{start_idx}"
            ms_result = run_high_fidelity_once(finalist, ms_name, artifact_dir, start_index=start_idx)
            multistart_results.append(ms_result)
            if ms_result["status"] == "ok":
                print(f"  multi-start {start_idx}: ✓ J={ms_result.get('productivity', 0):.4f}")
            else:
                detail = ms_result.get("termination_condition") or ms_result.get("solver_message") or ms_result.get("error") or ms_result['status']
                print(f"  multi-start {start_idx}: ✗ {ms_result['status']} ({str(detail)[:120]})")

        multistart_summary = summarize_multistart(multistart_results)

        return {
            "strategy": "Regular LHS",
            "best_config": best["nc"],
            "best_j": best.get("productivity"),
            "purity": best.get("purity"),
            "recovery_ga": best.get("recovery_ga"),
            "n_optimizations": len(valid_results),
            "results": results,
            "finalist_multistart": {
                "nc": finalist,
                "results": multistart_results,
                "summary": multistart_summary,
            },
        }
    else:
        print(f"\n✗ All optimizations failed")
        return {
            "strategy": "Regular LHS",
            "best_config": None,
            "best_j": None,
            "error": "All optimizations failed",
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 3 Strategy 1: Regular LHS")
    parser.add_argument("--phase2-dir", default="artifacts/phase2_lhs_seeding")
    parser.add_argument("--artifact-dir", default="artifacts/phase3_strategy1")

    args = parser.parse_args()

    # Load canonical Phase 2 screening/reference data
    phase2_dir = Path(args.phase2_dir)
    candidates = [
        phase2_dir / "phase2_reference_canonical.json",
        phase2_dir / "phase2_summary.canonical.json",
        phase2_dir / "phase2_summary.json",
    ]
    phase2_summary = next((p for p in candidates if p.exists()), None)
    if phase2_summary is None:
        print(f"❌ No usable Phase 2 results found in: {phase2_dir}")
        return 1

    print(f"Using Phase 2 data source: {phase2_summary}")
    with open(phase2_summary) as f:
        phase2 = json.load(f)

    # Flatten screening data
    screening_data = []
    for nc_result in phase2.get("results", []):
        for seed_result in nc_result.get("all_seed_results", []):
            if seed_result.get("status") == "ok":
                screening_data.append({
                    "nc": nc_result.get("nc"),
                    "seed_idx": seed_result.get("seed_idx"),
                    "metrics": seed_result.get("metrics", {}),
                    "feasible": True,
                })

    print(f"\nLoaded {len(screening_data)} feasible seeds from Phase 2B")

    # Create artifact directory
    Path(args.artifact_dir).mkdir(parents=True, exist_ok=True)

    # Run strategy
    result = run_strategy1(screening_data, args.artifact_dir)

    # Save result
    result_file = Path(args.artifact_dir) / "strategy1_result.json"
    with open(result_file, "w") as f:
        json.dump(result, f, indent=2)

    print(f"\nResults saved to: {result_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
