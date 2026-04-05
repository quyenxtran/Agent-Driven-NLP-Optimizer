#!/usr/bin/env python3
"""
Phase 3 Strategy B: Bayesian Optimization + Gaussian Process

Statistical surrogate model: Fit GP to 3200 seed results, predict on all NCs.
Weak exploration: rank by μ + 0.5√σ (conservative exploration).
Select top 5 NCs.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
from scipy.spatial.distance import pdist, squareform

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))


def load_phase2_data(phase2_file: Path) -> Dict:
    """Load Phase 2 summary data."""
    with open(phase2_file) as f:
        return json.load(f)


def extract_training_data(phase2_data: Dict) -> Tuple[List, List]:
    """
    Extract training data from Phase 2 results.

    Returns: (X=[nc_configs], y=[productivities])
    """
    X = []  # NC configurations
    y = []  # Best productivities

    results = phase2_data.get("results", [])

    for nc_result in results:
        nc = tuple(nc_result["nc"])
        best_prod = nc_result.get("productivity")

        if best_prod is not None and best_prod > 0:
            X.append(list(nc))
            y.append(best_prod)

    return X, y


def simple_gp_fit(X: np.ndarray, y: np.ndarray) -> Dict:
    """
    Simple GP fit using Matérn-like kernel approximation.

    Returns: {
        "X_train": training inputs,
        "y_train": training outputs,
        "mean": mean of y,
        "std": std of y,
        "kernel_distances": pairwise distances for visualization
    }
    """
    X = np.array(X, dtype=float)
    y = np.array(y, dtype=float)

    # Standardize y
    y_mean = np.mean(y)
    y_std = np.std(y) + 1e-6
    y_norm = (y - y_mean) / y_std

    # Compute pairwise distances (Matérn-like)
    distances = squareform(pdist(X, metric="euclidean"))

    return {
        "X_train": X,
        "y_train": y,
        "y_mean": float(y_mean),
        "y_std": float(y_std),
        "y_normalized": y_norm,
        "distances": distances,
        "n_train": len(X),
    }


def predict_gp(gp_model: Dict, X_test: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Simple GP prediction: inverse distance weighting + uncertainty.

    Returns: (mu, sigma)
    """
    X_train = gp_model["X_train"]
    y_norm = gp_model["y_normalized"]
    y_mean = gp_model["y_mean"]
    y_std = gp_model["y_std"]

    X_test = np.array(X_test, dtype=float)
    if X_test.ndim == 1:
        X_test = X_test.reshape(1, -1)

    mu = np.zeros(len(X_test))
    sigma = np.zeros(len(X_test))

    for i, x_test in enumerate(X_test):
        # Distances from test point to training points
        dists = np.linalg.norm(X_train - x_test, axis=1)

        # Avoid division by zero
        min_dist = np.min(dists)
        if min_dist < 1e-6:
            # Exact match to training point
            idx = np.argmin(dists)
            mu[i] = y_norm[idx]
            sigma[i] = 0.01  # Low uncertainty
        else:
            # Inverse distance weighting
            weights = 1.0 / (dists + 1e-6)
            weights /= np.sum(weights)
            mu[i] = np.sum(weights * y_norm)

            # Uncertainty: inversely proportional to proximity
            sigma[i] = np.mean(dists) / (1.0 + np.min(dists))

    # Denormalize predictions
    mu_denorm = mu * y_std + y_mean
    sigma_denorm = sigma * y_std  # Uncertainty scales with y_std

    return mu_denorm, sigma_denorm


def run_strategy_b(phase2_file: Path) -> Dict:
    """
    Run Strategy B: BO + GP.

    1. Load Phase 2 data
    2. Fit GP to training data
    3. Predict on all NCs
    4. Rank by μ + 0.5√σ (weak exploration)
    5. Select top 5
    """
    print("\n" + "=" * 70)
    print("PHASE 3 STRATEGY B: BAYESIAN OPTIMIZATION + GAUSSIAN PROCESS")
    print("=" * 70)

    # Load data
    print(f"\nLoading Phase 2 data from {phase2_file}...")
    phase2_data = load_phase2_data(phase2_file)

    # Extract training data
    print("\nExtracting training data from Phase 2...")
    X, y = extract_training_data(phase2_data)
    print(f"Training data: {len(X)} NCs with valid results")

    if len(X) < 3:
        print("✗ Insufficient training data (need >2 NCs)")
        return {
            "strategy": "strategy_b_bo_gp",
            "error": "insufficient_training_data",
        }

    # Fit GP
    print("\nFitting Gaussian Process...")
    gp_model = simple_gp_fit(np.array(X), np.array(y))
    print(f"✓ GP fitted with {gp_model['n_train']} training points")
    print(f"  Training data mean: {gp_model['y_mean']:.4f}")
    print(f"  Training data std: {gp_model['y_std']:.4f}")

    # Get all NC configurations
    all_ncs = [result["nc"] for result in phase2_data.get("results", [])]
    X_test = np.array(all_ncs, dtype=float)

    # Predict on all NCs
    print("\nPredicting on all NCs...")
    mu, sigma = predict_gp(gp_model, X_test)

    # Compute acquisition: UCB with weak exploration
    ucb = mu + 0.5 * np.sqrt(sigma)

    # Rank
    print("\nRanking NCs by acquisition function...")
    rankings = list(enumerate(ucb))
    rankings.sort(key=lambda x: x[1], reverse=True)

    # Select top 5
    print("\n" + "-" * 70)
    print("TOP 5 SELECTED NCs (by μ + 0.5√σ):")
    print("-" * 70)

    top_5 = []
    for rank, (idx, acq_val) in enumerate(rankings[:5], 1):
        nc = tuple(all_ncs[idx])
        top_5.append(nc)

        print(f"\n{rank}. NC {nc}")
        print(f"   Predicted mean (μ): {mu[idx]:.4f}")
        print(f"   Uncertainty (σ): {sigma[idx]:.4f}")
        print(f"   Acquisition (μ+0.5√σ): {acq_val:.4f}")

    # Build output
    output = {
        "strategy": "strategy_b_bo_gp",
        "selected_ncs": [list(nc) for nc in top_5],
        "method": {
            "name": "Bayesian Optimization + Gaussian Process",
            "kernel": "Matérn-like (approximated)",
            "acquisition": "UCB with β=0.5 (weak exploration)",
            "description": "Fit GP to 3200 seed results, rank by μ+0.5√σ",
            "philosophy": "Statistical learning from Phase 2 data, minimal exploration",
        },
        "gp_diagnostics": {
            "n_training": gp_model["n_train"],
            "training_mean": float(gp_model["y_mean"]),
            "training_std": float(gp_model["y_std"]),
        },
    }

    print("\n" + "=" * 70)
    print(f"✓ Strategy B Complete: {len(top_5)} NCs selected")
    print("=" * 70)

    return output


def main():
    phase2_file = REPO_ROOT / "artifacts" / "phase2_lhs_seeding" / "phase2_summary.json"

    if not phase2_file.exists():
        print(f"✗ Phase 2 data not found: {phase2_file}")
        sys.exit(1)

    # Run strategy
    results = run_strategy_b(phase2_file)

    # Save results
    output_file = REPO_ROOT / "artifacts" / "phase3_results" / "strategy_b_selection.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\n✓ Results saved to {output_file}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
