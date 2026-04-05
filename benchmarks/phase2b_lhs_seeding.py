#!/usr/bin/env python3
"""
Phase 2B: Optimization with LHS-Sampled Seeds

Instead of using fixed reference seeds, generate LHS-sampled seeds
across the 5-D continuous flow space for each NC.

For each NC:
  1. Generate 8 LHS-sampled seed points (tstep, ffeed, fdes, fex, f1)
  2. Run IPOPT optimization from each seed
  3. Collect best result
  4. Save to artifacts
"""

import argparse
import sys
import json
import subprocess
import tempfile
from pathlib import Path
from typing import List, Tuple, Dict

import numpy as np
from scipy.stats import qmc

# Setup path
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "benchmarks"))


def generate_lhs_seeds(n_seeds: int = 8) -> List[Dict[str, float]]:
    """
    Generate LHS-sampled seed points in 5-D flow space.

    Variables: [tstep, ffeed, fdes, fex, f1]
    Bounds: [8-12, 0.5-2.5, 0.5-2.5, 0.5-2.5, 0.5-5.0]
    """
    # Bounds for each variable
    bounds = [
        (8.0, 12.0),      # tstep
        (0.5, 2.5),       # ffeed
        (0.5, 2.5),       # fdes
        (0.5, 2.5),       # fex
        (0.5, 5.0),       # f1
    ]

    # Generate LHS samples
    sampler = qmc.LatinHypercube(d=5, seed=42)
    samples = sampler.random(n=n_seeds)

    # Scale to bounds
    seeds = []
    for sample in samples:
        seed = {
            "tstep": bounds[0][0] + sample[0] * (bounds[0][1] - bounds[0][0]),
            "ffeed": bounds[1][0] + sample[1] * (bounds[1][1] - bounds[1][0]),
            "fdes": bounds[2][0] + sample[2] * (bounds[2][1] - bounds[2][0]),
            "fex": bounds[3][0] + sample[3] * (bounds[3][1] - bounds[3][0]),
            "f1": bounds[4][0] + sample[4] * (bounds[4][1] - bounds[4][0]),
        }
        seeds.append(seed)

    return seeds


def format_nc(nc: List[int]) -> str:
    """Format NC config as string [a,b,c,d]"""
    return f"[{nc[0]},{nc[1]},{nc[2]},{nc[3]}]"


def run_optimization(
    nc: List[int],
    seed: Dict[str, float],
    seed_idx: int,
    artifact_dir: str,
    solver_name: str = "auto",
    linear_solver: str = "ma97",
    verbose: bool = True,
) -> Dict:
    """
    Run single optimization with given seed using run_stage.py
    """
    nc_str = format_nc(nc)
    seed_name = f"lhs_seed_{seed_idx}"
    run_name = f"phase2b_opt_nc_{nc_str}_seed_{seed_idx}"

    if verbose:
        print(f"  Seed {seed_idx}: tstep={seed['tstep']:.2f}, "
              f"ffeed={seed['ffeed']:.2f}, fdes={seed['fdes']:.2f}, "
              f"fex={seed['fex']:.2f}, f1={seed['f1']:.2f}")

    # Build command
    cmd = [
        sys.executable, "-m", "benchmarks.run_stage",
        "--stage", "optimize-layouts",
        "--run-name", run_name,
        "--artifact-dir", artifact_dir,
        "--nc", nc_str,
        "--solver-name", solver_name,
        "--linear-solver", linear_solver,
        "--nfex", "6",
        "--nfet", "3",
        "--ncp", "2",
        "--purity-min", "0.20",
        "--recovery-ga-min", "0.20",
        "--recovery-ma-min", "0.20",
        "--max-pump-flow", "3.0",
        # Set seed flows
        "--tstep", f"{seed['tstep']:.4f}",
        "--ffeed", f"{seed['ffeed']:.4f}",
        "--fdes", f"{seed['fdes']:.4f}",
        "--fex", f"{seed['fex']:.4f}",
        "--f1", f"{seed['f1']:.4f}",
    ]

    try:
        result = subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,  # 5 min per optimization
        )

        if result.returncode == 0:
            # Parse output to get artifact path
            for line in result.stdout.split('\n'):
                if '"artifact"' in line:
                    artifact_path = json.loads(line).get('artifact')
                    # Try to read the result
                    if artifact_path and Path(artifact_path).exists():
                        with open(artifact_path) as f:
                            artifact = json.load(f)
                        return {
                            "status": "ok",
                            "seed_idx": seed_idx,
                            "artifact": artifact,
                            "productivity": artifact.get("J_validated"),
                            "purity": artifact.get("metrics", {}).get("purity_ex_meoh_free"),
                            "recovery_ga": artifact.get("metrics", {}).get("recovery_ex_GA"),
                        }

        return {
            "status": "error",
            "seed_idx": seed_idx,
            "error": result.stderr[:200],
        }

    except subprocess.TimeoutExpired:
        return {"status": "timeout", "seed_idx": seed_idx}
    except Exception as e:
        return {"status": "exception", "seed_idx": seed_idx, "error": str(e)}


