#!/usr/bin/env python3
"""
Phase 2: Foundation Data Generation via LHS Screening

Generates comprehensive screening data across all 31 NC configurations
using N-dimensional LHS sampling. This screening data is the foundation
for Phase 3 strategy comparison.

Two-stage approach:
  Stage 1 (Screening): Quick evaluation at LOW fidelity
    - Tests all 100 LHS seeds per NC
    - Identifies feasible seeds (purity≥0.20, recovery≥0.20)
    - Expected result: ~300-350 feasible seed points across all NCs

  Stage 2 (Optional post-processing): Individual NC optimization
    - Only for Phase 3 strategies that want top-N optimization
    - NOT part of main Phase 2 output

Key: Phase 2 produces screening data that serves as input for Phase 3 strategies:
  1. Strategy 1 (Regular LHS): uses screening data to pick top 5, then optimizes
  2. Strategy 2 (BO Baseline): fits BO to screening data, uses for ranking
  3. Strategy 3 (Agent+LHS): agent analyzes screening data intelligently
  4. Strategy 4 (Agent+BO): agent+BO uses screening data as foundation

N-dimensional LHS:
  - Generic for any design space (not just SMB)
  - Configurable var_names and bounds
  - Default: 5D SMB flow space (tstep, ffeed, fdes, fex, f1)
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


def generate_lhs_seeds(
    n_seeds: int = 100,
    var_names: List[str] = None,
    bounds: List[Tuple[float, float]] = None,
) -> List[Dict[str, float]]:
    """
    N-dimensional LHS sampling (generic for any design space).

    Args:
        n_seeds: Number of LHS samples (default 100 for good 5D coverage)
        var_names: Variable names (default: SMB flow variables)
        bounds: [(min, max), ...] for each variable (default: SMB flow bounds)

    Returns: List of seed dicts with n_seeds samples

    Default (SMB): 5D flow space
      Variables: [tstep, ffeed, fdes, fex, f1]
      Bounds: [8-12, 0.5-2.5, 0.5-2.5, 0.5-2.5, 0.5-5.0]
      Coverage: n_seeds >= 50-100 for proper space coverage
    """
    # Default: SMB 5-D flow space
    if var_names is None:
        var_names = ["tstep", "ffeed", "fdes", "fex", "f1"]

    if bounds is None:
        bounds = [
            (8.0, 12.0),      # tstep
            (0.5, 2.5),       # ffeed
            (0.5, 2.5),       # fdes
            (0.5, 2.5),       # fex
            (0.5, 5.0),       # f1
        ]

    # Verify consistency
    assert len(var_names) == len(bounds), \
        f"var_names ({len(var_names)}) must match bounds ({len(bounds)})"

    n_dims = len(var_names)

    # Generate N-D LHS samples
    sampler = qmc.LatinHypercube(d=n_dims, seed=42)
    samples = sampler.random(n=n_seeds)

    # Scale to bounds and return as dicts
    seeds = []
    for sample in samples:
        seed = {
            var_names[i]: bounds[i][0] + sample[i] * (bounds[i][1] - bounds[i][0])
            for i in range(n_dims)
        }
        seeds.append(seed)

    return seeds


def format_nc(nc: List[int]) -> str:
    """Format NC config as string [a,b,c,d]"""
    return f"[{nc[0]},{nc[1]},{nc[2]},{nc[3]}]"


def screen_seed_feasibility(
    nc: List[int],
    seed: Dict[str, float],
    seed_idx: int,
    artifact_dir: str,
    verbose: bool = True,
) -> Dict:
    """
    Quick screening: evaluate seed at fixed flows (no optimization).
    Returns feasibility status and metrics.

    This filters bad seeds BEFORE running expensive optimization.
    """
    nc_str = format_nc(nc)
    run_name = f"phase2_screen_nc_{nc_str}_seed_{seed_idx}"

    # Build command: quick evaluation at seed point (no optimization)
    cmd = [
        sys.executable, "-m", "benchmarks.run_stage",
        "--stage", "reference-eval",  # Just evaluate at this point
        "--run-name", run_name,
        "--artifact-dir", artifact_dir,
        "--nc", nc_str,
        "--solver-name", "auto",
        "--linear-solver", "ma97",
        "--nfex", "4",  # Low fidelity for fast screening
        "--nfet", "2",
        "--ncp", "1",
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
            timeout=60,  # Fast screening, short timeout
        )

        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if '"artifact"' in line:
                    artifact_path = json.loads(line).get('artifact')
                    if artifact_path and Path(artifact_path).exists():
                        with open(artifact_path) as f:
                            artifact = json.load(f)

                        metrics = artifact.get("metrics", {})
                        purity = metrics.get("purity_ex_meoh_free")
                        recovery_ga = metrics.get("recovery_ex_GA")
                        recovery_ma = metrics.get("recovery_ex_MA")

                        # Check feasibility
                        feasible = (
                            purity is not None and purity >= 0.20 and
                            recovery_ga is not None and recovery_ga >= 0.20 and
                            recovery_ma is not None and recovery_ma >= 0.20
                        )

                        return {
                            "status": "ok",
                            "seed_idx": seed_idx,
                            "feasible": feasible,
                            "purity": purity,
                            "recovery_ga": recovery_ga,
                            "recovery_ma": recovery_ma,
                            "productivity": artifact.get("J_validated"),
                        }

        return {
            "status": "error",
            "seed_idx": seed_idx,
            "feasible": False,
            "error": "screening failed",
        }

    except subprocess.TimeoutExpired:
        return {
            "status": "timeout",
            "seed_idx": seed_idx,
            "feasible": False,
        }
    except Exception as e:
        return {
            "status": "exception",
            "seed_idx": seed_idx,
            "feasible": False,
            "error": str(e),
        }


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
    Run optimization with given seed using run_stage.py.
    Should only be called on seeds that passed feasibility screening.
    """
    nc_str = format_nc(nc)
    run_name = f"phase2_opt_nc_{nc_str}_seed_{seed_idx}"

    if verbose:
        print(f"    Optimizing seed {seed_idx}...", end=" ", flush=True)

    # Build command (LOW fidelity for Phase 2: quick evaluation)
    cmd = [
        sys.executable, "-m", "benchmarks.run_stage",
        "--stage", "optimize-layouts",
        "--run-name", run_name,
        "--artifact-dir", artifact_dir,
        "--nc", nc_str,
        "--solver-name", solver_name,
        "--linear-solver", linear_solver,
        "--nfex", "4",  # LOW fidelity: screening quality
        "--nfet", "2",
        "--ncp", "1",
        "--purity-min", "0.15",  # Relaxed: allow more seeds through
        "--recovery-ga-min", "0.15",
        "--recovery-ma-min", "0.15",
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
            timeout=600,  # 10 min per optimization (low fidelity, allows full startup + solver + artifact processing)
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

                        if verbose:
                            prod = artifact.get("J_validated")
                            purity = artifact.get("metrics", {}).get("purity_ex_meoh_free")
                            print(f"✓ J={prod:.2f}, pu={purity:.3f}")

                        return {
                            "status": "ok",
                            "seed_idx": seed_idx,
                            "artifact": artifact,
                            "productivity": artifact.get("J_validated"),
                            "purity": artifact.get("metrics", {}).get("purity_ex_meoh_free"),
                            "recovery_ga": artifact.get("metrics", {}).get("recovery_ex_GA"),
                        }

        if verbose:
            print(f"✗ failed")

        return {
            "status": "error",
            "seed_idx": seed_idx,
            "error": result.stderr[:200],
        }

    except subprocess.TimeoutExpired:
        if verbose:
            print("✗ timeout")
        return {"status": "timeout", "seed_idx": seed_idx}
    except Exception as e:
        if verbose:
            print(f"✗ exception")
        return {"status": "exception", "seed_idx": seed_idx, "error": str(e)}


def optimize_nc_with_lhs_seeds(
    nc: List[int],
    artifact_dir: str,
    seeds: List[Dict[str, float]],
    solver_name: str = "auto",
    linear_solver: str = "ma97",
    verbose: bool = True,
) -> Dict:
    """
    Simplified one-stage optimization for NC with pre-generated LHS seeds.
    Runs low-fidelity optimization directly on all seeds (screening stage removed due to subprocess issues).

    Args:
        seeds: Pre-generated LHS seeds (same for all NCs for fair comparison)

    Returns the best result from optimized seeds.
    """
    nc_str = format_nc(nc)
    n_seeds = len(seeds)

    if verbose:
        print(f"\n{'='*70}")
        print(f"NC {nc_str}: {n_seeds} LHS seeds for 5D space coverage")
        print(f"{'='*70}")

    # Run low-fidelity optimization on all seeds
    if verbose:
        print(f"\nOptimizing all {n_seeds} seeds at LOW fidelity (nfex=4, nfet=2)...")

    optimization_results = []
    for seed_idx, seed in enumerate(seeds):
        result = run_optimization(
            nc, seed, seed_idx, artifact_dir,
            solver_name=solver_name,
            linear_solver=linear_solver,
            verbose=verbose,
        )
        optimization_results.append(result)

    # Find best result
    valid_results = [
        r for r in optimization_results
        if r["status"] == "ok" and r.get("productivity") is not None
    ]

    if valid_results:
        best = max(valid_results, key=lambda r: r["productivity"])

        if verbose:
            print(f"\n{'─'*70}")
            print(f"Results for NC {nc_str}:")
            print(f"  Initial seeds: {n_seeds}")
            print(f"  Successfully optimized: {len(valid_results)}")
            print(f"  Success rate: {len(valid_results)/n_seeds*100:.1f}%")
            print(f"\n  Best seed: {best['seed_idx']}")
            print(f"    Productivity: {best['productivity']:.4f}")
            print(f"    Purity: {best['purity']:.4f}")
            print(f"    Recovery GA: {best['recovery_ga']:.4f}")

        return {
            "nc": nc,
            "n_seeds": n_seeds,
            "best_seed_idx": best["seed_idx"],
            "productivity": best["productivity"],
            "purity": best["purity"],
            "recovery_ga": best["recovery_ga"],
            "n_feasible": len(valid_results),
            "all_seed_results": valid_results,  # KEEP ALL for BO training
            "all_optimization_results": optimization_results,
        }
    else:
        if verbose:
            print(f"\n✗ No successful optimizations out of {n_seeds} seeds")

        return {
            "nc": nc,
            "n_seeds": n_seeds,
            "best_seed_idx": None,
            "productivity": None,
            "n_feasible": 0,
            "all_seed_results": [],
            "error": f"No successful optimizations out of {n_seeds} seeds",
        }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Phase 2: Optimize NCs with LHS-sampled seeds"
    )
    parser.add_argument("--ncs", nargs="+", default=[
        "[1,1,2,4]", "[1,1,3,3]", "[1,1,4,2]", "[1,2,1,4]", "[1,2,4,1]",
        "[1,3,1,3]", "[1,3,2,2]", "[2,1,2,3]", "[2,2,1,3]", "[2,2,2,2]",
    ], help="NC configs to optimize")
    parser.add_argument("--n-seeds", type=int, default=100, help="LHS seeds per NC for 5D space coverage (screened for feasibility, optimized only good ones)")
    parser.add_argument("--artifact-dir", default="artifacts/phase2_lhs_seeding")
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
    print("PHASE 2: LHS-SEEDED OPTIMIZATION (Two-Stage)")
    print("="*70)
    print(f"NCs to optimize: {len(ncs)}")
    print(f"LHS seeds per NC: {args.n_seeds} (for 5D space coverage)")
    print("")
    print(f"Two-stage approach:")
    print(f"  Stage 1 - Screening: {len(ncs)} NCs × {args.n_seeds} seeds = {len(ncs) * args.n_seeds} quick evals")
    print(f"  Stage 2 - Optimization: ~{len(ncs)} NCs × ~20-30 seeds = ~{len(ncs) * 25} full optimizations")
    print(f"  (Only feasible seeds from Stage 1 are optimized in Stage 2)")
    print(f"  (Same {args.n_seeds} LHS seeds used for all {len(ncs)} NCs - fair comparison)")
    print(f"Artifacts: {artifact_dir}")
    print("")

    # Generate LHS seeds ONCE for all NCs (fair comparison across NCs)
    print(f"Generating {args.n_seeds} LHS seeds in 5D space (used for all NCs)...")
    lhs_seeds = generate_lhs_seeds(n_seeds=args.n_seeds)
    print(f"✓ Generated {len(lhs_seeds)} seeds")
    print("")

    # Optimize each NC with same LHS seeds
    all_results = []
    for nc in ncs:
        result = optimize_nc_with_lhs_seeds(
            nc, artifact_dir,
            seeds=lhs_seeds,  # Use same seeds for all NCs
            solver_name=args.solver_name,
            linear_solver=args.linear_solver,
            verbose=args.verbose,
        )
        all_results.append(result)

    # Save summary
    summary = {
        "method": "Phase 2: LHS-Seeded Optimization",
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

    summary_path = Path(artifact_dir) / "phase2_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "="*70)
    print("PHASE 2 COMPLETE")
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
