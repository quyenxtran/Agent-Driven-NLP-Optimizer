"""
LHS-Only Runner - Pure LHS ranking with real IPOPT evaluation.

Runs SMB NC configuration optimization using LHS-ranked configs with real IPOPT.
No agent/LLM needed - deterministic baseline with physics guidance.
Evaluates configs in physics-ranked order (best candidates first).
"""

import argparse
import sys
import os
from pathlib import Path
import json
import time
from typing import Dict, List, Tuple, Sequence

import numpy as np

# Setup path
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "benchmarks"))

from lhs_sampler import generate_valid_constrained_configs
from physics_filter import filter_and_rank_lhs_configs
from run_stage import build_parser, evaluate_candidate, parse_nc, artifact_path, write_artifact


def setup_benchmark_args(
    run_name: str,
    artifact_dir: str,
    solver_name: str = "auto",
    linear_solver: str = "ma97",
    nfex: int = 5,
    nfet: int = 2,
    ncp: int = 1,
) -> argparse.Namespace:
    """Create argument namespace for benchmark evaluations."""
    parser = build_parser()
    args = parser.parse_args([
        "--stage", "reference-eval",
        "--run-name", run_name,
        "--artifact-dir", artifact_dir,
        "--solver-name", solver_name,
        "--nfex", str(nfex),
        "--nfet", str(nfet),
        "--ncp", str(ncp),
        "--tee",  # Print solver output
    ])

    if linear_solver:
        args.linear_solver = linear_solver

    return args


