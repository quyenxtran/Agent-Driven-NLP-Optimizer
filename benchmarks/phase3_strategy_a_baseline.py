#!/usr/bin/env python3
"""
Phase 3 Strategy A: Heuristic Baseline

Control group: Pure exploitation using domain heuristics.
Score each NC by metrics product / variance, select top 5.

No learning from Phase 2 data—just empirical best results.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Setup path
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))


def load_phase2_data(phase2_file: Path) -> Dict:
    """Load Phase 2 summary data."""
    with open(phase2_file) as f:
        return json.load(f)


def compute_heuristic_score(nc_result: Dict) -> Tuple[float, Dict]:
    """
    Compute heuristic score for NC.

    Score = (purity × recovery × productivity) / (variance + 0.01)

    Returns: (score, metadata)
    """
    if not nc_result.get("all_seed_results"):
        return 0.0, {"reason": "no_results"}

    all_results = nc_result["all_seed_results"]

    # Extract metrics from seed results
    productivities = []
    purities = []
    recoveries = []

    for seed_result in all_results:
        if isinstance(seed_result, dict):
            metrics = seed_result.get("metrics", {})
            if metrics:
                prod = metrics.get("productivity_ex_ga_ma", 0)
                pur = metrics.get("purity_ex_meoh_free", 0)
                rec_ga = metrics.get("recovery_ex_GA", 0)
                rec_ma = metrics.get("recovery_ex_MA", 0)

                if prod > 0 and pur > 0 and rec_ga > 0 and rec_ma > 0:
                    productivities.append(prod)
                    purities.append(pur)
                    recoveries.append(rec_ga * rec_ma)  # Combined recovery

    if not productivities:
        return 0.0, {"reason": "no_valid_metrics"}

    # Compute means and variance
    mean_prod = sum(productivities) / len(productivities)
    mean_pur = sum(purities) / len(purities)
    mean_rec = sum(recoveries) / len(recoveries)

    # Variance of productivity (penalize inconsistency)
    var_prod = sum((p - mean_prod) ** 2 for p in productivities) / len(productivities) + 0.01

    # Score: product of metrics / variance
    score = (mean_prod * mean_pur * mean_rec) / var_prod

    return score, {
        "mean_productivity": mean_prod,
        "mean_purity": mean_pur,
        "mean_recovery": mean_rec,
        "variance": var_prod,
        "n_feasible": len(productivities),
    }


def run_strategy_a(phase2_file: Path) -> Dict:
    """
    Run Strategy A: Heuristic baseline.

    1. Load Phase 2 data
    2. Score each NC by heuristic
    3. Select top 5
    4. Output with reasoning
    """
    print("\n" + "=" * 70)
    print("PHASE 3 STRATEGY A: HEURISTIC BASELINE")
    print("=" * 70)

    # Load data
    print(f"\nLoading Phase 2 data from {phase2_file}...")
    phase2_data = load_phase2_data(phase2_file)

    results = phase2_data.get("results", [])
    print(f"Found {len(results)} NCs in Phase 2 data")

    # Score all NCs
    print("\nScoring NCs by heuristic: (pu × re × pr) / variance...")
    scores = {}

    for nc_result in results:
        nc = tuple(nc_result["nc"])
        score, metadata = compute_heuristic_score(nc_result)
        scores[nc] = {
            "score": score,
            "metadata": metadata,
        }

        if score > 0:
            print(f"  NC {nc}: score={score:.4f} (pu={metadata.get('mean_purity', 0):.3f}, "
                  f"re={metadata.get('mean_recovery', 0):.3f}, pr={metadata.get('mean_productivity', 0):.3f})")

    # Sort by score
    ranked = sorted(scores.items(), key=lambda x: x[1]["score"], reverse=True)

    # Select top 5
    print("\n" + "-" * 70)
    print("TOP 5 SELECTED NCs:")
    print("-" * 70)

    top_5 = []
    for rank, (nc, data) in enumerate(ranked[:5], 1):
        top_5.append(nc)
        score = data["score"]
        meta = data["metadata"]

        print(f"\n{rank}. NC {nc}")
        print(f"   Score: {score:.4f}")
        print(f"   Productivity: {meta.get('mean_productivity', 0):.4f}")
        print(f"   Purity: {meta.get('mean_purity', 0):.4f}")
        print(f"   Recovery: {meta.get('mean_recovery', 0):.4f}")
        print(f"   Feasible seeds: {meta.get('n_feasible', 0)}/100")

    # Build output
    output = {
        "strategy": "strategy_a_baseline",
        "selected_ncs": [list(nc) for nc in top_5],
        "rankings": {
            str(nc): {
                "score": data["score"],
                "metadata": data["metadata"],
                "rank": rank,
            }
            for rank, (nc, data) in enumerate(ranked, 1)
        },
        "method": {
            "name": "Heuristic Baseline",
            "description": "Score = (purity × recovery × productivity) / variance",
            "philosophy": "Pure exploitation, no learning from Phase 2 data beyond best results",
        },
    }

    print("\n" + "=" * 70)
    print(f"✓ Strategy A Complete: {len(top_5)} NCs selected")
    print("=" * 70)

    return output


def main():
    phase2_file = REPO_ROOT / "artifacts" / "phase2_lhs_seeding" / "phase2_summary.json"

    if not phase2_file.exists():
        print(f"✗ Phase 2 data not found: {phase2_file}")
        print("  Run Phase 2 first (benchmarks/phase2_lhs_seeding_direct.py)")
        sys.exit(1)

    # Run strategy
    results = run_strategy_a(phase2_file)

    # Save results
    output_file = REPO_ROOT / "artifacts" / "phase3_results" / "strategy_a_selection.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n✓ Results saved to {output_file}")
    print(f"\nNext: Implement Strategy B (BO+GP) and Strategy C (Agent+LHS+Domain)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
