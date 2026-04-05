#!/usr/bin/env python3
"""
Phase 3: Data Aggregation
Combines Phase 1 (baseline eval) + Phase 2B (LHS-seeded optimization) into unified BO training dataset.

Training data structure:
  [
    {
      "source": "phase1" | "phase2b",
      "nc": [n0, n1, n2, n3],
      "seed_idx": null (phase1) | 0-7 (phase2b),
      "flows": {"tstep": ..., "ffeed": ..., ...},
      "metrics": {
        "productivity": ...,
        "purity": ...,
        "recovery_ga": ...,
        "recovery_ma": ...
      },
      "feasible": true | false (based on constraints)
    },
    ...
  ]

Expected output:
  - Phase 1: 31 baseline points (all feasible)
  - Phase 2B: ~80 optimized points (80% feasible expected)
  - Total: ~111 training points for BO surrogates

Progressive tool availability:
  - GP: available from start (only needs ≥1 point)
  - DNN: available after ≥100 points (Phase 1 + Phase 2B start)
  - PINN: available after ≥150-200 points (Phase 2B + more exploration)
"""

import json
import argparse
import sys
from pathlib import Path
from typing import List, Dict, Optional

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "benchmarks"))


def load_phase1_results(phase1_artifact_dir: str) -> List[Dict]:
    """
    Load Phase 1 baseline results from LHS-only evaluation.
    Each NC config is evaluated once at fixed reference flows.

    Returns list of data points with format:
    {
      "source": "phase1",
      "nc": [n0, n1, n2, n3],
      "seed_idx": None,
      "flows": {...},  # Fixed reference flows
      "metrics": {...},
      "feasible": True (all phase1 results are baseline, treat as feasible)
    }
    """
    phase1_dir = Path(phase1_artifact_dir)

    # Expected file: phase1_lhs_only_summary.json
    summary_file = phase1_dir / "phase1_lhs_only_summary.json"
    if not summary_file.exists():
        print(f"⚠️  Phase 1 summary not found: {summary_file}")
        return []

    with open(summary_file) as f:
        phase1_summary = json.load(f)

    phase1_data = []

    # Extract each NC evaluation result
    if "results" in phase1_summary:
        for result in phase1_summary["results"]:
            if result.get("status") != "ok":
                continue

            nc = result.get("nc")
            if not nc or len(nc) != 4:
                continue

            # Phase 1 uses fixed reference flows (from NOTEBOOK_SEEDS)
            # Typical values: tstep=9.4, ffeed=1.3, fdes=1.2, fex=0.9, f1=2.2
            data_point = {
                "source": "phase1",
                "nc": nc,
                "seed_idx": None,
                "flows": result.get("flows", {}),
                "metrics": {
                    "productivity": result.get("productivity"),
                    "purity": result.get("purity"),
                    "recovery_ga": result.get("recovery_ga"),
                    "recovery_ma": result.get("recovery_ma"),
                },
                "feasible": True,  # Phase 1 baseline, treat as feasible
            }

            # Check for NaN/None values
            if all(v is not None for v in data_point["metrics"].values()):
                phase1_data.append(data_point)

    print(f"✓ Loaded {len(phase1_data)} Phase 1 baseline points")
    return phase1_data


def load_phase2b_results(phase2b_artifact_dir: str) -> List[Dict]:
    """
    Load Phase 2B optimization results with LHS-sampled seeds.
    Each NC is optimized from 8 LHS-sampled starting points.
    Keep ALL seed results (not just best) for richer training data.

    Returns list of data points with format:
    {
      "source": "phase2b",
      "nc": [n0, n1, n2, n3],
      "seed_idx": 0-7,
      "flows": {...},  # Optimized flows from this seed
      "metrics": {...},
      "feasible": True (if feasible under loose constraints: purity≥0.20, recovery≥0.20)
    }
    """
    phase2b_dir = Path(phase2b_artifact_dir)

    # Expected file: phase2b_summary.json
    summary_file = phase2b_dir / "phase2b_summary.json"
    if not summary_file.exists():
        print(f"⚠️  Phase 2B summary not found: {summary_file}")
        return []

    with open(summary_file) as f:
        phase2b_summary = json.load(f)

    phase2b_data = []

    # Extract all NC results with all seed results
    if "results" in phase2b_summary:
        for nc_result in phase2b_summary["results"]:
            nc = nc_result.get("nc")
            if not nc or len(nc) != 4:
                continue

            # Get all_seed_results (includes all 8 seeds, not just best)
            all_seed_results = nc_result.get("all_seed_results", [])

            for seed_result in all_seed_results:
                if seed_result.get("status") != "ok":
                    continue

                seed_idx = seed_result.get("seed_idx")
                artifact = seed_result.get("artifact", {})

                # Phase 2B uses loose constraints for BO development
                # Feasible = purity ≥ 0.20 AND recovery_ga ≥ 0.20 AND recovery_ma ≥ 0.20
                metrics = artifact.get("metrics", {})
                purity = metrics.get("purity_ex_meoh_free")
                recovery_ga = metrics.get("recovery_ex_GA")
                recovery_ma = metrics.get("recovery_ex_MA")

                is_feasible = (
                    purity is not None and purity >= 0.20 and
                    recovery_ga is not None and recovery_ga >= 0.20 and
                    recovery_ma is not None and recovery_ma >= 0.20
                )

                data_point = {
                    "source": "phase2b",
                    "nc": nc,
                    "seed_idx": seed_idx,
                    "flows": artifact.get("optimized_flows", {}),
                    "metrics": {
                        "productivity": artifact.get("J_validated"),
                        "purity": purity,
                        "recovery_ga": recovery_ga,
                        "recovery_ma": recovery_ma,
                    },
                    "feasible": is_feasible,
                }

                # Only include if all metrics present
                if all(v is not None for v in data_point["metrics"].values()):
                    phase2b_data.append(data_point)

    print(f"✓ Loaded {len(phase2b_data)} Phase 2B optimization results")
    return phase2b_data


