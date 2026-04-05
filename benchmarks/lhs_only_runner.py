"""
LHS-Only Runner - Pure LHS ranking without LLM/agent.

Runs SMB NC configuration evaluation using LHS-ranked configs.
No agent/LLM needed - deterministic baseline with physics guidance.
Evaluates configs in physics-ranked order (best candidates first).
"""

import argparse
import sys
import os
from pathlib import Path
import json
import time
from typing import Dict, List, Tuple

import numpy as np

# Setup path
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "benchmarks"))

from lhs_sampler import generate_valid_constrained_configs
from physics_filter import filter_and_rank_lhs_configs


def run_lhs_only_benchmark(
    run_name: str = "lhs_only_benchmark",
    artifact_dir: str = "artifacts/lhs_only_benchmark",
    max_iterations: int = 20,
    random_noise: float = 1.0,
    verbose: bool = True,
) -> int:
    """
    Run LHS-only benchmark (pure physics-based ranking, no agent).

    Args:
        run_name: Name of the run
        artifact_dir: Directory for artifacts
        max_iterations: Maximum iterations
        random_noise: Noise level in objective simulation
        verbose: Print progress

    Returns:
        Exit code
    """
    artifact_path = Path(artifact_dir)
    artifact_path.mkdir(parents=True, exist_ok=True)

    log_path = artifact_path / "lhs_only_log.json"
    results_path = artifact_path / "lhs_only_results.json"

    # Generate and score configs
    config_space = generate_valid_constrained_configs(target_sum=8)
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

    # Evaluation loop (just iterate through ranked list)
    start_time = time.time()
    results = []
    evaluated_set = set()

    for iteration, (config, physics_score, status) in enumerate(ranked_configs, 1):
        if iteration > max_iterations:
            break

        config_tuple = tuple(config)
        if config_tuple in evaluated_set:
            continue

        evaluated_set.add(config_tuple)

        # Simulate objective: use physics score + noise
        imbalance = max(config) - min(config)
        # Prefer balanced configs, use physics heuristic as prior
        simulated_score = physics_score + np.random.normal(0, random_noise)

        elapsed = time.time() - start_time

        result_dict = {
            "iteration": iteration,
            "config": config,
            "physics_score": float(physics_score),
            "physics_status": status,
            "simulated_score": float(simulated_score),
            "imbalance": imbalance,
            "elapsed_seconds": elapsed,
        }
        results.append(result_dict)

        best_simulated = max(r["simulated_score"] for r in results) if results else 0
        best_physics = min(r["physics_score"] for r in results) if results else 0

        if verbose:
            print(
                f"[{iteration:3d}] Config {config} | "
                f"Physics: {physics_score:.2f} | "
                f"Score: {simulated_score:.2f} | "
                f"Best: {best_simulated:.2f}"
            )

    # Save results
    with open(log_path, "w") as f:
        json.dump(results, f, indent=2)

    total_time = time.time() - start_time
    best_idx = np.argmax([r["simulated_score"] for r in results])
    best_config = results[best_idx]["config"]
    best_score = results[best_idx]["simulated_score"]

    summary = {
        "method": "LHS-Only (Physics Ranking)",
        "run_name": run_name,
        "iterations": len(results),
        "total_time_seconds": total_time,
        "config_space_size": len(config_space),
        "best_config": best_config,
        "best_simulated_score": float(best_score),
        "best_physics_score": float(results[best_idx]["physics_score"]),
        "all_results": results,
    }

    with open(results_path, "w") as f:
        json.dump(summary, f, indent=2)

    if verbose:
        print()
        print("=" * 70)
        print(f"LHS-Only Benchmark Complete")
        print("=" * 70)
        print(f"Iterations: {len(results)}")
        print(f"Best config: {best_config}")
        print(f"Best score: {best_score:.2f}")
        print(f"Total time: {total_time:.1f}s")
        print(f"Results saved to: {results_path}")
        print()

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="LHS-Only Benchmark (Physics Ranking)")
    parser.add_argument("--run-name", default="lhs_only_benchmark")
    parser.add_argument("--artifact-dir", default="artifacts/lhs_only_benchmark")
    parser.add_argument("--max-iterations", type=int, default=31)
    parser.add_argument("--random-noise", type=float, default=1.0)
    parser.add_argument("--verbose", action="store_true", default=True)

    args = parser.parse_args()

    return run_lhs_only_benchmark(
        run_name=args.run_name,
        artifact_dir=args.artifact_dir,
        max_iterations=args.max_iterations,
        random_noise=args.random_noise,
        verbose=args.verbose,
    )


if __name__ == "__main__":
    sys.exit(main())
