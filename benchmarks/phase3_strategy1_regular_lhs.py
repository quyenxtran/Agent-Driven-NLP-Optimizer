#!/usr/bin/env python3
"""
Phase 3 Strategy 1: Regular LHS

Baseline approach: Screen all → select top 5 distinct → optimize high fidelity
No intelligence, purely productivity-based ranking.

Expected: Lowest best J (baseline)
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import List, Dict

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "benchmarks"))


def optimize_high_fidelity(nc: List[int], run_name: str, artifact_dir: str) -> Dict:
    """Run high-fidelity optimization on a single NC"""
    nc_str = f"[{nc[0]},{nc[1]},{nc[2]},{nc[3]}]"

    cmd = [
        sys.executable, "-m", "benchmarks.run_stage",
        "--stage", "optimize-layouts",
        "--run-name", run_name,
        "--artifact-dir", artifact_dir,
        "--nc", nc_str,
        "--solver-name", "auto",
        "--linear-solver", "ma97",
        "--nfex", "10",  # High fidelity
        "--nfet", "5",
        "--ncp", "2",
        "--purity-min", "0.20",
        "--recovery-ga-min", "0.20",
        "--recovery-ma-min", "0.20",
        "--max-pump-flow", "3.0",
    ]

    try:
        result = subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=600,
        )

        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if '"artifact"' in line:
                    artifact_path = json.loads(line).get('artifact')
                    if artifact_path and Path(artifact_path).exists():
                        with open(artifact_path) as f:
                            artifact = json.load(f)
                        return {
                            "status": "ok",
                            "nc": nc,
                            "productivity": artifact.get("J_validated"),
                            "purity": artifact.get("metrics", {}).get("purity_ex_meoh_free"),
                            "recovery_ga": artifact.get("metrics", {}).get("recovery_ex_GA"),
                        }

        return {"status": "error", "nc": nc, "error": result.stderr[:200]}

    except subprocess.TimeoutExpired:
        return {"status": "timeout", "nc": nc}
    except Exception as e:
        return {"status": "exception", "nc": nc, "error": str(e)}


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
        prod = point["metrics"].get("productivity")
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
    print(f"\nOptimizing top 5 with high fidelity (nfex=10, nfet=5)...")
    results = []
    for i, (nc, screen_prod) in enumerate(top_5_ncs):
        nc_list = list(nc)
        run_name = f"phase3_s1_nc_{nc_list[0]}{nc_list[1]}{nc_list[2]}{nc_list[3]}"

        print(f"  [{i+1}/5] NC {nc_list}...", end=" ", flush=True)

        result = optimize_high_fidelity(nc_list, run_name, artifact_dir)
        results.append(result)

        if result["status"] == "ok":
            opt_prod = result.get("productivity", 0)
            improvement = ((opt_prod - screen_prod) / screen_prod * 100) if screen_prod else 0
            print(f"✓ J={opt_prod:.2f} (screen: {screen_prod:.2f}, +{improvement:.1f}%)")
        else:
            print(f"✗ {result['status']}")

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

        return {
            "strategy": "Regular LHS",
            "best_config": best["nc"],
            "best_j": best.get("productivity"),
            "purity": best.get("purity"),
            "recovery_ga": best.get("recovery_ga"),
            "n_optimizations": len(valid_results),
            "results": results,
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

    # Load Phase 2B screening data
    phase2_summary = Path(args.phase2_dir) / "phase2_summary.json"
    if not phase2_summary.exists():
        print(f"❌ Phase 2B results not found: {phase2_summary}")
        return 1

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
