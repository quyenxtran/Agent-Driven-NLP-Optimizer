#!/usr/bin/env python3
"""
Phase 2: Parallel Seed Optimization with Checkpointing (High-Performance Version)

Strategy:
  - Use multiprocessing.Pool with N workers (default: 12)
  - Each worker runs 1 seed optimization sequentially
  - Each worker gets 2 MA97 threads (12 workers × 2 threads = 24 CPUs total)
  - Result: 12 seeds optimize in parallel
  - Expected speedup: 3x (47 hours → ~16 hours, or ~2.5-3 hours with good convergence)

Checkpointing:
  - Save results after EACH NC completes
  - Resume from last completed NC if job is restarted
  - Track completion in checkpoint JSON file

Thread allocation:
  - Total SLURM CPUs: 24
  - Workers: 12 (one per 2 CPUs)
  - OMP_NUM_THREADS per worker: 2
  - MA97 parallelization: 2 threads each
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from concurrent.futures import ProcessPoolExecutor, as_completed
import os

import numpy as np
from scipy.stats import qmc

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))


def generate_lhs_seeds(n_seeds: int = 100) -> List[Dict[str, float]]:
    """Generate N-D Latin Hypercube samples for flow space."""
    var_names = ["tstep", "ffeed", "fdes", "fex", "f1"]
    bounds = [(8.0, 12.0), (0.5, 2.5), (0.5, 2.5), (0.5, 2.5), (0.5, 5.0)]

    sampler = qmc.LatinHypercube(d=5, seed=42)
    samples = sampler.random(n=n_seeds)

    seeds = []
    for sample in samples:
        seed = {
            var_names[i]: bounds[i][0] + sample[i] * (bounds[i][1] - bounds[i][0])
            for i in range(5)
        }
        seeds.append(seed)

    return seeds


def format_nc(nc: List[int]) -> str:
    """Format NC config as string [a,b,c,d]"""
    return f"[{nc[0]},{nc[1]},{nc[2]},{nc[3]}]"


def optimize_seed_worker(args: Tuple) -> Dict:
    """
    Worker function for parallel optimization.

    Each worker gets OMP_NUM_THREADS=2 (set by parent before starting worker).
    Runs ONE seed optimization, blocks until complete.

    Args:
        args: (nc, seed, seed_idx, artifact_dir, timeout)

    Returns:
        {status, seed_idx, productivity, ...}
    """
    nc, seed, seed_idx, artifact_dir, timeout = args

    # Worker inherits OMP_NUM_THREADS=2 from parent process
    nc_str = format_nc(nc)
    run_name = f"phase2_parallel_nc_{nc_str}_seed_{seed_idx}"

    cmd = [
        sys.executable,
        "-m",
        "benchmarks.run_stage",
        "--stage",
        "optimize-layouts",
        "--run-name",
        run_name,
        "--artifact-dir",
        artifact_dir,
        "--nc",
        nc_str,
        "--solver-name",
        "ipopt",
        "--linear-solver",
        "ma97",
        "--nfex",
        "4",  # Standard low-fidelity
        "--nfet",
        "2",
        "--ncp",
        "1",
        "--purity-min",
        "0.15",
        "--recovery-ga-min",
        "0.15",
        "--recovery-ma-min",
        "0.15",
        "--tstep",
        f"{seed['tstep']:.4f}",
        "--ffeed",
        f"{seed['ffeed']:.4f}",
        "--fdes",
        f"{seed['fdes']:.4f}",
        "--fex",
        f"{seed['fex']:.4f}",
        "--f1",
        f"{seed['f1']:.4f}",
    ]

    try:
        result = subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "OMP_NUM_THREADS": "2"},  # 2 threads for this worker
        )

        if result.returncode == 0:
            for line in result.stdout.split("\n"):
                if '"artifact"' in line:
                    try:
                        artifact_data = json.loads(line)
                        artifact_path = artifact_data.get("artifact")
                        if artifact_path and Path(artifact_path).exists():
                            with open(artifact_path) as f:
                                artifact = json.load(f)

                            return {
                                "status": "ok",
                                "seed_idx": seed_idx,
                                "productivity": artifact.get("J_validated"),
                                "metrics": artifact.get("metrics", {}),
                                "artifact": artifact,
                            }
                    except (json.JSONDecodeError, KeyError):
                        pass

        return {"status": "error", "seed_idx": seed_idx}

    except subprocess.TimeoutExpired:
        return {"status": "timeout", "seed_idx": seed_idx}
    except Exception as e:
        return {"status": "exception", "seed_idx": seed_idx, "error": str(e)}


def optimize_nc_parallel(
    nc: List[int],
    artifact_dir: str,
    seeds: List[Dict[str, float]],
    timeout: int = 120,
    n_workers: int = 12,
    verbose: bool = True,
) -> Dict:
    """
    Optimize NC with LHS seeds using parallel workers.

    Args:
        nc: NC configuration
        artifact_dir: Output directory
        seeds: List of seed dictionaries
        timeout: Per-seed timeout (seconds)
        n_workers: Number of parallel workers (recommend: 12 for 24 CPUs)
        verbose: Print progress

    Returns:
        {nc, n_seeds, n_successful, best_seed_idx, productivity, ...}
    """
    nc_str = format_nc(nc)
    n_seeds = len(seeds)

    if verbose:
        print(f"\n{'='*70}")
        print(f"NC {nc_str}: {n_seeds} LHS seeds (PARALLEL with {n_workers} workers)")
        print(f"{'='*70}")
        print(f"Each worker: OMP_NUM_THREADS=2 (2 CPUs per worker)")
        print(f"Total CPUs used: {n_workers} workers × 2 threads = {n_workers * 2}")
        print(f"\nOptimizing with multiprocessing pool...")

    # Create task list: (nc, seed, seed_idx, artifact_dir, timeout)
    tasks = [(nc, seed, idx, artifact_dir, timeout) for idx, seed in enumerate(seeds)]

    optimization_results = []
    completed = 0

    # Use ProcessPoolExecutor with n_workers
    with ProcessPoolExecutor(max_workers=n_workers) as executor:
        # Submit all tasks
        futures = {executor.submit(optimize_seed_worker, task): task for task in tasks}

        # Process results as they complete
        for future in as_completed(futures):
            result = future.result()
            optimization_results.append(result)
            completed += 1

            if verbose and completed % 10 == 0:
                print(f"  Progress: {completed} / {n_seeds} seeds completed")

    # Find best result
    valid_results = [
        r for r in optimization_results
        if r.get("status") == "ok" and r.get("productivity") is not None
    ]

    if not valid_results:
        return {
            "nc": nc,
            "n_seeds": n_seeds,
            "n_successful": 0,
            "best_seed_idx": None,
            "productivity": None,
            "error": "No successful optimizations",
            "all_seed_results": optimization_results,
        }

    best = max(valid_results, key=lambda r: r.get("productivity", -float("inf")))

    if verbose:
        print(f"\n✓ Best result: seed {best['seed_idx']}, J={best['productivity']:.4f}")

    return {
        "nc": nc,
        "n_seeds": n_seeds,
        "n_successful": len(valid_results),
        "best_seed_idx": best["seed_idx"],
        "productivity": best["productivity"],
        "metrics": best.get("metrics", {}),
        "all_seed_results": optimization_results,
    }


def load_checkpoint(artifact_dir: str) -> Dict:
    """Load checkpoint file if it exists."""
    checkpoint_path = Path(artifact_dir) / "phase2_checkpoint.json"
    if checkpoint_path.exists():
        with open(checkpoint_path) as f:
            return json.load(f)
    return {"completed_ncs": [], "completed_results": []}


def save_checkpoint(artifact_dir: str, checkpoint: Dict):
    """Save checkpoint file."""
    checkpoint_path = Path(artifact_dir) / "phase2_checkpoint.json"
    with open(checkpoint_path, "w") as f:
        json.dump(checkpoint, f, indent=2, default=str)


def main():
    parser = argparse.ArgumentParser(description="Phase 2: Parallel LHS Optimization (Checkpointed)")
    parser.add_argument(
        "--ncs",
        nargs="+",
        default=[
            "[1,1,2,4]",
            "[1,1,3,3]",
            "[1,1,4,2]",
            "[1,2,1,4]",
            "[1,2,4,1]",
            "[1,3,1,3]",
            "[1,3,2,2]",
            "[2,1,2,3]",
            "[2,2,1,3]",
            "[2,2,2,2]",
            "[1,1,1,5]",
            "[1,1,5,1]",
            "[1,5,1,1]",
            "[5,1,1,1]",
            "[1,2,2,3]",
            "[1,2,3,2]",
            "[1,3,2,1]",
            "[2,1,1,4]",
            "[2,1,3,2]",
            "[2,1,4,1]",
            "[2,2,3,1]",
            "[2,3,1,2]",
            "[2,3,2,1]",
            "[3,1,1,3]",
            "[3,1,2,2]",
            "[3,1,3,1]",
            "[3,2,1,2]",
            "[3,2,2,1]",
            "[3,3,1,1]",
            "[4,1,1,2]",
            "[4,1,2,1]",
            "[4,2,1,1]",
        ],
        help="NC configs to optimize",
    )
    parser.add_argument("--n-seeds", type=int, default=100, help="LHS seeds per NC")
    parser.add_argument("--artifact-dir", default="artifacts/phase2_lhs_seeding")
    parser.add_argument("--timeout", type=int, default=120, help="Timeout per seed")
    parser.add_argument("--n-workers", type=int, default=12, help="Number of parallel workers (recommend 12 for 24 CPUs)")
    parser.add_argument("--verbose", action="store_true", default=True)
    parser.add_argument("--resume", action="store_true", help="Resume from last completed NC")

    args = parser.parse_args()

    # Parse NCs
    ncs = []
    for nc_str in args.ncs:
        nc_str = nc_str.strip("[]")
        nc = [int(x) for x in nc_str.split(",")]
        ncs.append(nc)

    artifact_dir = args.artifact_dir
    Path(artifact_dir).mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("PHASE 2: PARALLEL LHS OPTIMIZATION (WITH CHECKPOINTING)")
    print("=" * 70)
    print(f"\nNCs to optimize: {len(ncs)}")
    print(f"LHS seeds per NC: {args.n_seeds}")
    print(f"Parallel workers: {args.n_workers}")
    print(f"Threads per worker: 2 (OMP_NUM_THREADS=2)")
    print(f"Total CPUs: {args.n_workers * 2}")
    print(f"Expected speedup: ~{args.n_workers // 4}x (47 hours → ~{47 // (args.n_workers // 4)} hours)")
    print("")

    # Load checkpoint
    checkpoint = load_checkpoint(artifact_dir)
    completed_ncs = set(checkpoint.get("completed_ncs", []))

    if args.resume and completed_ncs:
        print(f"Resuming from checkpoint: {len(completed_ncs)} NCs already completed")
        # Skip completed NCs
        ncs_to_process = [nc for nc in ncs if format_nc(nc) not in completed_ncs]
        print(f"Remaining NCs to process: {len(ncs_to_process)}")
        print(f"Completed NCs: {sorted(completed_ncs)}")
    else:
        ncs_to_process = ncs
        checkpoint = {"completed_ncs": [], "completed_results": []}

    # Generate LHS seeds (same for all NCs)
    print(f"\nGenerating {args.n_seeds} LHS seeds...")
    lhs_seeds = generate_lhs_seeds(args.n_seeds)

    # Optimize each NC
    all_results = checkpoint.get("completed_results", [])
    for nc in ncs_to_process:
        result = optimize_nc_parallel(
            nc, artifact_dir, lhs_seeds, timeout=args.timeout, n_workers=args.n_workers, verbose=args.verbose
        )
        all_results.append(result)

        # Save checkpoint after each NC
        nc_str = format_nc(nc)
        checkpoint["completed_ncs"].append(nc_str)
        checkpoint["completed_results"] = all_results
        save_checkpoint(artifact_dir, checkpoint)

        if args.verbose:
            print(f"✓ Checkpoint saved: {nc_str}")

    # Save final summary
    summary = {
        "status": "ok",
        "stage": "phase2_parallel_checkpointed",
        "method": "Parallel seed optimization with multiprocessing + checkpointing",
        "n_lhs_seeds": args.n_seeds,
        "n_workers": args.n_workers,
        "omp_threads_per_worker": 2,
        "total_cpus_used": args.n_workers * 2,
        "ncs_tested": len(all_results),
        "results": all_results,
        "statistics": {
            "total_seeds": len(ncs) * args.n_seeds,
            "total_successful": sum(r.get("n_successful", 0) for r in all_results),
            "expected_speedup": f"~{args.n_workers // 4}x",
            "expected_runtime": f"~{47 // (args.n_workers // 4)} hours (vs 47 hours sequential)",
        },
    }

    output_file = Path(artifact_dir) / "phase2_summary.json"
    with open(output_file, "w") as f:
        json.dump(summary, f, indent=2, default=str)

    print("\n" + "=" * 70)
    print("✓ PHASE 2 PARALLEL OPTIMIZATION COMPLETE")
    print("=" * 70)
    print(f"\nResults: {output_file}")
    print(f"Total successful: {summary['statistics']['total_successful']} / {summary['statistics']['total_seeds']}")
    print(f"Expected speedup: {summary['statistics']['expected_speedup']}")
    print(f"Expected runtime: {summary['statistics']['expected_runtime']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
