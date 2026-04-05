#!/usr/bin/env python3
"""
Phase 2: Foundation Data Generation via LHS Screening (Direct Optimization)

REWRITTEN to call optimization directly instead of subprocess.run() to eliminate overhead.
Subprocess + run_stage overhead was causing 600s+ timeouts per seed.

This version:
- Imports sembasmb directly
- Builds/solves model in-process
- ~1-2s per low-fidelity optimization (vs 600s+ timeout via subprocess)
"""

import argparse
import sys
import json
import tempfile
import traceback
from pathlib import Path
from typing import List, Tuple, Dict

import numpy as np
from scipy.stats import qmc

# Setup path
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "benchmarks"))

# Import sembasmb directly
from sembasmb import (
    SMBConfig, FlowRates, build_inputs, build_model,
    apply_discretization, add_optimization, solve_model,
    compute_outlet_averages, compute_purity_recovery
)


def generate_lhs_seeds(
    n_seeds: int = 100,
    var_names: List[str] = None,
    bounds: List[Tuple[float, float]] = None,
) -> List[Dict[str, float]]:
    """
    N-dimensional LHS sampling.
    """
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

    assert len(var_names) == len(bounds)
    n_dims = len(var_names)

    sampler = qmc.LatinHypercube(d=n_dims, seed=42)
    samples = sampler.random(n=n_seeds)

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


def optimize_seed_direct(
    nc: List[int],
    seed: Dict[str, float],
    seed_idx: int,
    artifact_dir: str,
    verbose: bool = True,
) -> Dict:
    """
    Direct optimization (no subprocess).

    Builds and solves Pyomo model with given seed parameters.
    Returns artifact dict with metrics.
    """
    nc_str = format_nc(nc)
    run_name = f"phase2_nc_{nc_str}_seed_{seed_idx}"

    if verbose:
        print(f"    Optimizing seed {seed_idx}...", end=" ", flush=True)

    try:
        # Build SMBConfig (use default isotherm, adjust NC)
        config = SMBConfig(
            nc=tuple(nc),
            isoth="MLL",
        )

        # Convert flows to FlowRates
        flows = FlowRates(
            F1=seed["f1"],
            Ffeed=seed["ffeed"],
            Fdes=seed["fdes"],
            Fex=seed["fex"],
            tstep=seed["tstep"],
        )

        # Build inputs
        inputs = build_inputs(config, flows)

        # Build model
        model = build_model(inputs)

        # Apply LOW-fidelity discretization
        nfex, nfet, ncp = 4, 2, 1
        apply_discretization(model, nfex=nfex, nfet=nfet, ncp=ncp)

        # Add optimization
        add_optimization(
            model,
            inputs=inputs,
            purity_min=0.15,
            recovery_min_ga=0.15,
            recovery_min_ma=0.15,
            fex_bounds=(0.5, 2.5),
            f1_bounds=(0.5, 5.0),
        )

        # Solve with IPOPT options for low-fidelity
        options = {
            "max_iter": 200,
            "tol": 1e-6,
            "acceptable_tol": 1e-4,
            "max_cpu_time": 60,
            "linear_solver": "ma97",
        }

        result = solve_model(
            model,
            solver_name="ipopt",
            options=options,
            tee=False,
        )

        # Check if solve succeeded
        solver = getattr(result, "solver", None)
        status = str(getattr(solver, "status", "unknown")).lower() if solver else "unknown"
        termination = str(getattr(solver, "termination_condition", "unknown")).lower() if solver else "unknown"

        if status != "ok" or termination not in {"optimal", "locallyoptimal", "feasible"}:
            if verbose:
                print(f"✗ solver failed ({status}, {termination})")
            return {"status": "solver_failed", "seed_idx": seed_idx}

        # Extract metrics
        ce_acid_avg, cr_acid_avg = compute_outlet_averages(model)
        metrics = compute_purity_recovery(model, inputs, config)

        J_validated = metrics.get("productivity_ex_ga_ma")
        purity = metrics.get("purity_ex_meoh_free")
        recovery_ga = metrics.get("recovery_ex_GA")
        recovery_ma = metrics.get("recovery_ex_MA")

        # Build artifact
        artifact = {
            "status": "ok",
            "run_name": run_name,
            "stage": "optimize-layouts",
            "nc": nc,
            "seed_idx": seed_idx,
            "seed": seed,
            "J_validated": J_validated,
            "metrics": metrics,
            "solver_result": {
                "status": status,
                "termination": termination,
            },
            "feasible": (
                metrics.get("purity_ex_meoh_free", 0) >= 0.15 and
                metrics.get("recovery_ex_GA", 0) >= 0.15 and
                metrics.get("recovery_ex_MA", 0) >= 0.15
            ),
        }

        if verbose:
            print(f"✓ J={J_validated:.2f}, pu={purity:.3f}")

        return artifact

    except Exception as e:
        if verbose:
            print(f"✗ exception: {type(e).__name__}")
            # Print traceback to see actual error
            traceback.print_exc()
        return {
            "status": "exception",
            "seed_idx": seed_idx,
            "error": str(e),
            "traceback": traceback.format_exc(),
        }


