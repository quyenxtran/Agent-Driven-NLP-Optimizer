#!/usr/bin/env python3
"""
Phase 3 Strategy 3: Agent + LHS

Process:
  1. Load Phase 2B screening data
  2. Agent analyzes screening results
  3. Agent uses heuristics to intelligently rank NCs
  4. Select top 5 by agent reasoning (not just productivity)
  5. Optimize each with high fidelity
  6. Return best result

Expected: Moderate-High best J (agent intelligence, no BO)
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


def get_valid_ncs() -> List[List[int]]:
    """Get all valid NC configurations (sum=8, each>=1)"""
    ncs = []
    for n0 in range(1, 6):
        for n1 in range(1, 6):
            for n2 in range(1, 6):
                for n3 in range(1, 6):
                    if n0 + n1 + n2 + n3 == 8:
                        ncs.append([n0, n1, n2, n3])
    return ncs


def optimize_high_fidelity(nc: List[int], run_name: str, artifact_dir: str) -> Dict:
    """Run high-fidelity optimization on a single NC"""
    import subprocess

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


def run_strategy3(screening_data: List[Dict], artifact_dir: str) -> Dict:
    """
    Strategy 3: Agent + LHS

    Agent analyzes screening data and applies heuristics to intelligently
    rank NCs, then selects top 5 for optimization.
    """
    import numpy as np

    print(f"\n{'='*70}")
    print("STRATEGY 3: Agent + LHS (Intelligent Heuristics)")
    print(f"{'='*70}")
    print(f"\nLoaded {len(screening_data)} screening points")

    # Get all valid NCs and analyze screening data for each
    all_ncs = get_valid_ncs()
    nc_scores = {}

    print(f"\nAgent analyzing {len(all_ncs)} NCs...")

    for nc in all_ncs:
        nc_tuple = tuple(nc)

        # Get all feasible screening results for this NC
        nc_data = [p for p in screening_data if p["nc"] == nc and p.get("feasible")]

        if not nc_data:
            nc_scores[nc_tuple] = {"score": -float('inf'), "reason": "No feasible seeds"}
            continue

        # Extract metrics
        prods = [p["metrics"].get("productivity") for p in nc_data if p["metrics"].get("productivity")]
        purities = [p["metrics"].get("purity") for p in nc_data if p["metrics"].get("purity")]
        recoveries = [p["metrics"].get("recovery_ga") for p in nc_data if p["metrics"].get("recovery_ga")]

        if not prods:
            nc_scores[nc_tuple] = {"score": -float('inf'), "reason": "No valid productivity data"}
            continue

        # Agent heuristics
        prod_mean = float(np.mean(prods))
        prod_std = float(np.std(prods)) if len(prods) > 1 else 0
        purity_mean = float(np.mean(purities)) if purities else 0
        recovery_mean = float(np.mean(recoveries)) if recoveries else 0

        # Balance score: prefer balanced [a,b,c,d]
        balance = 1.0 / (1 + np.std(nc))  # Higher when all values are similar

        # Variance score: low variance = stable
        stability = 1.0 / (1 + prod_std)  # Higher when std is low

        # Feasibility score: metrics quality
        feasibility = (purity_mean * 0.3 + recovery_mean * 0.3) if purity_mean and recovery_mean else 0.5

        # Composite score: balance (40%) + stability (30%) + feasibility (20%) + productivity (10%)
        composite_score = (
            0.40 * balance +
            0.30 * stability +
            0.20 * feasibility +
            0.10 * (prod_mean / 100.0)  # Normalize productivity to ~0.1 range
        )

        nc_scores[nc_tuple] = {
            "score": composite_score,
            "productivity": prod_mean,
            "stability": stability,
            "balance": balance,
            "n_seeds": len(nc_data),
            "reason": f"Prod={prod_mean:.2f}, Balance={balance:.3f}, Stability={stability:.3f}"
        }

    # Sort by composite score
    ranked_ncs = sorted(
        nc_scores.items(),
        key=lambda x: x[1]["score"],
        reverse=True
    )

    # Select top 5
    top_5_ncs = ranked_ncs[:5]

    print(f"\nAgent reasoning (Top 5 by heuristic score):")
    for i, (nc_tuple, score_data) in enumerate(top_5_ncs, 1):
        nc = list(nc_tuple)
        print(f"  {i}. NC {nc}: score={score_data['score']:.4f}")
        print(f"     {score_data['reason']}")

    # Optimize each with high fidelity
    print(f"\nOptimizing top 5 with high fidelity (nfex=10, nfet=5)...")
    results = []
    for i, (nc_tuple, score_data) in enumerate(top_5_ncs):
        nc_list = list(nc_tuple)
        run_name = f"phase3_s3_nc_{nc_list[0]}{nc_list[1]}{nc_list[2]}{nc_list[3]}"

        print(f"  [{i+1}/5] NC {nc_list}...", end=" ", flush=True)

        result = run_high_fidelity_once(nc_list, run_name, artifact_dir, start_index=0)
        results.append(result)

        if result["status"] == "ok":
            opt_prod = result.get("productivity", 0)
            print(f"✓ J={opt_prod:.2f}")
        else:
            print(f"✗ {result['status']}")

    # Find best
    valid_results = [r for r in results if r["status"] == "ok"]
    if valid_results:
        best = max(valid_results, key=lambda r: r.get("productivity", -float('inf')))
        print(f"\n{'='*70}")
        print(f"STRATEGY 3 RESULT:")
        print(f"{'='*70}")
        print(f"Best NC: {best['nc']}")
        print(f"Best J: {best['productivity']:.4f}")
        print(f"Purity: {best['purity']:.4f}")
        print(f"Recovery GA: {best['recovery_ga']:.4f}")

        finalist = best["nc"]
        print(f"\nRunning 3 multi-start high-fidelity validations on finalist {finalist}...")
        multistart_results = []
        for start_idx in range(3):
            ms_name = f"phase3_s3_finalist_{finalist[0]}{finalist[1]}{finalist[2]}{finalist[3]}_ms{start_idx}"
            ms_result = run_high_fidelity_once(finalist, ms_name, artifact_dir, start_index=start_idx)
            multistart_results.append(ms_result)
            if ms_result["status"] == "ok":
                print(f"  multi-start {start_idx}: ✓ J={ms_result.get('productivity', 0):.4f}")
            else:
                print(f"  multi-start {start_idx}: ✗ {ms_result['status']}")

        multistart_summary = summarize_multistart(multistart_results)

        return {
            "strategy": "Agent + LHS",
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
            "top_5_reasoning": [
                {
                    "nc": list(nc_tuple),
                    "heuristic_score": score_data["score"],
                    "reason": score_data["reason"]
                }
                for nc_tuple, score_data in top_5_ncs
            ]
        }
    else:
        print(f"\n✗ All optimizations failed")
        return {
            "strategy": "Agent + LHS",
            "best_config": None,
            "best_j": None,
            "error": "All optimizations failed",
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 3 Strategy 3: Agent + LHS")
    parser.add_argument("--phase2-dir", default="artifacts/phase2_lhs_seeding")
    parser.add_argument("--artifact-dir", default="artifacts/phase3_strategy3")

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

    # Create artifact directory
    Path(args.artifact_dir).mkdir(parents=True, exist_ok=True)

    # Run strategy
    result = run_strategy3(screening_data, args.artifact_dir)

    # Save result
    result_file = Path(args.artifact_dir) / "strategy3_result.json"
    with open(result_file, "w") as f:
        json.dump(result, f, indent=2)

    print(f"\nResults saved to: {result_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
