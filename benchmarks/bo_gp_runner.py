"""
BO+GP Baseline Runner - Deterministic Bayesian Optimization with real IPOPT.

Runs SMB NC configuration optimization using Bayesian Optimization with GP.
Provides a baseline for comparison against agent-based and LHS-based methods.
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
from bo_gp_baseline import create_bo_gp_baseline, BOGPConfig
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


def run_bo_gp_baseline(
    run_name: str = "bo_gp_baseline",
    artifact_dir: str = "artifacts/bo_gp_baseline",
    benchmark_hours: float = 4.0,
    max_iterations: int = 20,
    solver_name: str = "auto",
    linear_solver: str = "ma97",
    nfex: int = 5,
    nfet: int = 2,
    ncp: int = 1,
    verbose: bool = True,
) -> int:
    """
    Run BO+GP baseline with real IPOPT evaluation.

    Args:
        run_name: Name of the run
        artifact_dir: Directory for artifacts
        benchmark_hours: Time budget (hours)
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

    log_path = artifact_path_obj / "bo_gp_log.json"
    results_path = artifact_path_obj / "bo_gp_results.json"

    # Generate config space
    config_space = list(generate_valid_constrained_configs(target_sum=8))
    if verbose:
        print(f"[BO+GP] Config space: {len(config_space)} valid configurations")

    # Create BO selector
    bo_config = BOGPConfig(
        n_initial_random=3,
        kernel_lengthscale=2.0,
        acquisition_type="ei",
    )
    selector = create_bo_gp_baseline(config_space, bo_config)

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

    # Optimization loop
    start_time = time.time()
    budget_seconds = benchmark_hours * 3600
    iteration = 0
    results = []

    if verbose:
        print(f"[BO+GP] Starting optimization loop (budget: {benchmark_hours:.1f}h)")
        print()

    while iteration < max_iterations:
        elapsed = time.time() - start_time
        if elapsed > budget_seconds:
            if verbose:
                print(f"[BO+GP] Budget exhausted ({elapsed:.1f}s > {budget_seconds:.1f}s)")
            break

        iteration += 1

        # Select next config
        config_idx, config = selector.select_next()

        if verbose:
            print(f"[BO+GP Iter {iteration:3d}] Selected: {config} (idx={config_idx})")

        # Evaluate config using real IPOPT
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

        # Use productivity for BO, or penalize if infeasible
        if productivity is not None:
            score = productivity
        else:
            # Penalty for infeasible/error cases
            score = 0.0

        selector.observe(config, score)

        best_val = max(selector.evaluated_values) if selector.evaluated_values else 0.0

        result = {
            "iteration": iteration,
            "config": config,
            "productivity": float(productivity) if productivity is not None else None,
            "purity": float(purity) if purity is not None else None,
            "recovery_ga": float(recovery_ga) if recovery_ga is not None else None,
            "recovery_ma": float(recovery_ma) if recovery_ma is not None else None,
            "eval_status": eval_result.get("status", "unknown"),
            "best_productivity": float(best_val),
            "elapsed_seconds": elapsed,
            "n_evaluated": len(selector.evaluated_values),
        }
        results.append(result)

        if verbose:
            print()

    # Save results
    with open(log_path, "w") as f:
        json.dump(results, f, indent=2)

    total_time = time.time() - start_time

    # Find best feasible result
    feasible_results = [r for r in results if r["productivity"] is not None]
    if feasible_results:
        best_result = max(feasible_results, key=lambda r: r["productivity"])
        best_config = best_result["config"]
        best_productivity = best_result["productivity"]
        best_purity = best_result["purity"]
        best_recovery_ga = best_result["recovery_ga"]
    else:
        best_config = None
        best_productivity = None
        best_purity = None
        best_recovery_ga = None

    summary = {
        "method": "BO+GP",
        "run_name": run_name,
        "iterations": iteration,
        "evaluated_iterations": len([r for r in results if r["eval_status"] == "ok"]),
        "feasible_iterations": len(feasible_results),
        "total_time_seconds": total_time,
        "config_space_size": len(config_space),
        "best_config": best_config,
        "best_productivity": best_productivity,
        "best_purity": best_purity,
        "best_recovery_ga": best_recovery_ga,
        "all_results": results,
    }

    with open(results_path, "w") as f:
        json.dump(summary, f, indent=2)

    if verbose:
        print("=" * 70)
        print(f"BO+GP Baseline Complete")
        print("=" * 70)
        print(f"Total evaluations: {iteration}")
        print(f"Evaluated successfully: {len([r for r in results if r['eval_status'] == 'ok'])}")
        print(f"Feasible solutions: {len(feasible_results)}")
        print(f"Best config: {best_config}")
        if best_productivity is not None:
            print(f"Best productivity: {best_productivity:.2f}")
            print(f"  Purity: {best_purity:.2f}, Recovery_GA: {best_recovery_ga:.2f}")
        else:
            print(f"No feasible solutions found")
        print(f"Total time: {total_time:.1f}s ({total_time/60:.1f} min)")
        print(f"Results saved to: {results_path}")
        print()

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="BO+GP Baseline with Real IPOPT")
    parser.add_argument("--run-name", default="bo_gp_baseline")
    parser.add_argument("--artifact-dir", default="artifacts/bo_gp_baseline")
    parser.add_argument("--benchmark-hours", type=float, default=4.0)
    parser.add_argument("--max-iterations", type=int, default=50)
    parser.add_argument("--solver-name", default="auto")
    parser.add_argument("--linear-solver", default="ma97")
    parser.add_argument("--nfex", type=int, default=5, help="Spatial discretization elements")
    parser.add_argument("--nfet", type=int, default=2, help="Time elements")
    parser.add_argument("--ncp", type=int, default=1, help="Collocation points")
    parser.add_argument("--verbose", action="store_true", default=True)

    args = parser.parse_args()

    return run_bo_gp_baseline(
        run_name=args.run_name,
        artifact_dir=args.artifact_dir,
        benchmark_hours=args.benchmark_hours,
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
