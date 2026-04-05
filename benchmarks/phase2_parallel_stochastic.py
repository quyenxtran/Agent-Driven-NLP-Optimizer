#!/usr/bin/env python3
"""
Phase 2: Stochastic Parallel Optimization (32 CPUs, 16 workers)

Strategy:
  - 16 workers × 2 MA97 threads = 32 CPUs total
  - Generate all (NC, seed) combinations: 32 NCs × 100 seeds = 3,200 jobs
  - Randomly shuffle job pool
  - Each worker randomly picks from remaining jobs
  - Result: 16 seeds optimize in parallel across any NC
  - No dependency on NC ordering
  - Better load balancing: fast NCs don't idle, slow ones get multiple workers
  - Expected speedup: ~16x (47 hours → ~3 hours)

Advantages over sequential NC processing:
  1. Load balancing: Fast NCs don't leave workers idle
  2. Stochastic: Less sensitive to NC ordering
  3. Fault tolerance: Can restart missing (NC, seed) pairs independently
  4. Dynamic: Workers always have work if any jobs remain

Checkpointing:
  - Track completed (NC, seed) pairs instead of just completed NCs
  - Can resume from any missing combination
  - More granular than NC-level checkpointing
"""

import argparse
import json
import subprocess
import sys
import random
from pathlib import Path
from typing import Dict, List, Tuple, Set
from concurrent.futures import ProcessPoolExecutor, as_completed
import os

import numpy as np
from scipy.stats import qmc

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))


def generate_lhs_seeds(n_seeds: int = 100) -> List[Dict[str, float]]:
    """Generate N-D Latin Hypercube samples for flow space.

    Only sample independent variables (tstep, ffeed, fdes, fex).
    Derive F1 from mass balance: F1 = Fdes + Fex
    Enforce physical feasibility: Fraf = F1 - Ffeed = Fdes + Fex - Ffeed ≥ 0
    (reject seeds where Ffeed > Fdes + Fex)
    """
    var_names = ["tstep", "ffeed", "fdes", "fex"]
    bounds = [(8.0, 12.0), (0.5, 2.5), (0.5, 2.5), (0.5, 2.5)]

    sampler = qmc.LatinHypercube(d=4, seed=42)
    # Generate 50% extra samples to account for rejected seeds
    samples = sampler.random(n=int(n_seeds * 1.5))

    seeds = []
    for sample in samples:
        seed = {
            var_names[i]: bounds[i][0] + sample[i] * (bounds[i][1] - bounds[i][0])
            for i in range(4)
        }
        # Derive F1 from mass balance: F1 = Fdes + Fex
        seed['f1'] = seed['fdes'] + seed['fex']
        # Check physical feasibility: Fraf = F1 - Ffeed ≥ 0
        fraf = seed['f1'] - seed['ffeed']
        if fraf >= 0:
            seeds.append(seed)
            if len(seeds) >= n_seeds:
                break

    if len(seeds) < n_seeds:
        import warnings
        warnings.warn(f"Generated only {len(seeds)} feasible seeds (requested {n_seeds})")

    return seeds


def format_nc(nc: List[int]) -> str:
    """Format NC config as string [a,b,c,d]"""
    return f"[{nc[0]},{nc[1]},{nc[2]},{nc[3]}]"


def optimize_seed_worker(args: Tuple) -> Dict:
    """
    Worker function for parallel optimization.

    Each worker gets OMP_NUM_THREADS=2 (set by parent before starting worker).
    Runs ONE seed optimization for one NC, blocks until complete.

    Args:
        args: (nc, seed_idx, seed_dict, artifact_dir, timeout, nfex, nfet, ncp, purity_min, recovery_min)

    Returns:
        {status, nc, seed_idx, productivity, ...}
    """
    nc, seed_idx, seed_dict, artifact_dir, timeout, nfex, nfet, ncp, purity_min, recovery_min = args

    nc_str = format_nc(nc)
    # nc-library format is "a,b,c,d" (no brackets, comma-separated)
    nc_library_str = ",".join(str(x) for x in nc)
    run_name = f"phase2_stoch_nc_{nc_str}_seed_{seed_idx}"

    # Build a single-element seed library from the LHS seed values to avoid NOTEBOOK_SEEDS
    # Format: F1,Fdes,Fex,Ffeed,tstep
    fraf = seed_dict['fdes'] + seed_dict['fex'] - seed_dict['ffeed']  # Derived from mass balance
    seed_library_str = f"{seed_dict['f1']:.4f},{seed_dict['fdes']:.4f},{seed_dict['fex']:.4f},{seed_dict['ffeed']:.4f},{seed_dict['tstep']:.4f}"

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
                                "nc": nc,
                                "seed_idx": seed_idx,
                                "productivity": artifact.get("J_validated"),
                                "metrics": artifact.get("metrics", {}),
                                "artifact": artifact,
                            }
                    except (json.JSONDecodeError, KeyError):
                        pass

        return {"status": "error", "nc": nc, "seed_idx": seed_idx}

    except subprocess.TimeoutExpired:
        return {"status": "timeout", "nc": nc, "seed_idx": seed_idx}
    except Exception as e:
        return {"status": "exception", "nc": nc, "seed_idx": seed_idx, "error": str(e)}


