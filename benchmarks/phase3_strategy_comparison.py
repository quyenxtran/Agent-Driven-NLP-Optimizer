#!/usr/bin/env python3
"""
Phase 3: Strategy Comparison Framework

After Phase 2B screening generates foundation data, compare 4 optimization strategies:

1. Regular LHS: Screen all → optimize top 5 distinct with high fidelity
2. BO Baseline: BO fitted from screening → optimize top BO predictions
3. Agent + LHS: Agent searches screening data intelligently
4. Agent + BO: Agent uses BO predictions to rank and evaluate

Purpose: Demonstrate that multi-BO + agent beats all alternatives.
"""

import argparse
import json
import sys
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Tuple

import numpy as np

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "benchmarks"))


class Strategy1_RegularLHS:
    """
    Strategy 1: Regular LHS

    Process:
      1. Load Phase 2B screening data (all feasible seeds)
      2. Sort by productivity
      3. Select top 5 DISTINCT NC configurations
      4. Optimize each with high fidelity
      5. Report best

    Baseline approach: maximize productivity at screening, then refine top 5.
    """

    def __init__(self, screening_data: List[Dict]):
        self.screening_data = screening_data
        self.name = "Regular LHS"

    def run(self, artifact_dir: str) -> Dict:
        """Run Strategy 1: screen results → optimize top 5 distinct"""

        # Find top NC configs by screening productivity
        nc_best = {}
        for point in self.screening_data:
            if not point.get("feasible"):
                continue
            nc = tuple(point["nc"])
            prod = point["metrics"].get("productivity")
            if prod and (nc not in nc_best or prod > nc_best[nc]):
                nc_best[nc] = prod

        # Sort by productivity, pick top 5 distinct NCs
        top_5_ncs = sorted(nc_best.items(), key=lambda x: -x[1])[:5]

        print(f"\n{self.name} Strategy:")
        print(f"  Found {len(nc_best)} feasible NCs in screening")
        print(f"  Top 5 by productivity: {[list(nc) for nc, _ in top_5_ncs]}")

        # Optimize each with high fidelity
        results = []
        for i, (nc, screen_prod) in enumerate(top_5_ncs):
            nc_list = list(nc)
            run_name = f"phase3_strategy1_nc_{nc_list[0]}{nc_list[1]}{nc_list[2]}{nc_list[3]}"

            result = self._optimize_high_fidelity(nc_list, run_name, artifact_dir)
            results.append(result)

            if result["status"] == "ok":
                print(f"    NC {nc_list}: screening J≈{screen_prod:.2f} → "
                      f"optimized J={result.get('productivity', 0):.2f}")

        # Find best
        best = max([r for r in results if r["status"] == "ok"],
                   key=lambda r: r.get("productivity", -float('inf')),
                   default=None)

        return {
            "strategy": self.name,
            "best_config": best["nc"] if best else None,
            "best_j": best.get("productivity") if best else None,
            "evaluations": len(results),
            "results": results,
        }

    def _optimize_high_fidelity(self, nc: List[int], run_name: str, artifact_dir: str) -> Dict:
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


class Strategy2_BO_Baseline:
    """
    Strategy 2: BO Baseline

    Process:
      1. Load Phase 2B screening data
      2. Fit BO (GP) to screening results
      3. Predict all NCs
      4. Select top 5 BO predictions
      5. Optimize each with high fidelity
      6. Report best

    Single-method BO: demonstrates single BO method performance.
    """

    def __init__(self, screening_data: List[Dict]):
        self.screening_data = screening_data
        self.name = "BO Baseline (Single GP)"

    def run(self, artifact_dir: str) -> Dict:
        print(f"\n{self.name} Strategy:")
        print(f"  Fit BO(GP) to {len(self.screening_data)} screening points")
        print(f"  Predict all NCs, optimize top 5")

        # TODO: Implement BO fitting and prediction
        # For now, return placeholder
        return {
            "strategy": self.name,
            "best_config": None,
            "best_j": None,
            "evaluations": 0,
            "note": "Implementation pending: fit BO to screening data",
        }


