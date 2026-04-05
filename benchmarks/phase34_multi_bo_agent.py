#!/usr/bin/env python3
"""
Phase 3-4: Multi-BO Agent Orchestrator
Implements the complete optimization loop:
  1. Load Phase 1+2B training data
  2. Fit available BO surrogates (progressive: GP → DNN → PINN)
  3. Agent receives BO predictions and intelligently decides next config
  4. Evaluate chosen config with IPOPT
  5. Update all BO models with new data
  6. Repeat until budget exhausted

Progressive Tool Availability:
  - Iteration 1-N: GP only (≥1 point)
  - After ~100 data: GP + DNN
  - After ~150 data: GP + DNN + PINN

Agent Decision Strategies:
  - Consensus (>67% agreement) → Exploit best prediction
  - Disagreement (all different) → Explore disagreement region
  - Trade-off (moderate) → Risk-adjusted based on budget
"""

import argparse
import json
import os
import sys
import subprocess
import tempfile
from pathlib import Path
from typing import List, Dict, Optional, Tuple

import numpy as np

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "benchmarks"))

from phase3_data_aggregation import aggregate_training_data
from phase3_multi_bo_calculator import MultiBoCalculator, BOPrediction
from phase3_agent_prioritizer import AgentPrioritizer, AgentDecision


def generate_all_nc_configs() -> List[List[int]]:
    """Generate all 31 valid NC configurations (sum = 8, each ≥1)."""
    configs = []
    for n0 in range(1, 6):  # 1-5
        for n1 in range(1, 8 - n0):  # 1 to (8-n0-1)
            for n2 in range(1, 8 - n0 - n1):  # 1 to (8-n0-n1-1)
                n3 = 8 - n0 - n1 - n2
                if n3 >= 1:
                    configs.append([n0, n1, n2, n3])
    return sorted(configs)


def evaluate_candidate(
    nc: List[int],
    run_name: str,
    artifact_dir: str,
    solver_name: str = "auto",
    linear_solver: str = "ma97",
    nfex: int = 6,
    nfet: int = 3,
    ncp: int = 2,
) -> Dict:
    """
    Evaluate a single NC configuration using run_stage.py.
    Uses loose constraints for Phase 3-4 development.

    Returns dict with:
    {
        "status": "ok" | "error" | "timeout",
        "nc": [n0, n1, n2, n3],
        "productivity": float,
        "purity": float,
        "recovery_ga": float,
        "recovery_ma": float,
        "flows": {...}
    }
    """

    nc_str = f"[{nc[0]},{nc[1]},{nc[2]},{nc[3]}]"

    cmd = [
        sys.executable, "-m", "benchmarks.run_stage",
        "--stage", "optimize-layouts",
        "--run-name", run_name,
        "--artifact-dir", artifact_dir,
        "--nc", nc_str,
        "--solver-name", solver_name,
        "--linear-solver", linear_solver,
        "--nfex", str(nfex),
        "--nfet", str(nfet),
        "--ncp", str(ncp),
        "--purity-min", "0.20",  # LOOSE constraints
        "--recovery-ga-min", "0.20",
        "--recovery-ma-min", "0.20",
        "--max-pump-flow", "3.0",
    ]

    try:
        # Set environment: disable reference gate (agent provides warm-start via BO predictions)
        env = os.environ.copy()
        env["SMB_REFERENCE_GATE"] = "0"

        result = subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,  # 5 min per optimization
            env=env,
        )

        if result.returncode == 0:
            # Parse JSON output
            for line in result.stdout.split('\n'):
                if '"artifact"' in line:
                    try:
                        artifact_data = json.loads(line)
                        artifact_path = artifact_data.get('artifact')

                        if artifact_path and Path(artifact_path).exists():
                            with open(artifact_path) as f:
                                artifact = json.load(f)

                            metrics = artifact.get("metrics", {})
                            return {
                                "status": "ok",
                                "nc": nc,
                                "productivity": artifact.get("J_validated"),
                                "purity": metrics.get("purity_ex_meoh_free"),
                                "recovery_ga": metrics.get("recovery_ex_GA"),
                                "recovery_ma": metrics.get("recovery_ex_MA"),
                                "flows": artifact.get("optimized_flows", {}),
                            }
                    except (json.JSONDecodeError, TypeError):
                        pass

        return {
            "status": "error",
            "nc": nc,
            "error": result.stderr[:200],
        }

    except subprocess.TimeoutExpired:
        return {
            "status": "timeout",
            "nc": nc,
        }
    except Exception as e:
        return {
            "status": "exception",
            "nc": nc,
            "error": str(e),
        }


