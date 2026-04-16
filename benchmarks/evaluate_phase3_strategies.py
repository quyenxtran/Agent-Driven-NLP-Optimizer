#!/usr/bin/env python3
"""
Phase 3 Comparative Evaluation Orchestrator

This is the canonical current Phase 3 entrypoint.

Runs the revised 3-strategy benchmark family:
  1. Wait for Phase 2 data
  2. Run Strategy A: Heuristic baseline
  3. Run Strategy B: Bayesian Optimization + GP
  4. Run Strategy C: Agent + LHS + Domain
  5. For each strategy's top 5 NCs: run 1 high-fidelity promotion optimization
  6. Promote the single best NC per strategy
  7. Run 3 multi-start high-fidelity validations only on each promoted winner
  8. Compute summary statistics aligned with the revised plan
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

from benchmarks.artifact_contract import (
    PHASE2_ARTIFACT_DIR,
    PHASE2_REFERENCE_CANONICAL,
    PHASE2_REFERENCE_LEGACY_COMPAT,
    PHASE2_REFERENCE_RAW_GLOB,
    PHASE3_FINALIST_DIR,
    PHASE3_PROMOTION_DIR,
    PHASE3_RESULTS_DIR,
    PHASE3_STUDY_SUMMARY,
    contract_metadata,
    phase3_selection_path,
)


def run_strategy_selection(strategy_script: str) -> bool:
    """Run a single NC selection strategy script."""
    script_path = REPO_ROOT / "benchmarks" / strategy_script

    print(f"\n📍 Running {strategy_script}...")

    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=600,
        )

        if result.returncode == 0:
            print(f"✓ {strategy_script} completed successfully")
            for line in result.stdout.split("\n"):
                if "Results saved to" in line:
                    print(f"  Output: {line.strip()}")
            return True

        print(f"✗ {strategy_script} failed with return code {result.returncode}")
        print(f"  stderr: {result.stderr[:500]}")
        return False

    except subprocess.TimeoutExpired:
        print(f"✗ {strategy_script} timed out")
        return False
    except Exception as exc:
        print(f"✗ {strategy_script} error: {exc}")
        return False


def load_strategy_results(strategy_name: str) -> Optional[Dict]:
    """Load saved strategy selection results."""
    result_file = phase3_selection_path(strategy_name.rsplit("_", 1)[1])

    if not result_file.exists():
        print(f"⚠ Strategy results not found: {result_file}")
        return None

    with open(result_file) as handle:
        return json.load(handle)


def run_high_fidelity_optimization(
    nc: List[int],
    strategy: str,
    run_label: str,
    *,
    artifact_dir: str,
) -> Dict:
    """Run a single high-fidelity optimization for one NC."""
    nc_str = f"[{nc[0]},{nc[1]},{nc[2]},{nc[3]}]"
    run_name = f"phase3_s{strategy}_nc_{''.join(map(str, nc))}_{run_label}"

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
        "--nc-library",
        nc_str,
        "--solver-name",
        "auto",
        "--linear-solver",
        "ma97",
        "--nfex",
        "10",
        "--nfet",
        "5",
        "--ncp",
        "2",
        "--purity-min",
        "0.30",
        "--recovery-ga-min",
        "0.75",
        "--recovery-ma-min",
        "0.75",
        "--max-pump-flow",
        "3.0",
    ]

    try:
        result = subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=900,
        )

        if result.returncode == 0:
            for line in result.stdout.split("\n"):
                if '"artifact"' in line:
                    try:
                        artifact_data = json.loads(line)
                        artifact_path = artifact_data.get("artifact")
                        if artifact_path and Path(artifact_path).exists():
                            with open(artifact_path) as handle:
                                artifact = json.load(handle)
                            return {
                                "status": "ok",
                                "nc": nc,
                                "strategy": strategy,
                                "run_label": run_label,
                                "J_validated": artifact.get("J_validated"),
                                "purity": artifact.get("metrics", {}).get(
                                    "purity_ex_meoh_free"
                                ),
                                "recovery_ga": artifact.get("metrics", {}).get(
                                    "recovery_ex_GA"
                                ),
                                "recovery_ma": artifact.get("metrics", {}).get(
                                    "recovery_ex_MA"
                                ),
                            }
                    except (json.JSONDecodeError, KeyError):
                        continue

        return {
            "status": "error",
            "nc": nc,
            "strategy": strategy,
            "run_label": run_label,
            "error": result.stderr[:200],
        }

    except subprocess.TimeoutExpired:
        return {
            "status": "timeout",
            "nc": nc,
            "strategy": strategy,
            "run_label": run_label,
        }
    except Exception as exc:
        return {
            "status": "exception",
            "nc": nc,
            "strategy": strategy,
            "run_label": run_label,
            "error": str(exc),
        }


def run_promotion_stage(strategy_results: Dict, strategy_name: str) -> List[Dict]:
    """Run one high-fidelity promotion optimization for each selected NC."""
    selected_ncs = strategy_results.get("selected_ncs", [])

    print(f"\n{'=' * 70}")
    print(f"PHASE 3 PROMOTION STAGE: Strategy {strategy_name.upper()}")
    print(f"{'=' * 70}")
    print(f"Running one promotion optimization for {len(selected_ncs)} selected NCs...")

    results = []
    for nc_idx, nc in enumerate(selected_ncs, 1):
        print(f"  [{nc_idx}/{len(selected_ncs)}] NC {nc}...", end=" ", flush=True)
        result = run_high_fidelity_optimization(
            nc,
            strategy_name,
            run_label="promote",
            artifact_dir=str(PHASE3_PROMOTION_DIR.relative_to(REPO_ROOT)),
        )
        results.append(result)

        if result["status"] == "ok":
            j_val = result.get("J_validated")
            print(f"✓ J={j_val:.4f}" if j_val is not None else "✓ ok")
        else:
            print(f"✗ {result['status']}")

    return results


def select_best_promoted_nc(promotion_results: List[Dict]) -> Optional[Dict]:
    """Return the best successful promotion-stage result."""
    successful = [r for r in promotion_results if r.get("status") == "ok" and r.get("J_validated") is not None]
    if not successful:
        return None
    return max(successful, key=lambda result: result["J_validated"])


def run_finalist_robustness(finalist_result: Dict, strategy_name: str) -> List[Dict]:
    """Run 3 multi-start high-fidelity validations on the promoted winner."""
    nc = finalist_result["nc"]

    print(f"\n{'=' * 70}")
    print(f"FINALIST ROBUSTNESS STAGE: Strategy {strategy_name.upper()}")
    print(f"{'=' * 70}")
    print(f"Running 3 multi-start validations for promoted winner NC {nc}...")

    results = []
    for run_num in range(1, 4):
        run_label = f"finalist_run{run_num}"
        print(f"  [run {run_num}/3] NC {nc}...", end=" ", flush=True)
        result = run_high_fidelity_optimization(
            nc,
            strategy_name,
            run_label=run_label,
            artifact_dir=str(PHASE3_FINALIST_DIR.relative_to(REPO_ROOT)),
        )
        results.append(result)

        if result["status"] == "ok":
            j_val = result.get("J_validated")
            print(f"✓ J={j_val:.4f}" if j_val is not None else "✓ ok")
        else:
            print(f"✗ {result['status']}")

    return results


def summarize_result_set(results: List[Dict]) -> Dict:
    """Summarize a set of optimization results."""
    successful = [r for r in results if r.get("status") == "ok" and r.get("J_validated") is not None]
    j_values = [r["J_validated"] for r in successful]

    return {
        "n_total": len(results),
        "n_successful": len(successful),
        "best_j": float(max(j_values)) if j_values else None,
        "mean_j": float(np.mean(j_values)) if j_values else None,
        "median_j": float(np.median(j_values)) if j_values else None,
        "std_j": float(np.std(j_values)) if j_values else None,
    }


def build_strategy_summary(promotion_results: List[Dict], finalist_results: List[Dict]) -> Dict:
    """Build one strategy summary aligned with the revised Phase 3 plan."""
    best_promoted = select_best_promoted_nc(promotion_results)

    return {
        "best_promoted_nc": best_promoted["nc"] if best_promoted else None,
        "best_promoted_j": best_promoted["J_validated"] if best_promoted else None,
        "promotion_stage": summarize_result_set(promotion_results),
        "finalist_robustness": summarize_result_set(finalist_results),
    }


def compute_statistics(
    promotion_results_by_strategy: Dict[str, List[Dict]],
    finalist_results_by_strategy: Dict[str, List[Dict]],
) -> Dict:
    """Compute revised-plan summary statistics by strategy."""
    summary = {}

    for strategy in ["a", "b", "c"]:
        promoted = promotion_results_by_strategy.get(strategy, [])
        finalists = finalist_results_by_strategy.get(strategy, [])
        promoted_ok = [r["J_validated"] for r in promoted if r.get("status") == "ok" and r.get("J_validated") is not None]
        finalists_ok = [r["J_validated"] for r in finalists if r.get("status") == "ok" and r.get("J_validated") is not None]

        summary[strategy] = {
            "best_promoted_j": float(max(promoted_ok)) if promoted_ok else None,
            "promotion_mean_j": float(np.mean(promoted_ok)) if promoted_ok else None,
            "promotion_median_j": float(np.median(promoted_ok)) if promoted_ok else None,
            "promotion_n": len(promoted_ok),
            "finalist_best_j": float(max(finalists_ok)) if finalists_ok else None,
            "finalist_mean_j": float(np.mean(finalists_ok)) if finalists_ok else None,
            "finalist_std_j": float(np.std(finalists_ok)) if finalists_ok else None,
            "finalist_n": len(finalists_ok),
        }

    return summary


def generate_summary_report(
    strategy_results: Dict[str, Dict],
    promotion_results: Dict[str, List[Dict]],
    finalist_results: Dict[str, List[Dict]],
    statistics: Dict,
) -> None:
    """Generate human-readable summary report and save JSON output."""
    print(f"\n{'=' * 70}")
    print("PHASE 3 COMPARATIVE STUDY: SUMMARY REPORT")
    print(f"{'=' * 70}")

    print("\n📋 NC SELECTIONS BY STRATEGY:")
    for strategy in ["a", "b", "c"]:
        results = strategy_results.get(strategy, {})
        selected = results.get("selected_ncs", [])
        print(f"\nStrategy {strategy.upper()}: {selected}")

    print("\n✅ REVISED-PLAN SUMMARY:")
    print(json.dumps(statistics, indent=2))

    strategy_summaries = {
        strategy: build_strategy_summary(
            promotion_results.get(strategy, []),
            finalist_results.get(strategy, []),
        )
        for strategy in ["a", "b", "c"]
    }

    output = {
        "phase": "3_comparative",
        "plan": "revised_publication_plan",
        "artifact_contract": contract_metadata(),
        "strategies": strategy_results,
        "promotion_results": promotion_results,
        "finalist_results": finalist_results,
        "strategy_summaries": strategy_summaries,
        "statistics": statistics,
    }

    output_file = PHASE3_STUDY_SUMMARY
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w") as handle:
        json.dump(output, handle, indent=2, default=str)

    print(f"\n✓ Summary saved to {output_file}")


def main() -> int:
    """Main orchestration workflow."""
    print(f"\n{'=' * 70}")
    print("PHASE 3 COMPARATIVE STUDY ORCHESTRATOR")
    print(f"{'=' * 70}")

    phase2_dir = PHASE2_ARTIFACT_DIR
    has_canonical = PHASE2_REFERENCE_CANONICAL.exists() or PHASE2_REFERENCE_LEGACY_COMPAT.exists()
    has_legacy = (phase2_dir / "phase2_summary.json").exists()
    has_reference = any(phase2_dir.glob(PHASE2_REFERENCE_RAW_GLOB))

    if not (has_canonical or has_legacy or has_reference):
        print(f"\n⏳ Waiting for Phase 2 data under: {phase2_dir}")
        print("   (Need canonical phase2_reference_canonical.json, legacy phase2_summary.json, or raw reference-eval seed artifacts)")
        return 1

    print(f"✓ Phase 2 data source found under: {phase2_dir}")

    output_dir = PHASE3_RESULTS_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'=' * 70}")
    print("STRATEGY SELECTION (Phase 3A)")
    print(f"{'=' * 70}")

    strategies = {
        "a": "phase3_strategy_a_baseline.py",
        "b": "phase3_strategy_b_bo_gp.py",
        "c": "phase3_strategy_c_agent_lhs.py",
    }

    strategy_results: Dict[str, Dict] = {}
    for strategy_key, strategy_script in strategies.items():
        success = run_strategy_selection(strategy_script)
        if success:
            results = load_strategy_results(f"strategy_{strategy_key}")
            if results:
                strategy_results[strategy_key] = results

    if len(strategy_results) < 3:
        print("\n❌ Not all strategies completed successfully")
        return 1

    promotion_results: Dict[str, List[Dict]] = {}
    finalist_results: Dict[str, List[Dict]] = {}

    print(f"\n{'=' * 70}")
    print("PROMOTION STAGE (Phase 3B)")
    print(f"{'=' * 70}")

    for strategy_key in ["a", "b", "c"]:
        promotion_results[strategy_key] = run_promotion_stage(
            strategy_results[strategy_key],
            strategy_key,
        )

    print(f"\n{'=' * 70}")
    print("FINALIST ROBUSTNESS STAGE (Phase 3C)")
    print(f"{'=' * 70}")

    for strategy_key in ["a", "b", "c"]:
        best_promoted = select_best_promoted_nc(promotion_results[strategy_key])
        finalist_results[strategy_key] = (
            run_finalist_robustness(best_promoted, strategy_key)
            if best_promoted
            else []
        )

    statistics = compute_statistics(promotion_results, finalist_results)
    generate_summary_report(
        strategy_results,
        promotion_results,
        finalist_results,
        statistics,
    )

    print(f"\n{'=' * 70}")
    print("✓ PHASE 3 COMPARATIVE STUDY COMPLETE")
    print(f"{'=' * 70}")
    print(f"\nResults directory: {output_dir}")
    print("Next: Analyze results and write manuscript")

    return 0


if __name__ == "__main__":
    sys.exit(main())
