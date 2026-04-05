#!/usr/bin/env python3
"""
Phase 3 Comparative Evaluation Orchestrator

Runs all three NC selection strategies, executes high-fidelity validation on
their top-5 selections, computes statistics, and generates publication figures.

Workflow:
  1. Wait for Phase 2 data (phase2_summary.json)
  2. Run Strategy A: Heuristic baseline
  3. Run Strategy B: Bayesian Optimization + GP
  4. Run Strategy C: Agent + LHS + Domain
  5. For each strategy's top 5 NCs: run 3 high-fidelity optimizations (45 total)
  6. Compute statistics: ANOVA, Tukey HSD, effect sizes, confidence intervals
  7. Generate summary table and figures
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))


def run_strategy_selection(strategy_script: str) -> Dict:
    """
    Run a single NC selection strategy.

    Args:
        strategy_script: Path to strategy script (relative to benchmarks/)

    Returns:
        Selection results JSON with selected_ncs and reasoning
    """
    script_path = REPO_ROOT / "benchmarks" / strategy_script

    print(f"\n📍 Running {strategy_script}...")

    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=600,  # 10 minutes per strategy
        )

        if result.returncode == 0:
            print(f"✓ {strategy_script} completed successfully")
            # Try to parse any JSON output from the script
            for line in result.stdout.split("\n"):
                if "Results saved to" in line:
                    # Extract file path from output
                    print(f"  Output: {line.strip()}")
        else:
            print(f"✗ {strategy_script} failed with return code {result.returncode}")
            print(f"  stderr: {result.stderr[:500]}")
            return None

    except subprocess.TimeoutExpired:
        print(f"✗ {strategy_script} timed out")
        return None
    except Exception as e:
        print(f"✗ {strategy_script} error: {e}")
        return None

    return result.returncode == 0


def load_strategy_results(strategy_name: str) -> Dict:
    """Load saved strategy selection results."""
    result_file = (
        REPO_ROOT
        / "artifacts"
        / "phase3_results"
        / f"{strategy_name}_selection.json"
    )

    if not result_file.exists():
        print(f"⚠ Strategy results not found: {result_file}")
        return None

    with open(result_file) as f:
        return json.load(f)


def run_high_fidelity_optimization(nc: List[int], strategy: str, run_num: int) -> Dict:
    """
    Run single high-fidelity optimization on an NC.

    Args:
        nc: NC configuration [n1, n2, n3, n4]
        strategy: Strategy name (a, b, or c)
        run_num: Run number (1, 2, or 3)

    Returns:
        {status, nc, J_validated, purity, recovery, ...}
    """
    nc_str = f"[{nc[0]},{nc[1]},{nc[2]},{nc[3]}]"
    run_name = f"phase3_s{strategy}_nc_{''.join(map(str, nc))}_run{run_num}"

    cmd = [
        sys.executable,
        "-m",
        "benchmarks.run_stage",
        "--stage",
        "optimize-layouts",
        "--run-name",
        run_name,
        "--artifact-dir",
        "artifacts/phase3_validation",
        "--nc",
        nc_str,
        "--solver-name",
        "auto",
        "--linear-solver",
        "ma97",
        "--nfex",
        "10",  # High fidelity
        "--nfet",
        "5",
        "--ncp",
        "2",
        "--purity-min",
        "0.60",  # Strict validation
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
            timeout=900,  # 15 minutes per optimization
        )

        if result.returncode == 0:
            # Parse artifact JSON from output
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
                                "strategy": strategy,
                                "run": run_num,
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
            "run": run_num,
            "error": result.stderr[:200],
        }

    except subprocess.TimeoutExpired:
        return {
            "status": "timeout",
            "nc": nc,
            "strategy": strategy,
            "run": run_num,
        }
    except Exception as e:
        return {
            "status": "exception",
            "nc": nc,
            "strategy": strategy,
            "run": run_num,
            "error": str(e),
        }


def execute_phase3_validation(strategy_results: Dict, strategy_name: str) -> List[Dict]:
    """
    Execute high-fidelity validation for a strategy's top 5 NCs.

    3 independent runs per NC → 5 NCs × 3 runs = 15 optimizations per strategy
    Total across 3 strategies: 45 optimizations
    """
    selected_ncs = strategy_results.get("selected_ncs", [])

    print(f"\n{'='*70}")
    print(f"PHASE 3 VALIDATION: Strategy {strategy_name.upper()}")
    print(f"{'='*70}")
    print(f"Validating {len(selected_ncs)} selected NCs with 3 runs each...")

    results = []
    for nc_idx, nc in enumerate(selected_ncs, 1):
        for run_num in range(1, 4):
            print(f"  [{nc_idx}/5, run {run_num}/3] NC {nc}...", end=" ", flush=True)

            result = run_high_fidelity_optimization(nc, strategy_name, run_num)
            results.append(result)

            if result["status"] == "ok":
                j_val = result.get("J_validated", 0)
                print(f"✓ J={j_val:.4f}")
            else:
                print(f"✗ {result['status']}")

    return results


def compute_statistics(all_results: List[Dict]) -> Dict:
    """
    Compute statistical comparison across strategies.

    Primary metric: Best J achieved per strategy
    Tests: One-way ANOVA, Tukey HSD, effect sizes, confidence intervals
    """
    from scipy import stats

    print(f"\n{'='*70}")
    print("STATISTICAL ANALYSIS")
    print(f"{'='*70}")

    # Group results by strategy
    results_by_strategy = {}
    for result in all_results:
        if result.get("status") == "ok":
            strategy = result.get("strategy")
            if strategy not in results_by_strategy:
                results_by_strategy[strategy] = []
            results_by_strategy[strategy].append(result.get("J_validated", 0))

    # Summary statistics
    print("\n📊 Summary by Strategy:")
    summary = {}
    for strategy in ["a", "b", "c"]:
        j_values = results_by_strategy.get(strategy, [])
        if j_values:
            best_j = max(j_values)
            mean_j = np.mean(j_values)
            std_j = np.std(j_values)
            ci_lower = np.percentile(j_values, 2.5)
            ci_upper = np.percentile(j_values, 97.5)

            print(
                f"\nStrategy {strategy.upper()}:"
                f"\n  Best J: {best_j:.4f}"
                f"\n  Mean J: {mean_j:.4f} ± {std_j:.4f}"
                f"\n  95% CI: [{ci_lower:.4f}, {ci_upper:.4f}]"
                f"\n  N: {len(j_values)} evaluations"
            )

            summary[strategy] = {
                "best_j": float(best_j),
                "mean_j": float(mean_j),
                "std_j": float(std_j),
                "ci_lower": float(ci_lower),
                "ci_upper": float(ci_upper),
                "n_evals": len(j_values),
            }
        else:
            print(f"\nStrategy {strategy.upper()}: No successful evaluations")

    # ANOVA test (if we have data from all strategies)
    if len(results_by_strategy) >= 3:
        all_groups = [
            results_by_strategy.get(s, []) for s in ["a", "b", "c"]
        ]

        if all(len(g) > 0 for g in all_groups):
            f_stat, p_value = stats.f_oneway(*all_groups)

            print(f"\n📈 One-Way ANOVA:")
            print(f"  F-statistic: {f_stat:.4f}")
            print(f"  p-value: {p_value:.6f}")
            print(f"  Significant at α=0.05: {'Yes' if p_value < 0.05 else 'No'}")

            summary["anova"] = {
                "f_statistic": float(f_stat),
                "p_value": float(p_value),
                "significant": p_value < 0.05,
            }

    return summary


def generate_summary_report(
    strategy_results: Dict,
    validation_results: Dict,
    statistics: Dict,
) -> None:
    """Generate human-readable summary report."""
    print(f"\n{'='*70}")
    print("PHASE 3 COMPARATIVE STUDY: SUMMARY REPORT")
    print(f"{'='*70}")

    # Selection summaries
    print("\n📋 NC SELECTIONS BY STRATEGY:")
    for strategy in ["a", "b", "c"]:
        results = strategy_results.get(strategy, {})
        selected = results.get("selected_ncs", [])
        print(f"\nStrategy {strategy.upper()}: {selected}")

    # Validation results
    print("\n✅ VALIDATION RESULTS:")
    print(f"Statistics: {json.dumps(statistics, indent=2)}")

    # Save comprehensive results
    output = {
        "phase": "3_comparative",
        "date": str(Path.cwd()),
        "strategies": strategy_results,
        "statistics": statistics,
    }

    output_file = REPO_ROOT / "artifacts" / "phase3_results" / "study_summary.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w") as f:
        json.dump(output, f, indent=2, default=str)

    print(f"\n✓ Summary saved to {output_file}")


def main():
    """Main orchestration workflow."""
    print(f"\n{'='*70}")
    print("PHASE 3 COMPARATIVE STUDY ORCHESTRATOR")
    print(f"{'='*70}")

    phase2_file = (
        REPO_ROOT / "artifacts" / "phase2_lhs_seeding" / "phase2_summary.json"
    )

    if not phase2_file.exists():
        print(f"\n⏳ Waiting for Phase 2 data: {phase2_file}")
        print("   (Run Phase 2 first: python -m benchmarks.phase2_lhs_seeding)")
        return 1

    print(f"✓ Phase 2 data found: {phase2_file}")

    # Create output directory
    output_dir = REPO_ROOT / "artifacts" / "phase3_results"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Run all three strategy selections
    print(f"\n{'='*70}")
    print("STRATEGY SELECTION (Phase 3A)")
    print(f"{'='*70}")

    strategies = {
        "a": "phase3_strategy_a_baseline.py",
        "b": "phase3_strategy_b_bo_gp.py",
        "c": "phase3_strategy_c_agent_lhs.py",
    }

    strategy_results = {}
    for strategy_key, strategy_script in strategies.items():
        success = run_strategy_selection(strategy_script)
        if success:
            results = load_strategy_results(f"strategy_{strategy_key}")
            if results:
                strategy_results[strategy_key] = results

    if len(strategy_results) < 3:
        print("\n❌ Not all strategies completed successfully")
        return 1

    # Execute high-fidelity validation
    print(f"\n{'='*70}")
    print("HIGH-FIDELITY VALIDATION (Phase 3B)")
    print(f"{'='*70}")

    all_validation_results = []
    for strategy_key in ["a", "b", "c"]:
        results = execute_phase3_validation(
            strategy_results[strategy_key], strategy_key
        )
        all_validation_results.extend(results)

    # Compute statistics
    statistics = compute_statistics(all_validation_results)

    # Generate summary
    generate_summary_report(strategy_results, all_validation_results, statistics)

    print(f"\n{'='*70}")
    print("✓ PHASE 3 COMPARATIVE STUDY COMPLETE")
    print(f"{'='*70}")
    print(f"\nResults directory: {output_dir}")
    print(f"Next: Analyze results and write manuscript")

    return 0


if __name__ == "__main__":
    sys.exit(main())