def run_lhs_only_benchmark(
    run_name: str = "lhs_only_benchmark",
    artifact_dir: str = "artifacts/lhs_only_benchmark",
    max_iterations: int = 20,
    solver_name: str = "auto",
    linear_solver: str = "ma97",
    nfex: int = 5,
    nfet: int = 2,
    ncp: int = 1,
    verbose: bool = True,
) -> int:
    """
    Run LHS-only benchmark with real IPOPT evaluation.

    Args:
        run_name: Name of the run
        artifact_dir: Directory for artifacts
        max_iterations: Maximum iterations
        solver_name: Solver to use (auto, ipopt)
        linear_solver: Linear solver (ma57, ma97, mumps)
        nfex: Spatial discretization elements
        nfet: Time elements
        ncp: Collocation points
        verbose: Print progress

    Returns:
        Exit code
    """
    artifact_path_obj = Path(artifact_dir)
    artifact_path_obj.mkdir(parents=True, exist_ok=True)

    log_path = artifact_path_obj / "lhs_only_log.json"
    results_path = artifact_path_obj / "lhs_only_results.json"

    # Generate and score configs
    config_space = list(generate_valid_constrained_configs(target_sum=8))
    if verbose:
        print(f"[LHS-Only] Generated {len(config_space)} valid configurations")

    # Filter and rank using physics
    result = filter_and_rank_lhs_configs(
        config_space,
        n_keep=len(config_space),
        target_sum=8,
    )

    ranked_configs = result["top_n"]
    if verbose:
        print(f"[LHS-Only] Physics filter ranked {len(ranked_configs)} configs")
        print(f"[LHS-Only] Score range: {ranked_configs[-1][1]:.2f} to {ranked_configs[0][1]:.2f}")
        print()

    # Setup evaluation arguments
    args = setup_benchmark_args(
        run_name=run_name,
        artifact_dir=artifact_dir,
        solver_name=solver_name,
        linear_solver=linear_solver,
        nfex=nfex,
        nfet=nfet,
        ncp=ncp,
    )

    # Evaluation loop: iterate through ranked list
    start_time = time.time()
    results = []
    evaluated_set = set()

    for iteration, (config, physics_score, status) in enumerate(ranked_configs, 1):
        if iteration > max_iterations:
            if verbose:
                print(f"[LHS-Only] Reached max iterations ({max_iterations})")
            break

        config_tuple = tuple(config)
        if config_tuple in evaluated_set:
            continue

        evaluated_set.add(config_tuple)

        if verbose:
            print(f"[LHS-Only Iter {iteration:3d}] Evaluating nc={config} (physics_score={physics_score:.2f})")

        # Evaluate using real IPOPT
        eval_start = time.time()
        try:
            eval_result = evaluate_candidate(args, config)
            eval_time = time.time() - eval_start

            status_str = eval_result.get("status", "unknown")

            # Extract metrics: productivity, purity, recovery (from metrics dict)
            metrics = eval_result.get("metrics", {})
            productivity = metrics.get("productivity_ex_ga_ma", None)
            purity = metrics.get("purity_ex_meoh_free", None)
            recovery_ga = metrics.get("recovery_ex_GA", None)
            recovery_ma = metrics.get("recovery_ex_MA", None)

            if verbose:
                if productivity is not None:
                    print(f"               → Status: {status_str}, J={productivity:.2f}, Pu={purity:.2f}, RecGA={recovery_ga:.2f}, Time: {eval_time:.1f}s")
                else:
                    print(f"               → Status: {status_str}, Time: {eval_time:.1f}s")

        except Exception as e:
            eval_time = time.time() - eval_start
            eval_result = {"status": "error", "error": str(e)}
            productivity = purity = recovery_ga = recovery_ma = None
            if verbose:
                print(f"               → Error: {str(e)[:80]}, Time: {eval_time:.1f}s")

        elapsed = time.time() - start_time

        result_dict = {
            "iteration": iteration,
            "config": config,
            "physics_score": float(physics_score),
            "physics_status": status,
            "productivity": float(productivity) if productivity is not None else None,
            "purity": float(purity) if purity is not None else None,
            "recovery_ga": float(recovery_ga) if recovery_ga is not None else None,
            "recovery_ma": float(recovery_ma) if recovery_ma is not None else None,
            "eval_status": eval_result.get("status", "unknown"),
            "imbalance": max(config) - min(config),
            "elapsed_seconds": elapsed,
        }
        results.append(result_dict)

    # Save results
    with open(log_path, "w") as f:
        json.dump(results, f, indent=2)

    total_time = time.time() - start_time

    # Find best result (by productivity if available)
    best_config = None
    best_productivity = None
    best_purity = None
    best_recovery_ga = None
    best_idx = None

    feasible_results = [r for r in results if r["productivity"] is not None]
    if feasible_results:
        best_idx = max(range(len(feasible_results)), key=lambda i: feasible_results[i]["productivity"])
        best_config = feasible_results[best_idx]["config"]
        best_productivity = feasible_results[best_idx]["productivity"]
        best_purity = feasible_results[best_idx]["purity"]
        best_recovery_ga = feasible_results[best_idx]["recovery_ga"]
    elif results:
        best_idx = 0
        best_config = results[0]["config"]

    summary = {
        "method": "LHS-Only (Physics Ranking)",
        "run_name": run_name,
        "iterations": len(results),
        "evaluated_iterations": len([r for r in results if r["eval_status"] == "ok"]),
        "feasible_iterations": len(feasible_results),
        "total_time_seconds": total_time,
        "config_space_size": len(config_space),
        "best_config": best_config,
        "best_productivity": float(best_productivity) if best_productivity is not None else None,
        "best_purity": float(best_purity) if best_purity is not None else None,
        "best_recovery_ga": float(best_recovery_ga) if best_recovery_ga is not None else None,
        "all_results": results,
    }

    with open(results_path, "w") as f:
        json.dump(summary, f, indent=2)

    if verbose:
        print()
        print("=" * 70)
        print(f"LHS-Only Benchmark Complete")
        print("=" * 70)
        print(f"Total evaluations: {len(results)}")
        print(f"Evaluated successfully: {len([r for r in results if r['eval_status'] == 'ok'])}")
        print(f"Feasible solutions: {len(feasible_results)}")
        print(f"Best config: {best_config}")
        if best_productivity is not None:
            print(f"Best productivity: {best_productivity:.2f}")
            print(f"  Purity: {best_purity:.2f}, Recovery_GA: {best_recovery_ga:.2f}")
        else:
            print(f"No feasible solutions found at fixed flows")
        print(f"Total time: {total_time:.1f}s ({total_time/60:.1f} min)")
        print(f"Results saved to: {results_path}")
        print()

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="LHS-Only Benchmark (Physics Ranking + Real IPOPT)")
    parser.add_argument("--run-name", default="lhs_only_benchmark")
    parser.add_argument("--artifact-dir", default="artifacts/lhs_only_benchmark")
    parser.add_argument("--max-iterations", type=int, default=31)
    parser.add_argument("--solver-name", default="auto")
    parser.add_argument("--linear-solver", default="ma97")
    parser.add_argument("--nfex", type=int, default=5, help="Spatial discretization elements")
    parser.add_argument("--nfet", type=int, default=2, help="Time elements")
    parser.add_argument("--ncp", type=int, default=1, help="Collocation points")
    parser.add_argument("--verbose", action="store_true", default=True)

    args = parser.parse_args()

    return run_lhs_only_benchmark(
        run_name=args.run_name,
        artifact_dir=args.artifact_dir,
        max_iterations=args.max_iterations,
        solver_name=args.solver_name,
        linear_solver=args.linear_solver,
        nfex=args.nfex,
        nfet=args.nfet,
        ncp=args.ncp,
        verbose=args.verbose,
    )


if __name__ == "__main__":
    sys.exit(main())