class Phase34Orchestrator:
    """Main orchestration loop for Phase 3-4 optimization."""

    def __init__(
        self,
        max_iterations: int = 50,
        artifact_dir: str = "artifacts/phase34_multi_bo_agent",
        risk_tolerance: float = 0.5,
    ):
        self.max_iterations = max_iterations
        self.artifact_dir = Path(artifact_dir)
        self.artifact_dir.mkdir(parents=True, exist_ok=True)

        self.calculator = MultiBoCalculator()
        self.prioritizer = AgentPrioritizer(max_budget=max_iterations, risk_tolerance=risk_tolerance)

        self.training_data = []
        self.evaluation_history = []
        self.best_j = -float('inf')

    def run(
        self,
        phase1_dir: str = "artifacts/phase1_lhs_only",
        phase2b_dir: str = "artifacts/phase2b_lhs_seeding",
    ) -> Dict:
        """
        Execute Phase 3-4 optimization loop.

        Returns: summary dict with results and history.
        """

        print("="*70)
        print("PHASE 3-4: MULTI-BO AGENT ORCHESTRATION")
        print("="*70)
        print(f"Max iterations: {self.max_iterations}")
        print(f"Artifact directory: {self.artifact_dir}")
        print("")

        # Step 1: Aggregate Phase 1 + Phase 2B data
        print("Step 1: Aggregating training data...")
        training_file = self.artifact_dir / "phase3_training_data.json"
        aggregate_training_data(phase1_dir, phase2b_dir, str(training_file))

        # Step 2: Load training data
        print("\nStep 2: Loading training data...")
        if not self.calculator.load_training_data(str(training_file)):
            print("❌ Failed to load training data")
            return {"status": "failed"}

        self.training_data = self.calculator.training_data

        # Step 3: Fit initial surrogates
        print("\nStep 3: Fitting initial BO surrogates...")
        fit_results = self.calculator.fit_surrogates()
        print(f"  Fitted surrogates: {[m for m, ok in fit_results.items() if ok]}")

        # Step 4: Main optimization loop
        print(f"\nStep 4: Optimization loop ({self.max_iterations} iterations)...")
        all_nc_configs = generate_all_nc_configs()

        for iteration in range(1, self.max_iterations + 1):
            print(f"\n{'─'*70}")
            print(f"Iteration {iteration}/{self.max_iterations}")
            print(f"Current best J: {self.best_j:.2f}" if self.best_j > -float('inf') else "Current best J: N/A")

            # Get predictions from all available BO methods
            predictions = self.calculator.get_predictions()
            if not predictions:
                print("❌ No predictions available")
                break

            print(f"Active BO methods: {list(predictions.keys())}")

            # Analyze agreement
            analysis = self.calculator.analyze_agreement(predictions)

            # Agent decides
            iterations_remaining = self.max_iterations - iteration + 1
            decision = self.prioritizer.decide(
                predictions,
                analysis,
                iterations_remaining=iterations_remaining,
                iteration_number=iteration,
            )

            # Log decision
            self.prioritizer.log_decision(decision)

            # Evaluate chosen config
            print(f"\nEvaluating config {decision.chosen_config}...")
            run_name = f"phase34_iter{iteration:02d}_nc_{decision.chosen_config[0]}{decision.chosen_config[1]}{decision.chosen_config[2]}{decision.chosen_config[3]}"
            eval_result = evaluate_candidate(
                decision.chosen_config,
                run_name=run_name,
                artifact_dir=str(self.artifact_dir / "evaluations"),
            )

            if eval_result["status"] == "ok":
                productivity = eval_result.get("productivity")
                purity = eval_result.get("purity")
                recovery_ga = eval_result.get("recovery_ga")
                recovery_ma = eval_result.get("recovery_ma")

                print(f"✓ Evaluation successful")
                print(f"  Productivity: {productivity:.2f}")
                print(f"  Purity: {purity:.3f}")
                print(f"  Recovery GA: {recovery_ga:.3f}")
                print(f"  Recovery MA: {recovery_ma:.3f}")

                if productivity is not None and productivity > self.best_j:
                    self.best_j = productivity
                    print(f"  🎯 NEW BEST: {productivity:.2f}")

                # Add to training data
                new_point = {
                    "source": "phase34",
                    "iteration": iteration,
                    "agent_decision": decision.strategy.value,
                    "nc": decision.chosen_config,
                    "seed_idx": None,
                    "flows": eval_result.get("flows", {}),
                    "metrics": {
                        "productivity": productivity,
                        "purity": purity,
                        "recovery_ga": recovery_ga,
                        "recovery_ma": recovery_ma,
                    },
                    "feasible": (purity >= 0.20 and recovery_ga >= 0.20 and recovery_ma >= 0.20),
                }
                self.training_data.append(new_point)

                # Retrain all surrogates
                print("\nRetraining BO surrogates...")
                self.calculator.fit_surrogates()

            else:
                print(f"⚠️  Evaluation failed: {eval_result.get('error', eval_result['status'])}")

            # Record iteration
            self.evaluation_history.append({
                "iteration": iteration,
                "decision": decision.strategy.value,
                "config": decision.chosen_config,
                "source_method": decision.source_method,
                "predicted_j": decision.predicted_j,
                "actual_j": eval_result.get("productivity"),
                "status": eval_result["status"],
            })

        # Step 5: Final summary
        print("\n" + "="*70)
        print("PHASE 3-4 COMPLETE")
        print("="*70)

        summary = {
            "method": "Phase 3-4: Multi-BO + Agent",
            "iterations": len(self.evaluation_history),
            "best_j": self.best_j,
            "training_points_collected": len([p for p in self.training_data if p.get("source") == "phase34"]),
            "evaluation_history": self.evaluation_history,
            "final_training_data": self.training_data,
        }

        summary_file = self.artifact_dir / "phase34_summary.json"
        with open(summary_file, "w") as f:
            json.dump(summary, f, indent=2)

        print(f"\nResults saved to: {self.artifact_dir}")
        print(f"Best J achieved: {self.best_j:.2f}")
        print(f"Evaluations: {len(self.evaluation_history)}")

        return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 3-4: Multi-BO Agent Optimization")
    parser.add_argument("--max-iterations", type=int, default=50)
    parser.add_argument("--artifact-dir", default="artifacts/phase34_multi_bo_agent")
    parser.add_argument("--phase1-dir", default="artifacts/phase1_lhs_only")
    parser.add_argument("--phase2b-dir", default="artifacts/phase2b_lhs_seeding")
    parser.add_argument("--risk-tolerance", type=float, default=0.5)

    args = parser.parse_args()

    orchestrator = Phase34Orchestrator(
        max_iterations=args.max_iterations,
        artifact_dir=args.artifact_dir,
        risk_tolerance=args.risk_tolerance,
    )

    result = orchestrator.run(
        phase1_dir=args.phase1_dir,
        phase2b_dir=args.phase2b_dir,
    )

    return 0 if result.get("status") != "failed" else 1


if __name__ == "__main__":
    sys.exit(main())