def load_checkpoint(artifact_dir: str) -> Dict:
    """Load checkpoint file with completed (NC, seed) pairs."""
    checkpoint_path = Path(artifact_dir) / "phase2_checkpoint_stochastic.json"
    if checkpoint_path.exists():
        with open(checkpoint_path) as f:
            return json.load(f)
    return {"completed_pairs": [], "completed_results": {}}


def save_checkpoint(artifact_dir: str, checkpoint: Dict):
    """Save checkpoint file."""
    checkpoint_path = Path(artifact_dir) / "phase2_checkpoint_stochastic.json"
    with open(checkpoint_path, "w") as f:
        json.dump(checkpoint, f, indent=2, default=str)


def main():
    parser = argparse.ArgumentParser(description="Phase 2: Stochastic Parallel LHS Optimization (32 CPUs)")
    parser.add_argument(
        "--ncs",
        nargs="+",
        default=[
            "[1,1,2,4]", "[1,1,3,3]", "[1,1,4,2]", "[1,2,1,4]", "[1,2,4,1]",
            "[1,3,1,3]", "[1,3,2,2]", "[2,1,2,3]", "[2,2,1,3]", "[2,2,2,2]",
            "[1,1,1,5]", "[1,1,5,1]", "[1,5,1,1]", "[5,1,1,1]", "[1,2,2,3]",
            "[1,2,3,2]", "[1,3,2,1]", "[2,1,1,4]", "[2,1,3,2]", "[2,1,4,1]",
            "[2,2,3,1]", "[2,3,1,2]", "[2,3,2,1]", "[3,1,1,3]", "[3,1,2,2]",
            "[3,1,3,1]", "[3,2,1,2]", "[3,2,2,1]", "[3,3,1,1]", "[4,1,1,2]",
            "[4,1,2,1]", "[4,2,1,1]",
        ],
        help="NC configs to optimize",
    )
    parser.add_argument("--n-seeds", type=int, default=100, help="LHS seeds per NC")
    parser.add_argument("--artifact-dir", default="artifacts/phase2_lhs_seeding")
    parser.add_argument("--timeout", type=int, default=120, help="Timeout per seed")
    parser.add_argument("--n-workers", type=int, default=16, help="Number of parallel workers (16 for 32 CPUs)")
    parser.add_argument("--nfex", type=int, default=4, help="Finite elements in space")
    parser.add_argument("--nfet", type=int, default=2, help="Finite elements in time")
    parser.add_argument("--ncp", type=int, default=1, help="Collocation points")
    parser.add_argument("--purity-min", type=float, default=0.15, help="Minimum purity constraint")
    parser.add_argument("--recovery-min", type=float, default=0.15, help="Minimum recovery constraint")
    parser.add_argument("--verbose", action="store_true", default=True)
    parser.add_argument("--resume", action="store_true", help="Resume from checkpoint")

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
    print("PHASE 2: STOCHASTIC PARALLEL LHS OPTIMIZATION (32 CPUs)")
    print("=" * 70)
    print(f"\nNCs to optimize: {len(ncs)}")
    print(f"LHS seeds per NC: {args.n_seeds}")
    print(f"Total (NC, seed) combinations: {len(ncs) * args.n_seeds}")
    print(f"Parallel workers: {args.n_workers}")
    print(f"Threads per worker: 2 (OMP_NUM_THREADS=2)")
    print(f"Total CPUs: {args.n_workers * 2}")
    print(f"Discretization: nfex={args.nfex}, nfet={args.nfet}, ncp={args.ncp}")
    print(f"Constraints: purity≥{args.purity_min:.2f}, recovery≥{args.recovery_min:.2f}")
    print(f"Expected speedup: ~{args.n_workers}x (47 hours → ~{47 // args.n_workers} hours)")
    print("")

    # Load checkpoint
    checkpoint = load_checkpoint(artifact_dir)
    completed_pairs = set(checkpoint.get("completed_pairs", []))

    if args.resume and completed_pairs:
        print(f"Resuming from checkpoint: {len(completed_pairs)} (NC, seed) pairs completed")
    else:
        checkpoint = {"completed_pairs": [], "completed_results": {}}
        completed_pairs = set()

    # Generate LHS seeds (same for all NCs)
    print(f"Generating {args.n_seeds} LHS seeds...")
    lhs_seeds = generate_lhs_seeds(args.n_seeds)

    # Create job pool: all (NC, seed) combinations, excluding completed ones
    job_pool = []
    for nc in ncs:
        for seed_idx in range(args.n_seeds):
            nc_str = format_nc(nc)
            pair_key = f"{nc_str}:seed_{seed_idx}"
            if pair_key not in completed_pairs:
                job_pool.append((nc, seed_idx, lhs_seeds[seed_idx]))

    print(f"Total jobs in pool: {len(job_pool)}")

    if not job_pool:
        print("✅ All jobs completed!")
        return 0

    # Shuffle job pool for stochastic distribution
    random.shuffle(job_pool)

    # Create task arguments with fixed parameters
    tasks = [
        (nc, seed_idx, seed_dict, artifact_dir, args.timeout, args.nfex, args.nfet, args.ncp, args.purity_min, args.recovery_min)
        for nc, seed_idx, seed_dict in job_pool
    ]

    print(f"Shuffled job pool and queued for {args.n_workers} workers...")
    print(f"\nStarting optimization...")

    optimization_results = []
    completed = 0

    # Use ProcessPoolExecutor with stochastic job distribution
    with ProcessPoolExecutor(max_workers=args.n_workers) as executor:
        futures = {executor.submit(optimize_seed_worker, task): task for task in tasks}

        for future in as_completed(futures):
            result = future.result()
            optimization_results.append(result)
            completed += 1

            if result.get("status") == "ok":
                nc_str = format_nc(result["nc"])
                pair_key = f"{nc_str}:seed_{result['seed_idx']}"
                completed_pairs.add(pair_key)

            if args.verbose and completed % 10 == 0:
                pct = 100 * completed / len(job_pool)
                print(f"  Progress: {completed} / {len(job_pool)} jobs ({pct:.1f}%)")

    # Save checkpoint
    checkpoint["completed_pairs"] = list(completed_pairs)
    checkpoint["completed_results"] = {
        str(r.get("nc", [])): r for r in optimization_results if r.get("status") == "ok"
    }
    save_checkpoint(artifact_dir, checkpoint)

    # Reorganize results by NC for summary
    results_by_nc = {}
    for nc in ncs:
        nc_str = format_nc(nc)
        nc_results = [r for r in optimization_results if r.get("nc") == nc and r.get("status") == "ok"]

        if nc_results:
            best = max(nc_results, key=lambda r: r.get("productivity", -float("inf")))
            results_by_nc[nc_str] = {
                "nc": nc,
                "n_seeds": args.n_seeds,
                "n_successful": len(nc_results),
                "best_seed_idx": best["seed_idx"],
                "productivity": best["productivity"],
                "metrics": best.get("metrics", {}),
            }
        else:
            results_by_nc[nc_str] = {
                "nc": nc,
                "n_seeds": args.n_seeds,
                "n_successful": 0,
            }

    # Save final summary
    summary = {
        "status": "ok",
        "stage": "phase2_stochastic_parallel",
        "method": "Stochastic parallel optimization with 16 workers × 2 threads",
        "n_lhs_seeds": args.n_seeds,
        "n_workers": args.n_workers,
        "omp_threads_per_worker": 2,
        "total_cpus_used": args.n_workers * 2,
        "ncs_tested": len(results_by_nc),
        "discretization": {"nfex": args.nfex, "nfet": args.nfet, "ncp": args.ncp},
        "constraints": {"purity_min": args.purity_min, "recovery_min": args.recovery_min},
        "results": list(results_by_nc.values()),
        "statistics": {
            "total_seeds": len(ncs) * args.n_seeds,
            "total_successful": sum(r.get("n_successful", 0) for r in results_by_nc.values()),
            "expected_speedup": f"~{args.n_workers}x",
            "expected_runtime": f"~{47 // args.n_workers} hours (vs 47 hours sequential)",
        },
    }

    output_file = Path(artifact_dir) / "phase2_summary.json"
    with open(output_file, "w") as f:
        json.dump(summary, f, indent=2, default=str)

    print("\n" + "=" * 70)
    print("✓ PHASE 2 STOCHASTIC PARALLEL OPTIMIZATION COMPLETE")
    print("=" * 70)
    print(f"\nResults: {output_file}")
    print(f"Total successful: {summary['statistics']['total_successful']} / {summary['statistics']['total_seeds']}")
    print(f"Expected speedup: {summary['statistics']['expected_speedup']}")
    print(f"Expected runtime: {summary['statistics']['expected_runtime']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
