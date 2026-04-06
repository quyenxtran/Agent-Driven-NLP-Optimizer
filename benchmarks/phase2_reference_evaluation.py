#!/usr/bin/env python3
"""
Phase 2: Reference Evaluation with 5D LHS Sampling

Strategy:
  - Generate 5D LHS seeds: [F1, ffeed, fdes, fex, tstep]
  - Use reference-eval (NOT optimize-layouts) - fixed flows, no optimization
  - 4 workers × OMP_NUM_THREADS=2 = 8 CPUs total
  - 32 NCs × 25 seeds = 800 total reference evaluations
  - Expected runtime: ~30-45 minutes
  - Medium fidelity: nfex=6, nfet=3, ncp=1

Purpose:
  Deterministic screening of design space at fixed operating points.
  No solver exploration - just evaluate metrics at LHS-sampled flow rates.
  Provides foundation data for Phase 3 strategy comparison.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from concurrent.futures import ProcessPoolExecutor, as_completed
import os

import numpy as np
from scipy.stats import qmc

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))


def generate_lhs_seeds(n_seeds: int = 25) -> List[Dict[str, float]]:
    """Generate 5D Latin Hypercube samples for flow space.

    Sample independent variables: [F1, ffeed, fdes, fex, tstep]
    Derive Fraf from mass balance equality: Fraf = Ffeed + Fdes - Fex
    Enforce bounds constraint: 0.5 ≤ Fraf ≤ 5.0 (required by SMB solver)
    Reject seeds violating Fraf bounds.

    Returns:
        List of Dict with keys: F1, ffeed, fdes, fex, tstep, fraf
    """
    var_names = ["F1", "ffeed", "fdes", "fex", "tstep"]
    bounds = [(0.5, 5.0), (0.5, 2.5), (0.5, 2.5), (0.5, 2.5), (8.0, 12.0)]
    fraf_bounds = (0.5, 5.0)

    sampler = qmc.LatinHypercube(d=5, seed=42)
    # Generate 2x samples to account for rejections
    samples = sampler.random(n=int(n_seeds * 2.0))

    seeds = []
    for sample in samples:
        seed = {
            var_names[i]: bounds[i][0] + sample[i] * (bounds[i][1] - bounds[i][0])
            for i in range(5)
        }
        # Derive Fraf from mass balance: Fraf = Ffeed + Fdes - Fex
        fraf = seed['ffeed'] + seed['fdes'] - seed['fex']

        # Enforce Fraf bounds (required by SMB solver)
        if fraf_bounds[0] <= fraf <= fraf_bounds[1]:
            seed['fraf'] = fraf
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


def evaluate_reference_worker(args: Tuple) -> Dict:
    """
    Worker function for parallel reference evaluation.

    Each worker gets OMP_NUM_THREADS=2 (set by parent before starting worker).
    Runs ONE seed evaluation at fixed flows (reference point), blocks until complete.

    Args:
        args: (nc, seed, seed_idx, artifact_dir, timeout, nfex, nfet, ncp)

    Returns:
        {status, seed_idx, metrics, feasible, artifact}
    """
    nc, seed, seed_idx, artifact_dir, timeout, nfex, nfet, ncp = args

    # Worker inherits OMP_NUM_THREADS=2 from parent process
    nc_str = format_nc(nc)
    nc_library_str = ",".join(str(x) for x in nc)
    run_name = f"phase2_ref_nc_{nc_str}_seed_{seed_idx}"

    # Format seed as: F1,Fdes,Fex,Ffeed,tstep (matching run_stage.py convention)
    # See benchmarks/run_stage.py line ~442 for seed library format
    cmd = [
        sys.executable,
        "-m",
        "benchmarks.run_stage",
        "--stage",
        "reference-eval",  # NOT optimize-layouts - evaluate at fixed flows
        "--run-name",
        run_name,
        "--artifact-dir",
        artifact_dir,
        "--nc",
        nc_library_str,
        "--f1",
        f"{seed['F1']:.4f}",
        "--fdes",
        f"{seed['fdes']:.4f}",
        "--fex",
        f"{seed['fex']:.4f}",
        "--ffeed",
        f"{seed['ffeed']:.4f}",
        "--tstep",
        f"{seed['tstep']:.4f}",
        "--solver-name",
        "ipopt",
        "--linear-solver",
        "ma97",
        "--nfex",
        str(nfex),
        "--nfet",
        str(nfet),
        "--ncp",
        str(ncp),
        "--tol",
        "1e-3",
        "--acceptable-tol",
        "1e-2",
        "--constr-viol-tol",
        "0.1",
        "--acceptable-constr-viol-tol",
        "0.1",
        "--dual-inf-tol",
        "1e-2",
        "--acceptable-dual-inf-tol",
        "0.1",
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

                            result_data = artifact.get("results", [{}])[0]
                            return {
                                "status": result_data.get("status"),
                                "seed_idx": seed_idx,
                                "metrics": result_data.get("metrics", {}),
                                "feasible": result_data.get("feasible", False),
                                "J_validated": result_data.get("J_validated"),
                                "artifact": artifact,
                            }
                    except (json.JSONDecodeError, KeyError):
                        pass

        return {"status": "error", "seed_idx": seed_idx}

    except subprocess.TimeoutExpired:
        return {"status": "timeout", "seed_idx": seed_idx}
    except Exception as e:
        return {"status": "exception", "seed_idx": seed_idx, "error": str(e)}


def evaluate_nc_parallel(
    nc: List[int],
    artifact_dir: str,
    seeds: List[Dict[str, float]],
    timeout: int = 120,
    n_workers: int = 4,
    nfex: int = 6,
    nfet: int = 3,
    ncp: int = 1,
    verbose: bool = True,
) -> Dict:
    """
    Evaluate NC with reference points using parallel workers.

    Args:
        nc: NC configuration
        artifact_dir: Output directory
        seeds: List of seed dictionaries (with F1, ffeed, fdes, fex, tstep)
        timeout: Per-seed timeout (seconds)
        n_workers: Number of parallel workers
        nfex, nfet, ncp: Discretization parameters
        verbose: Print progress

    Returns:
        {nc, n_seeds, n_successful, best_seed_idx, metrics, ...}
    """
    nc_str = format_nc(nc)
    n_seeds = len(seeds)

    if verbose:
        print(f"\n{'='*70}")
        print(f"NC {nc_str}: {n_seeds} reference seeds (PARALLEL with {n_workers} workers)")
        print(f"{'='*70}")
        print(f"Discretization: nfex={nfex}, nfet={nfet}, ncp={ncp}")
        print(f"Evaluating at fixed flows (no optimization)...")

    # Create task list: (nc, seed, seed_idx, artifact_dir, timeout, nfex, nfet, ncp)
    tasks = [(nc, seed, idx, artifact_dir, timeout, nfex, nfet, ncp) for idx, seed in enumerate(seeds)]

    evaluation_results = []
    completed = 0

    # Use ProcessPoolExecutor with n_workers
    with ProcessPoolExecutor(max_workers=n_workers) as executor:
        # Submit all tasks
        futures = {executor.submit(evaluate_reference_worker, task): task for task in tasks}

        # Process results as they complete
        for future in as_completed(futures):
            result = future.result()
            evaluation_results.append(result)
            completed += 1

            if verbose and completed % max(1, n_seeds // 5) == 0:
                print(f"  Progress: {completed} / {n_seeds} seeds completed")

    # Find best result (feasible, highest productivity)
    valid_results = [
        r for r in evaluation_results
        if r.get("status") == "ok" and r.get("J_validated") is not None
    ]

    if not valid_results:
        return {
            "nc": nc,
            "n_seeds": n_seeds,
            "n_successful": 0,
            "best_seed_idx": None,
            "productivity": None,
            "error": "No successful evaluations",
            "all_seed_results": evaluation_results,
        }

    best = max(valid_results, key=lambda r: r.get("J_validated", -float("inf")))

    if verbose:
        print(f"\n✓ Best result: seed {best['seed_idx']}, J={best['J_validated']:.4f}")

    return {
        "nc": nc,
        "n_seeds": n_seeds,
        "n_successful": len(valid_results),
        "best_seed_idx": best["seed_idx"],
        "productivity": best["J_validated"],
        "metrics": best.get("metrics", {}),
        "all_seed_results": evaluation_results,
    }


def main():
    parser = argparse.ArgumentParser(description="Phase 2: Reference Evaluation with 5D LHS")
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
        help="NC configs to evaluate",
    )
    parser.add_argument("--n-seeds", type=int, default=25, help="LHS seeds per NC")
    parser.add_argument("--artifact-dir", default="artifacts/phase2_lhs_seeding")
    parser.add_argument("--timeout", type=int, default=120, help="Timeout per seed")
    parser.add_argument("--n-workers", type=int, default=4, help="Number of parallel workers")
    parser.add_argument("--nfex", type=int, default=6, help="Spatial elements")
    parser.add_argument("--nfet", type=int, default=3, help="Finite elements in time")
    parser.add_argument("--ncp", type=int, default=1, help="Collocation points")
    parser.add_argument("--verbose", action="store_true", default=True)

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
    print("PHASE 2: REFERENCE EVALUATION WITH 5D LHS SAMPLING")
    print("=" * 70)
    print(f"\nNCs to evaluate: {len(ncs)}")
    print(f"LHS seeds per NC: {args.n_seeds}")
    print(f"Parallel workers: {args.n_workers}")
    print(f"Discretization: nfex={args.nfex}, nfet={args.nfet}, ncp={args.ncp}")
    print(f"Total evaluations: {len(ncs)} × {args.n_seeds} = {len(ncs) * args.n_seeds}")
    print("")

    # Generate LHS seeds (same for all NCs)
    print(f"Generating {args.n_seeds} 5D LHS seeds...")
    lhs_seeds = generate_lhs_seeds(args.n_seeds)
    print(f"✓ Generated {len(lhs_seeds)} valid seeds (Fraf within bounds)")
    print("")

    # Evaluate each NC
    all_results = []
    for i, nc in enumerate(ncs, 1):
        print(f"[{i:2d}/{len(ncs)}] Evaluating NC {format_nc(nc)}...")
        result = evaluate_nc_parallel(
            nc,
            artifact_dir,
            lhs_seeds,
            timeout=args.timeout,
            n_workers=args.n_workers,
            nfex=args.nfex,
            nfet=args.nfet,
            ncp=args.ncp,
            verbose=args.verbose,
        )
        all_results.append(result)

    # Save summary
    summary = {
        "status": "ok",
        "stage": "phase2_reference_evaluation",
        "method": "5D LHS reference evaluation (no optimization)",
        "n_lhs_seeds": args.n_seeds,
        "n_workers": args.n_workers,
        "discretization": {
            "nfex": args.nfex,
            "nfet": args.nfet,
            "ncp": args.ncp,
        },
        "lhs_bounds": {
            "F1": [0.5, 5.0],
            "ffeed": [0.5, 2.5],
            "fdes": [0.5, 2.5],
            "fex": [0.5, 2.5],
            "tstep": [8.0, 12.0],
            "fraf_derived": [0.5, 5.0],
        },
        "ncs_tested": len(all_results),
        "results": all_results,
        "statistics": {
            "total_evaluations": len(ncs) * args.n_seeds,
            "total_successful": sum(r.get("n_successful", 0) for r in all_results),
            "expected_feasible_rate": "~0.75",
        },
    }

    output_file = Path(artifact_dir) / "phase2_reference_summary.json"
    with open(output_file, "w") as f:
        json.dump(summary, f, indent=2, default=str)

    print("\n" + "=" * 70)
    print("✓ PHASE 2 REFERENCE EVALUATION COMPLETE")
    print("=" * 70)
    print(f"\nResults: {output_file}")
    print(f"Total successful: {summary['statistics']['total_successful']} / {summary['statistics']['total_evaluations']}")
    print(f"Success rate: {100 * summary['statistics']['total_successful'] / summary['statistics']['total_evaluations']:.1f}%")

    return 0


if __name__ == "__main__":
    sys.exit(main())