def optimize_nc_with_lhs_seeds(
    nc: List[int],
    artifact_dir: str,
    n_seeds: int = 8,
    solver_name: str = "auto",
    linear_solver: str = "ma97",
    verbose: bool = True,
) -> Dict:
    """
    Optimize single NC with multiple LHS-sampled seeds.
    Returns the best result.
    """
    nc_str = format_nc(nc)

    if verbose:
        print(f"\n{'='*70}")
        print(f"NC {nc_str}: Generating {n_seeds} LHS seeds and optimizing...")
        print(f"{'='*70}")

    # Generate LHS seeds
    seeds = generate_lhs_seeds(n_seeds=n_seeds)

    # Run optimization from each seed
    results = []
    for seed_idx, seed in enumerate(seeds):
        result = run_optimization(
            nc, seed, seed_idx, artifact_dir,
            solver_name=solver_name,
            linear_solver=linear_solver,
            verbose=verbose,
        )
        results.append(result)

        if result["status"] == "ok":
            prod = result.get("productivity")
            if prod is not None:
                if verbose:
                    print(f"             ✓ J={prod:.4f}, pu={result.get('purity', 'N/A'):.3f}")

    # Find best result
    valid_results = [r for r in results if r["status"] == "ok" and r.get("productivity") is not None]

    if valid_results:
        best = max(valid_results, key=lambda r: r["productivity"])

        if verbose:
            print(f"\nBest from {n_seeds} seeds: Seed {best['seed_idx']}")
            print(f"  Productivity: {best['productivity']:.4f}")
            print(f"  Purity: {best['purity']:.4f}")
            print(f"  Recovery_GA: {best['recovery_ga']:.4f}")

        return {
            "nc": nc,
            "n_seeds": n_seeds,
            "best_seed_idx": best["seed_idx"],
            "productivity": best["productivity"],
            "purity": best["purity"],
            "recovery_ga": best["recovery_ga"],
            "all_results": results,
        }
    else:
        if verbose:
            print(f"No feasible solutions from {n_seeds} seeds")

        return {
            "nc": nc,
            "n_seeds": n_seeds,
            "best_seed_idx": None,
            "productivity": None,
            "error": f"{sum(1 for r in results if r['status'] != 'ok')} seeds failed",
        }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Phase 2B: Optimize NCs with LHS-sampled seeds"
    )
    parser.add_argument("--ncs", nargs="+", default=[
        "[1,1,2,4]", "[1,1,3,3]", "[1,1,4,2]", "[1,2,1,4]", "[1,2,4,1]",
        "[1,3,1,3]", "[1,3,2,2]", "[2,1,2,3]", "[2,2,1,3]", "[2,2,2,2]",
    ], help="NC configs to optimize")
    parser.add_argument("--n-seeds", type=int, default=8, help="LHS seeds per NC")
    parser.add_argument("--artifact-dir", default="artifacts/phase2b_lhs_seeding")
    parser.add_argument("--solver-name", default="auto")
    parser.add_argument("--linear-solver", default="ma97")
    parser.add_argument("--verbose", action="store_true", default=True)

    args = parser.parse_args()

    # Parse NC strings to lists
    ncs = []
    for nc_str in args.ncs:
        # Handle "[1,2,3,4]" format
        nc_str = nc_str.strip("[]")
        nc = [int(x) for x in nc_str.split(",")]
        ncs.append(nc)

    artifact_dir = args.artifact_dir
    Path(artifact_dir).mkdir(parents=True, exist_ok=True)

    print("="*70)
    print("PHASE 2B: LHS-SEEDED OPTIMIZATION")
    print("="*70)
    print(f"NCs to optimize: {len(ncs)}")
    print(f"Seeds per NC: {args.n_seeds}")
    print(f"Total optimizations: {len(ncs) * args.n_seeds}")
    print(f"Artifacts: {artifact_dir}")
    print("")

    # Optimize each NC with LHS seeds
    all_results = []
    for nc in ncs:
        result = optimize_nc_with_lhs_seeds(
            nc, artifact_dir,
            n_seeds=args.n_seeds,
            solver_name=args.solver_name,
            linear_solver=args.linear_solver,
            verbose=args.verbose,
        )
        all_results.append(result)

    # Save summary
    summary = {
        "method": "Phase 2B: LHS-Seeded Optimization",
        "n_ncs": len(ncs),
        "n_seeds_per_nc": args.n_seeds,
        "total_optimizations": len(ncs) * args.n_seeds,
        "results": all_results,
        "best_overall": max(
            [r for r in all_results if r.get("productivity") is not None],
            key=lambda r: r["productivity"],
            default=None,
        ),
    }

    summary_path = Path(artifact_dir) / "phase2b_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "="*70)
    print("PHASE 2B COMPLETE")
    print("="*70)
    print(f"Results saved to: {summary_path}")

    if summary["best_overall"]:
        best = summary["best_overall"]
        print(f"\nBest overall:")
        print(f"  NC: {best['nc']}")
        print(f"  Productivity: {best['productivity']:.4f}")
        print(f"  Purity: {best['purity']:.4f}")
        print(f"  Recovery_GA: {best['recovery_ga']:.4f}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