class Strategy3_Agent_LHS:
    """
    Strategy 3: Agent + LHS

    Process:
      1. Load Phase 2B screening data
      2. Agent analyzes screening results
      3. Agent intelligently selects top 5 promising NCs (not just by productivity)
      4. Optimize each with high fidelity
      5. Report best

    Agent intelligence: uses domain knowledge + heuristics to pick better NCs than naive ranking.
    """

    def __init__(self, screening_data: List[Dict]):
        self.screening_data = screening_data
        self.name = "Agent + LHS"

    def run(self, artifact_dir: str) -> Dict:
        print(f"\n{self.name} Strategy:")
        print(f"  Agent analyzes {len(self.screening_data)} screening points")
        print(f"  Agent selects top 5 promising NCs (intelligent ranking)")

        # TODO: Implement agent ranking logic
        return {
            "strategy": self.name,
            "best_config": None,
            "best_j": None,
            "evaluations": 0,
            "note": "Implementation pending: agent ranking",
        }


class Strategy4_Agent_BO:
    """
    Strategy 4: Agent + BO (Multi-BO)

    Process:
      1. Load Phase 2B screening data
      2. Fit multiple BO methods (GP, DNN, PINN - progressive availability)
      3. Agent receives predictions from all available methods
      4. Agent analyzes consensus/disagreement
      5. Agent decides top 5 to evaluate based on BO predictions
      6. Optimize each with high fidelity
      7. Update BO models, iterate
      8. Report best

    Full intelligence: multi-BO + agent prioritization.
    """

    def __init__(self, screening_data: List[Dict]):
        self.screening_data = screening_data
        self.name = "Agent + Multi-BO"

    def run(self, artifact_dir: str) -> Dict:
        print(f"\n{self.name} Strategy:")
        print(f"  Fit multi-BO to {len(self.screening_data)} screening points")
        print(f"  Agent receives GP/DNN/PINN predictions")
        print(f"  Agent intelligently selects top 5 to evaluate")

        # TODO: Implement multi-BO + agent loop
        return {
            "strategy": self.name,
            "best_config": None,
            "best_j": None,
            "evaluations": 0,
            "note": "Implementation pending: full multi-BO + agent orchestration",
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 3: Strategy Comparison")
    parser.add_argument("--phase2b-dir", default="artifacts/phase2b_lhs_seeding",
                        help="Phase 2B screening results directory")
    parser.add_argument("--artifact-dir", default="artifacts/phase3_strategy_comparison",
                        help="Output artifact directory")
    parser.add_argument("--strategies", nargs="+", default=["1", "2", "3", "4"],
                        choices=["1", "2", "3", "4"],
                        help="Which strategies to run (1=LHS, 2=BO, 3=Agent+LHS, 4=Agent+BO)")

    args = parser.parse_args()

    print("="*70)
    print("PHASE 3: STRATEGY COMPARISON")
    print("="*70)

    # Load Phase 2B screening data
    phase2b_summary = Path(args.phase2b_dir) / "phase2b_summary.json"
    if not phase2b_summary.exists():
        print(f"❌ Phase 2B results not found: {phase2b_summary}")
        return 1

    with open(phase2b_summary) as f:
        phase2b = json.load(f)

    # Flatten all seed results into screening data
    screening_data = []
    for nc_result in phase2b.get("results", []):
        for seed_result in nc_result.get("all_seed_results", []):
            if seed_result.get("status") == "ok":
                screening_data.append({
                    "nc": nc_result.get("nc"),
                    "seed_idx": seed_result.get("seed_idx"),
                    "metrics": seed_result.get("metrics", {}),
                    "feasible": True,  # Already filtered in Phase 2B
                })

    print(f"\nLoaded {len(screening_data)} feasible seed results from Phase 2B")

    # Create artifact directory
    Path(args.artifact_dir).mkdir(parents=True, exist_ok=True)

    # Run selected strategies
    strategies_map = {
        "1": Strategy1_RegularLHS(screening_data),
        "2": Strategy2_BO_Baseline(screening_data),
        "3": Strategy3_Agent_LHS(screening_data),
        "4": Strategy4_Agent_BO(screening_data),
    }

    results = {}
    for strategy_id in args.strategies:
        strategy = strategies_map[strategy_id]
        result = strategy.run(args.artifact_dir)
        results[strategy.name] = result

    # Summary
    print("\n" + "="*70)
    print("PHASE 3 COMPLETE - STRATEGY COMPARISON RESULTS")
    print("="*70)

    summary = {
        "screening_data_points": len(screening_data),
        "strategies_compared": args.strategies,
        "results": results,
    }

    summary_path = Path(args.artifact_dir) / "phase3_comparison_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\nResults saved to: {summary_path}")

    # Compare best J across strategies
    print("\nBest J by Strategy:")
    for strategy_name, result in results.items():
        best_j = result.get("best_j")
        if best_j:
            print(f"  {strategy_name}: {best_j:.2f}")
        else:
            print(f"  {strategy_name}: (not implemented yet)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