def optimize_nc_with_lhs_seeds(
    nc: List[int],
    artifact_dir: str,
    seeds: List[Dict[str, float]],
    verbose: bool = True,
) -> Dict:
    """
    Optimize NC with all LHS seeds.
    """
    nc_str = format_nc(nc)
    n_seeds = len(seeds)

    if verbose:
        print(f"\n{'='*70}")
        print(f"NC {nc_str}: {n_seeds} LHS seeds for 5D space coverage")
        print(f"{'='*70}")

    if verbose:
        print(f"\nOptimizing all {n_seeds} seeds at LOW fidelity (nfex=4, nfet=2)...")

    optimization_results = []
    for seed_idx, seed in enumerate(seeds):
        result = optimize_seed_direct(
            nc, seed, seed_idx, artifact_dir, verbose=verbose
        )
        optimization_results.append(result)

    # Find valid results
    valid_results = [
        r for r in optimization_results
        if r.get("status") == "ok" and r.get("J_validated") is not None
    ]

    if valid_results:
        best = max(valid_results, key=lambda r: r["J_validated"])

        if verbose:
            print(f"\n{'─'*70}")
            print(f"Results for NC {nc_str}:")
            print(f"  Initial seeds: {n_seeds}")
            print(f"  Successfully optimized: {len(valid_results)}")
            print(f"  Success rate: {len(valid_results)/n_seeds*100:.1f}%")
            print(f"\n  Best seed: {best['seed_idx']}")
            print(f"    Productivity: {best['J_validated']:.4f}")
            print(f"    Purity: {best['metrics'].get('purity_ex_meoh_free', 0):.4f}")
            print(f"    Recovery GA: {best['metrics'].get('recovery_ex_GA', 0):.4f}")

        return {
            "nc": nc,
            "n_seeds": n_seeds,
            "best_seed_idx": best["seed_idx"],
            "productivity": best["J_validated"],
            "purity": best["metrics"].get("purity_ex_meoh_free"),
            "recovery_ga": best["metrics"].get("recovery_ex_GA"),
            "n_feasible": len(valid_results),
            "all_seed_results": valid_results,
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
        description="Phase 2: Direct LHS Seeded Optimization (No Subprocess)"
    )
    parser.add_argument("--ncs", nargs="+", default=[
        "[1,1,2,4]", "[1,1,3,3]", "[1,1,4,2]", "[1,2,1,4]", "[1,2,4,1]",
        "[1,3,1,3]", "[1,3,2,2]", "[2,1,2,3]", "[2,2,1,3]", "[2,2,2,2]",
        "[2,2,3,1]", "[2,3,1,2]", "[2,3,2,1]", "[2,4,1,1]", "[3,1,1,3]",
        "[3,1,2,2]", "[3,1,3,1]", "[3,2,1,2]", "[3,2,2,1]", "[3,3,1,1]",
        "[4,1,1,2]", "[4,1,2,1]", "[4,2,1,1]", "[1,4,1,2]", "[1,4,2,1]",
        "[1,2,2,3]", "[2,1,1,4]", "[1,1,1,5]", "[2,2,4,0]", "[1,2,3,2]",
        "[3,2,2,1]", "[2,3,2,1]",
    ])
    parser.add_argument("--n-seeds", type=int, default=100)
    parser.add_argument("--artifact-dir", default="artifacts/phase2_lhs_seeding")
    # Optional (ignored, for SLURM script compatibility)
    parser.add_argument("--solver-name", default="ipopt")
    parser.add_argument("--linear-solver", default="ma97")
    parser.add_argument("--verbose", action="store_true", default=True)

    args = parser.parse_args()

    # Parse NCs
    ncs = []
    for nc_str in args.ncs:
        nc_str_clean = nc_str.strip("[]")
        nc_vals = tuple(int(x.strip()) for x in nc_str_clean.split(","))
        if len(nc_vals) == 4 and sum(nc_vals) == 8:
            ncs.append(list(nc_vals))

    artifact_dir = Path(args.artifact_dir)
    artifact_dir.mkdir(parents=True, exist_ok=True)

    # Generate shared LHS seeds
    print("\nGenerating 100 LHS seeds in 5D space (used for all NCs)...")
    seeds = generate_lhs_seeds(n_seeds=args.n_seeds)
    print(f"✓ Generated {len(seeds)} seeds")

    # Optimize each NC
    all_results = []
    for nc in ncs[:args.n_seeds]:  # Limit for testing
        result = optimize_nc_with_lhs_seeds(nc, str(artifact_dir), seeds, verbose=True)
        all_results.append(result)

    # Summary
    print(f"\n{'='*70}")
    print("PHASE 2 SUMMARY")
    print(f"{'='*70}")
    successful_ncs = [r for r in all_results if r.get("productivity") is not None]
    print(f"NCs tested: {len(all_results)}")
    print(f"Successful: {len(successful_ncs)}")
    print(f"Total feasible seeds: {sum(r.get('n_feasible', 0) for r in all_results)}")

    # Write summary
    summary = {
        "status": "ok",
        "stage": "phase2_lhs_seeding",
        "n_lhs_seeds": args.n_seeds,
        "ncs_tested": len(all_results),
        "successful_ncs": len(successful_ncs),
        "results": all_results,
    }

    summary_path = artifact_dir / "phase2_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))
    print(f"\n✓ Summary written to {summary_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
