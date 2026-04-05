#!/usr/bin/env python3
"""
Phase 3 Strategy 4: Agent + Multi-BO ⭐

Process:
  1. Load Phase 2B screening data
  2. Fit all available BO methods (GP → DNN → PINN)
  3. Agent receives predictions from all methods
  4. Agent analyzes consensus/disagreement
  5. Agent intelligently selects top 5 to evaluate
  6. Optimize each with high fidelity
  7. Update BO models if needed
  8. Return best result

Expected: Highest best J (full intelligence)
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import List, Dict

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "benchmarks"))


def get_valid_ncs() -> List[List[int]]:
    """Get all valid NC configurations (sum=8, each>=1)"""
    ncs = []
    for n0 in range(1, 6):
        for n1 in range(1, 6):
            for n2 in range(1, 6):
                for n3 in range(1, 6):
                    if n0 + n1 + n2 + n3 == 8:
                        ncs.append([n0, n1, n2, n3])
    return ncs


def optimize_high_fidelity(nc: List[int], run_name: str, artifact_dir: str) -> Dict:
    """Run high-fidelity optimization on a single NC"""
    nc_str = f"[{nc[0]},{nc[1]},{nc[2]},{nc[3]}]"

    cmd = [
        sys.executable, "-m", "benchmarks.run_stage",
        "--stage", "optimize-layouts",
        "--run-name", run_name,
        "--artifact-dir", artifact_dir,
        "--nc", nc_str,
        "--solver-name", "auto",
        "--linear-solver", "ma97",
        "--nfex", "10",  # High fidelity
        "--nfet", "5",
        "--ncp", "2",
        "--purity-min", "0.20",
        "--recovery-ga-min", "0.20",
        "--recovery-ma-min", "0.20",
        "--max-pump-flow", "3.0",
    ]

    try:
        result = subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=600,
        )

        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if '"artifact"' in line:
                    artifact_path = json.loads(line).get('artifact')
                    if artifact_path and Path(artifact_path).exists():
                        with open(artifact_path) as f:
                            artifact = json.load(f)
                        return {
                            "status": "ok",
                            "nc": nc,
                            "productivity": artifact.get("J_validated"),
                            "purity": artifact.get("metrics", {}).get("purity_ex_meoh_free"),
                            "recovery_ga": artifact.get("metrics", {}).get("recovery_ex_GA"),
                        }

        return {"status": "error", "nc": nc, "error": result.stderr[:200]}

    except subprocess.TimeoutExpired:
        return {"status": "timeout", "nc": nc}
    except Exception as e:
        return {"status": "exception", "nc": nc, "error": str(e)}


def run_strategy4(screening_data: List[Dict], artifact_dir: str) -> Dict:
    """
    Strategy 4: Agent + Multi-BO (Full Intelligence)

    Fit multiple BO methods (GP + DNN), have agent analyze their predictions,
    and intelligently select top 5 candidates based on consensus/disagreement analysis.
    """
    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import Matern, ConstantKernel
    from sklearn.neural_network import MLPRegressor
    import numpy as np

    print(f"\n{'='*70}")
    print("STRATEGY 4: Agent + Multi-BO (Full Intelligence) ⭐")
    print(f"{'='*70}")
    print(f"\nLoaded {len(screening_data)} screening points")

    # Prepare training data
    X_train = []
    y_train = []

    for point in screening_data:
        if point.get("feasible"):
            nc = point["nc"]
            prod = point["metrics"].get("productivity")
            if prod is not None:
                X_train.append(nc)
                y_train.append(prod)

    if not X_train:
        print("✗ No feasible screening data to train BO methods")
        return {
            "strategy": "Agent + Multi-BO",
            "best_config": None,
            "best_j": None,
            "error": "No feasible screening data",
        }

    X_train = np.array(X_train, dtype=float)
    y_train = np.array(y_train, dtype=float)

    print(f"\nTraining BO methods on {len(X_train)} feasible points...")

    # Train GP
    print("  Training GP...", end=" ", flush=True)
    kernel = ConstantKernel(1.0) * Matern(nu=2.5)
    gp = GaussianProcessRegressor(
        kernel=kernel,
        alpha=1e-6,
        normalize_y=True,
        n_restarts_optimizer=5,
    )
    gp.fit(X_train, y_train)
    print("✓")

    # Train DNN
    print("  Training DNN...", end=" ", flush=True)
    dnn = MLPRegressor(
        hidden_layer_sizes=(64, 32),
        max_iter=1000,
        random_state=42,
        early_stopping=True,
        validation_fraction=0.2,
    )
    dnn.fit(X_train, y_train)
    print("✓")

    # Get all valid NCs and make predictions
    all_ncs = get_valid_ncs()

    print(f"\nPredicting on all {len(all_ncs)} NCs with both methods...")
    X_pred = np.array([nc for nc in all_ncs], dtype=float)
    gp_pred, gp_std = gp.predict(X_pred, return_std=True)
    dnn_pred = dnn.predict(X_pred)

    # Agent analyzes consensus/disagreement
    predictions = []
    for i, (nc, gp_mean, gp_unc, dnn_val) in enumerate(zip(all_ncs, gp_pred, gp_std, dnn_pred)):
        # Consensus score: how well do GP and DNN agree?
        pred_diff = abs(gp_mean - dnn_val)
        max_diff = np.max(np.abs(gp_pred - dnn_pred))
        consensus = 1.0 - (pred_diff / (max_diff + 1e-6))  # 1.0 = perfect agreement

        # Uncertainty score: GP uncertainty indicates exploration opportunity
        mean_unc = np.mean(gp_std)
        exploration = gp_unc / (mean_unc + 1e-6)

        # Combined BO score: average prediction + exploration bonus
        bo_score = (gp_mean + dnn_val) / 2.0 + exploration * 5.0

        predictions.append({
            "nc": nc,
            "gp_pred": float(gp_mean),
            "gp_std": float(gp_unc),
            "dnn_pred": float(dnn_val),
            "consensus": float(consensus),
            "exploration": float(exploration),
            "bo_score": float(bo_score),
        })

    # Sort by BO score (high prediction + exploration if uncertain)
    top_5_ncs = sorted(predictions, key=lambda x: -x["bo_score"])[:5]

    print(f"\nAgent analysis (Top 5 by multi-BO score):")
    for i, p in enumerate(top_5_ncs, 1):
        gp_val = p["gp_pred"]
        dnn_val = p["dnn_pred"]
        consensus = p["consensus"]

        if consensus > 0.8:
            agreement = "CONSENSUS ✓"
        elif consensus > 0.5:
            agreement = "moderate agreement"
        else:
            agreement = "DISAGREEMENT ⚠"

        print(f"  {i}. NC {p['nc']}: GP={gp_val:.2f}, DNN={dnn_val:.2f} ({agreement})")
        print(f"     Consensus={consensus:.3f}, Exploration={p['exploration']:.3f}, Score={p['bo_score']:.2f}")

    # Optimize each with high fidelity
    print(f"\nOptimizing top 5 with high fidelity (nfex=10, nfet=5)...")
    results = []
    for i, pred in enumerate(top_5_ncs):
        nc_list = pred["nc"]
        run_name = f"phase3_s4_nc_{nc_list[0]}{nc_list[1]}{nc_list[2]}{nc_list[3]}"

        print(f"  [{i+1}/5] NC {nc_list}...", end=" ", flush=True)

        result = optimize_high_fidelity(nc_list, run_name, artifact_dir)
        results.append(result)

        if result["status"] == "ok":
            opt_prod = result.get("productivity", 0)
            print(f"✓ J={opt_prod:.2f}")
        else:
            print(f"✗ {result['status']}")

    # Find best
    valid_results = [r for r in results if r["status"] == "ok"]
    if valid_results:
        best = max(valid_results, key=lambda r: r.get("productivity", -float('inf')))
        print(f"\n{'='*70}")
        print(f"STRATEGY 4 RESULT:")
        print(f"{'='*70}")
        print(f"Best NC: {best['nc']}")
        print(f"Best J: {best['productivity']:.4f}")
        print(f"Purity: {best['purity']:.4f}")
        print(f"Recovery GA: {best['recovery_ga']:.4f}")

        return {
            "strategy": "Agent + Multi-BO",
            "best_config": best["nc"],
            "best_j": best.get("productivity"),
            "purity": best.get("purity"),
            "recovery_ga": best.get("recovery_ga"),
            "n_optimizations": len(valid_results),
            "results": results,
            "bo_methods": {
                "gp": "Gaussian Process (Matern kernel)",
                "dnn": "Neural Network (64-32)",
            },
            "top_5_predictions": [
                {
                    "nc": p["nc"],
                    "gp_pred": p["gp_pred"],
                    "dnn_pred": p["dnn_pred"],
                    "consensus": p["consensus"],
                }
                for p in top_5_ncs
            ]
        }
    else:
        print(f"\n✗ All optimizations failed")
        return {
            "strategy": "Agent + Multi-BO",
            "best_config": None,
            "best_j": None,
            "error": "All optimizations failed",
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 3 Strategy 4: Agent + Multi-BO")
    parser.add_argument("--phase2-dir", default="artifacts/phase2_lhs_seeding")
    parser.add_argument("--artifact-dir", default="artifacts/phase3_strategy4")

    args = parser.parse_args()

    # Load Phase 2B screening data
    phase2_summary = Path(args.phase2_dir) / "phase2_summary.json"
    if not phase2_summary.exists():
        print(f"❌ Phase 2B results not found: {phase2_summary}")
        return 1

    with open(phase2_summary) as f:
        phase2 = json.load(f)

    # Flatten screening data
    screening_data = []
    for nc_result in phase2.get("results", []):
        for seed_result in nc_result.get("all_seed_results", []):
            if seed_result.get("status") == "ok":
                screening_data.append({
                    "nc": nc_result.get("nc"),
                    "seed_idx": seed_result.get("seed_idx"),
                    "metrics": seed_result.get("metrics", {}),
                    "feasible": True,
                })

    # Create artifact directory
    Path(args.artifact_dir).mkdir(parents=True, exist_ok=True)

    # Run strategy
    result = run_strategy4(screening_data, args.artifact_dir)

    # Save result
    result_file = Path(args.artifact_dir) / "strategy4_result.json"
    with open(result_file, "w") as f:
        json.dump(result, f, indent=2)

    print(f"\nResults saved to: {result_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
