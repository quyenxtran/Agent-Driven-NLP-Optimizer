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
    """Generate N-D Latin Hypercube samples for flow space.

    Only sample independent variables (tstep, ffeed, fdes, fex).
    Derive Fraf from mass balance equality: Fraf = Ffeed + Fdes - Fex
    Enforce bounds constraint: 0.5 ≤ Fraf ≤ 5.0 (required by SMB solver)
    Reject seeds violating Fraf bounds; derive F1 = Ffeed + Fraf
    """
    var_names = ["tstep", "ffeed", "fdes", "fex"]
    bounds = [(8.0, 12.0), (0.5, 2.5), (0.5, 2.5), (0.5, 2.5)]
    fraf_bounds = (0.5, 5.0)

    sampler = qmc.LatinHypercube(d=4, seed=42)
    # Generate 2x samples to account for rejections
    samples = sampler.random(n=int(n_seeds * 2.0))

    seeds = []
    for sample in samples:
        seed = {
            var_names[i]: bounds[i][0] + sample[i] * (bounds[i][1] - bounds[i][0])
            for i in range(4)
        }
        # Derive Fraf from mass balance: Fraf = Ffeed + Fdes - Fex
        fraf = seed['ffeed'] + seed['fdes'] - seed['fex']

        # Enforce Fraf bounds (required by SMB solver)
        if fraf_bounds[0] <= fraf <= fraf_bounds[1]:
            seed['f1'] = seed['ffeed'] + fraf
            seeds.append(seed)
            if len(seeds) >= n_seeds:
                break

    if len(seeds) < n_seeds:
        import warnings
        warnings.warn(f"Generated only {len(seeds)} seeds within Fraf bounds {fraf_bounds} (requested {n_seeds})")

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
        args: (nc, seed, seed_idx, artifact_dir, timeout, nfex, nfet, ncp, purity_min, recovery_min)

    Returns:
        {status, seed_idx, productivity, ...}
    """
    nc, seed, seed_idx, artifact_dir, timeout, nfex, nfet, ncp, purity_min, recovery_min = args

    # Worker inherits OMP_NUM_THREADS=2 from parent process
    nc_str = format_nc(nc)
    nc_library_str = ",".join(str(x) for x in nc)
    run_name = f"phase2_parallel_nc_{nc_str}_seed_{seed_idx}"

    # Build a single-element seed library from the LHS seed values to avoid NOTEBOOK_SEEDS
    # Format: F1,Fdes,Fex,Ffeed,tstep
    seed_library_str = f"{seed['f1']:.4f},{seed['fdes']:.4f},{seed['fex']:.4f},{seed['ffeed']:.4f},{seed['tstep']:.4f}"

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
        "--nc-library",
        nc_library_str,
        "--seed-library",
        seed_library_str,  # Pass single LHS seed instead of NOTEBOOK_SEEDS
        "--no-reference-gate",  # Disable reference gate for fast foundation data
        "--solver-name",
        "ipopt",
        "--linear-solver",
        "ma97",
        "--tol",
        "1e-3",  # Relaxed from 1e-6: allow 0.1% error for Phase 2 exploration
        "--acceptable-tol",
        "1e-2",  # Relaxed from 1e-5: allow 1% error for fast convergence
        "--constr-viol-tol",
        "1e-1",  # Relaxed from 1e-4: allow 10% constraint violation
        "--acceptable-constr-viol-tol",
        "0.1",  # Allow 10% constraint violation for Phase 2 screening
        "--dual-inf-tol",
        "1e-2",  # Relaxed from 1e-4: allow 1% dual infeasibility
        "--acceptable-dual-inf-tol",
        "0.1",  # Allow 10% dual infeasibility for Phase 2 screening
        "--nfex",
        str(nfex),
        "--nfet",
        str(nfet),
        "--ncp",
        str(ncp),
        "--purity-min",
        str(purity_min),
        "--recovery-ga-min",
        str(recovery_min),
        "--recovery-ma-min",
        str(recovery_min),
    ]

    try:
        result = subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "OMP_NUM_THREADS": "2"},
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
    nfex: int = 4,
    nfet: int = 2,
    ncp: int = 1,
    purity_min: float = 0.15,
    recovery_min: float = 0.15,
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
        nfex: Number of finite elements in space
        nfet: Number of finite elements in time
        ncp: Number of collocation points
        purity_min: Minimum purity constraint
        recovery_min: Minimum recovery constraint

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
        print(f"Discretization: nfex={nfex}, nfet={nfet}, ncp={ncp}")
        print(f"Constraints: purity≥{purity_min:.2f}, recovery≥{recovery_min:.2f}")
        print(f"\nOptimizing with multiprocessing pool...")

    # Create task list: (nc, seed, seed_idx, artifact_dir, timeout, nfex, nfet, ncp, purity_min, recovery_min)
    tasks = [(nc, seed, idx, artifact_dir, timeout, nfex, nfet, ncp, purity_min, recovery_min) for idx, seed in enumerate(seeds)]

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
    parser.add_argument("--nfex", type=int, default=4, help="Finite elements in space")
    parser.add_argument("--nfet", type=int, default=2, help="Finite elements in time")
    parser.add_argument("--ncp", type=int, default=1, help="Collocation points")
    parser.add_argument("--purity-min", type=float, default=0.15, help="Minimum purity constraint")
    parser.add_argument("--recovery-min", type=float, default=0.15, help="Minimum recovery constraint")
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
    print(f"Discretization: nfex={args.nfex}, nfet={args.nfet}, ncp={args.ncp}")
    print(f"Constraints: purity≥{args.purity_min:.2f}, recovery≥{args.recovery_min:.2f}")
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
            nc, artifact_dir, lhs_seeds, timeout=args.timeout, n_workers=args.n_workers, verbose=args.verbose,
            nfex=args.nfex, nfet=args.nfet, ncp=args.ncp, purity_min=args.purity_min, recovery_min=args.recovery_min
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
