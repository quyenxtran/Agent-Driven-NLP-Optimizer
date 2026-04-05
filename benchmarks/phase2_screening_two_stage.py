#!/usr/bin/env python3
"""
Phase 2: Two-Stage Screening
Stage 1: Quick feasibility check (single-point reference evaluation)
Stage 2: Full optimization only on feasible seeds

This dramatically reduces computational cost by:
- Eliminating optimization for clearly infeasible seeds
- Focusing effort on promising regions
- Maintaining 5D coverage across feasible space
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple

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


def stage1_feasibility_check(
    nc: List[int],
    seed: Dict[str, float],
    seed_idx: int,
    artifact_dir: str,
    verbose: bool = True,
) -> Dict:
    """
    Stage 1: Quick feasibility check using reference single-point evaluation.

    Runs low-fidelity optimization with VERY relaxed constraints to see if
    the seed can produce ANY feasible result. If it fails here, skip full optimization.

    Returns: {status, seed_idx, feasible, metrics (if feasible)}
    """
    nc_str = format_nc(nc)
    run_name = f"phase2_s1_check_nc_{nc_str}_seed_{seed_idx}"

    if verbose:
        print(f"    [S1] seed {seed_idx:3d}... ", end="", flush=True)

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
        "3",  # Ultra-low fidelity for quick screening
        "--nfet",
        "1",
        "--ncp",
        "1",
        "--purity-min",
        "0.05",  # VERY relaxed: just see if feasible at all
        "--recovery-ga-min",
        "0.05",
        "--recovery-ma-min",
        "0.05",
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
            timeout=120,  # Feasibility check (ultra-low fidelity, but still ~60-80s)
        )

        if result.returncode == 0:
            # Parse to confirm feasibility
            for line in result.stdout.split("\n"):
                if '"artifact"' in line:
                    try:
                        artifact_data = json.loads(line)
                        artifact_path = artifact_data.get("artifact")
                        if artifact_path and Path(artifact_path).exists():
                            with open(artifact_path) as f:
                                artifact = json.load(f)

                            metrics = artifact.get("metrics", {})
                            purity = metrics.get("purity_ex_meoh_free", 0)

                            if purity > 0.05:  # Passed feasibility
                                if verbose:
                                    print(f"✓ FEASIBLE")
                                return {
                                    "status": "feasible",
                                    "seed_idx": seed_idx,
                                    "feasible": True,
                                }
                            else:
                                if verbose:
                                    print(f"✗ infeasible")
                                return {
                                    "status": "infeasible",
                                    "seed_idx": seed_idx,
                                    "feasible": False,
                                }
                    except (json.JSONDecodeError, KeyError):
                        pass

        if verbose:
            print(f"✗ failed")
        return {"status": "error", "seed_idx": seed_idx, "feasible": False}

    except subprocess.TimeoutExpired:
        if verbose:
            print(f"✗ timeout")
        return {"status": "timeout", "seed_idx": seed_idx, "feasible": False}
    except Exception as e:
        if verbose:
            print(f"✗ exception")
        return {"status": "exception", "seed_idx": seed_idx, "feasible": False, "error": str(e)}


def stage2_full_optimization(
    nc: List[int],
    seed: Dict[str, float],
    seed_idx: int,
    artifact_dir: str,
    timeout: int = 120,
    verbose: bool = True,
) -> Dict:
    """
    Stage 2: Full optimization on feasible seeds.

    Runs low-fidelity optimization with standard constraints.
    Only called for seeds that passed Stage 1 feasibility check.
    """
    nc_str = format_nc(nc)
    run_name = f"phase2_s2_opt_nc_{nc_str}_seed_{seed_idx}"

    if verbose:
        print(f"    [S2] seed {seed_idx:3d}... ", end="", flush=True)

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
        "0.15",  # Standard constraints
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

                            if verbose:
                                prod = artifact.get("J_validated", 0)
                                purity = artifact.get("metrics", {}).get("purity_ex_meoh_free", 0)
                                print(f"✓ J={prod:.2f}, pu={purity:.3f}")

                            return {
                                "status": "ok",
                                "seed_idx": seed_idx,
                                "artifact": artifact,
                                "productivity": artifact.get("J_validated"),
                                "metrics": artifact.get("metrics", {}),
                            }
                    except (json.JSONDecodeError, KeyError):
                        pass

        if verbose:
            print(f"✗ failed")
        return {"status": "error", "seed_idx": seed_idx}

    except subprocess.TimeoutExpired:
        if verbose:
            print(f"✗ timeout")
        return {"status": "timeout", "seed_idx": seed_idx}
    except Exception as e:
        if verbose:
            print(f"✗ exception")
        return {"status": "exception", "seed_idx": seed_idx, "error": str(e)}


def optimize_nc_two_stage(
    nc: List[int],
    artifact_dir: str,
    seeds: List[Dict[str, float]],
    timeout: int = 120,
    verbose: bool = True,
) -> Dict:
    """
    Two-stage optimization for NC with LHS seeds.

    Stage 1: Screen all seeds for feasibility (fast, ~10s each)
    Stage 2: Full optimize only feasible seeds (~50s each)

    Result: Only feasible seeds fully optimized, saving ~50% runtime
    """
    nc_str = format_nc(nc)
    n_seeds = len(seeds)

    if verbose:
        print(f"\n{'='*70}")
        print(f"NC {nc_str}: {n_seeds} LHS seeds (TWO-STAGE screening)")
        print(f"{'='*70}")

    # STAGE 1: Feasibility screening
    if verbose:
        print(f"\nSTAGE 1: Feasibility screening (quick check, ~10s each)...")

    feasible_indices = []
    stage1_results = []

    for seed_idx, seed in enumerate(seeds):
        result = stage1_feasibility_check(nc, seed, seed_idx, artifact_dir, verbose=verbose)
        stage1_results.append(result)

        if result.get("feasible"):
            feasible_indices.append(seed_idx)

    n_feasible = len(feasible_indices)
    if verbose:
        print(f"\n✓ Stage 1 complete: {n_feasible} / {n_seeds} seeds feasible ({100*n_feasible/n_seeds:.0f}%)")

    # STAGE 2: Full optimization only on feasible seeds
    if verbose:
        print(f"\nSTAGE 2: Full optimization ({n_feasible} feasible seeds, ~50s each)...")

    optimization_results = []
    for seed_idx in feasible_indices:
        seed = seeds[seed_idx]
        result = stage2_full_optimization(nc, seed, seed_idx, artifact_dir, timeout=timeout, verbose=verbose)
        optimization_results.append(result)

    # Find best result
    valid_results = [r for r in optimization_results if r["status"] == "ok" and r.get("productivity") is not None]

    if not valid_results:
        return {
            "nc": nc,
            "n_seeds": n_seeds,
            "n_feasible_stage1": n_feasible,
            "n_successful_stage2": 0,
            "best_seed_idx": None,
            "productivity": None,
            "error": "No successful optimizations",
            "all_seed_results": [],
        }

    best = max(valid_results, key=lambda r: r.get("productivity", -float("inf")))

    if verbose:
        print(f"\n✓ Best result: seed {best['seed_idx']}, J={best['productivity']:.4f}")

    return {
        "nc": nc,
        "n_seeds": n_seeds,
        "n_feasible_stage1": n_feasible,
        "n_successful_stage2": len(valid_results),
        "best_seed_idx": best["seed_idx"],
        "productivity": best["productivity"],
        "metrics": best.get("metrics", {}),
        "all_seed_results": optimization_results,
    }


def main():
    parser = argparse.ArgumentParser(description="Phase 2: Two-Stage LHS Screening")
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
    parser.add_argument("--timeout", type=int, default=120, help="Timeout for Stage 2 optimization")
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
    print("PHASE 2: TWO-STAGE SCREENING (Feasibility + Optimization)")
    print("=" * 70)
    print(f"\nNCs to optimize: {len(ncs)}")
    print(f"LHS seeds per NC: {args.n_seeds}")
    print(f"Total evaluations: Stage 1 (feasibility) = {len(ncs) * args.n_seeds}")
    print(f"                   Stage 2 (full opt) = variable (only feasible seeds)")
    print(f"\nExpected speedup: ~40-50% (only optimizing feasible seeds)")
    print("")

    # Generate LHS seeds (shared by all NCs)
    print(f"Generating {args.n_seeds} LHS seeds...")
    lhs_seeds = generate_lhs_seeds(args.n_seeds)

    # Optimize each NC
    all_results = []
    for nc in ncs:
        result = optimize_nc_two_stage(nc, artifact_dir, lhs_seeds, timeout=args.timeout, verbose=args.verbose)
        all_results.append(result)

    # Save summary
    summary = {
        "status": "ok",
        "stage": "phase2_two_stage_screening",
        "method": "Two-stage: feasibility check + full optimization",
        "n_lhs_seeds": args.n_seeds,
        "ncs_tested": len(all_results),
        "results": all_results,
        "statistics": {
            "total_seeds": len(ncs) * args.n_seeds,
            "total_feasible_stage1": sum(r.get("n_feasible_stage1", 0) for r in all_results),
            "total_successful_stage2": sum(r.get("n_successful_stage2", 0) for r in all_results),
            "speedup_vs_full_optimization": "~40-50% (only feasible seeds optimized)",
        },
    }

    output_file = Path(artifact_dir) / "phase2_summary.json"
    with open(output_file, "w") as f:
        json.dump(summary, f, indent=2, default=str)

    print("\n" + "=" * 70)
    print("✓ PHASE 2 TWO-STAGE SCREENING COMPLETE")
    print("=" * 70)
    print(f"\nResults: {output_file}")
    print(f"Feasible seeds (Stage 1): {summary['statistics']['total_feasible_stage1']} / {summary['statistics']['total_seeds']}")
    print(f"Successful optimizations (Stage 2): {summary['statistics']['total_successful_stage2']}")
    print(f"Expected speedup: {summary['statistics']['speedup_vs_full_optimization']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