def aggregate_training_data(
    phase1_dir: str,
    phase2b_dir: str,
    output_file: str,
) -> Dict:
    """
    Aggregate Phase 1 + Phase 2B into unified training dataset.

    Returns summary with:
    - total_points: Combined training size
    - phase1_count, phase2b_count: Breakdown
    - feasible_count, infeasible_count: Feasibility breakdown
    - training_data: Full aggregated list
    """

    print("="*70)
    print("PHASE 3: DATA AGGREGATION")
    print("="*70)
    print(f"Phase 1 artifacts: {phase1_dir}")
    print(f"Phase 2B artifacts: {phase2b_dir}")
    print("")

    # Load both phases
    phase1_data = load_phase1_results(phase1_dir)
    phase2b_data = load_phase2b_results(phase2b_dir)

    # Aggregate
    all_data = phase1_data + phase2b_data

    # Count feasibility
    feasible_count = sum(1 for d in all_data if d["feasible"])
    infeasible_count = len(all_data) - feasible_count

    # Summary
    summary = {
        "method": "Phase 3: Data Aggregation",
        "timestamp": str(Path("/tmp").resolve()),
        "phase1_count": len(phase1_data),
        "phase2b_count": len(phase2b_data),
        "total_points": len(all_data),
        "feasible_count": feasible_count,
        "infeasible_count": infeasible_count,
        "feasibility_rate": feasible_count / len(all_data) if all_data else 0.0,
        "training_data": all_data,
    }

    # Save
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(summary, f, indent=2)

    print("="*70)
    print("AGGREGATION COMPLETE")
    print("="*70)
    print(f"Total training points: {len(all_data)}")
    print(f"  Phase 1 baseline: {len(phase1_data)}")
    print(f"  Phase 2B optimized: {len(phase2b_data)}")
    print(f"  Feasible: {feasible_count} ({100*feasible_count/len(all_data) if all_data else 0:.1f}%)")
    print(f"  Infeasible: {infeasible_count}")
    print("")
    print(f"BO Tool Availability:")
    if len(all_data) >= 1:
        print(f"  ✓ GP: Ready (needs ≥1 point, have {len(all_data)})")
    if len(all_data) >= 100:
        print(f"  ✓ DNN: Ready (needs ≥100 points, have {len(all_data)})")
    if len(all_data) < 100:
        print(f"  ⏳ DNN: Not yet (needs ≥100 points, have {len(all_data)})")
    if len(all_data) >= 150:
        print(f"  ✓ PINN: Ready (needs ≥150 points, have {len(all_data)})")
    if len(all_data) < 150:
        print(f"  ⏳ PINN: Not yet (needs ≥150 points, have {len(all_data)})")
    print("")
    print(f"Output: {output_path}")
    print("")

    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Aggregate Phase 1 + Phase 2B training data")
    parser.add_argument(
        "--phase1-dir",
        default="artifacts/phase1_lhs_only",
        help="Phase 1 artifact directory"
    )
    parser.add_argument(
        "--phase2b-dir",
        default="artifacts/phase2b_lhs_seeding",
        help="Phase 2B artifact directory"
    )
    parser.add_argument(
        "--output",
        default="artifacts/phase3_training_data.json",
        help="Output training data file"
    )

    args = parser.parse_args()

    aggregate_training_data(args.phase1_dir, args.phase2b_dir, args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
