#!/usr/bin/env python3
"""
Phase 3-4: Agent Prioritization Layer
Agent receives predictions from all available BO calculators and intelligently decides
which configuration to evaluate next.

Decision Patterns:
  1. Consensus: All methods agree → exploit that region
  2. Disagreement: Methods disagree → explore gap
  3. Trade-off: Methods suggest different strategies → risk-adjusted choice

Agent uses convergence tracking to adjust strategy:
  - High improvement rate → can afford exploration (disagreement)
  - Low improvement rate → prefer exploitation (consensus)
  - Near budget limit → prefer conservative (PINN)
"""

import json
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
from enum import Enum


class DecisionStrategy(Enum):
    """Agent decision strategy"""
    EXPLOIT_CONSENSUS = "exploit_consensus"  # All methods agree
    EXPLORE_DISAGREEMENT = "explore_disagreement"  # Methods disagree
    RISK_ADJUSTED = "risk_adjusted"  # Trade-off between return and risk


@dataclass
class AgentDecision:
    """Agent's decision on which config to evaluate next"""
    strategy: DecisionStrategy
    chosen_config: List[int]
    source_method: str  # "gp", "dnn", "pinn", or "consensus"
    predicted_j: float
    reasoning: str
    confidence: float  # 0-1, how confident is this decision?
    expected_value: float  # Expected info gain + expected J


class ConvergenceTracker:
    """Tracks optimization progress to inform risk-adjustment."""

    def __init__(self, window_size: int = 5):
        self.window_size = window_size
        self.best_j_history = []
        self.improvement_rate = 0.0
        self.iterations_completed = 0

    def update(self, new_j: float):
        """Record new evaluation result."""
        self.best_j_history.append(new_j)
        self.iterations_completed += 1

        # Compute improvement rate (slope of best_J over last N iterations)
        if len(self.best_j_history) >= self.window_size:
            recent = self.best_j_history[-self.window_size:]
            diffs = [recent[i+1] - recent[i] for i in range(len(recent)-1)]
            self.improvement_rate = sum(diffs) / len(diffs)

    def get_improvement_rate(self) -> float:
        """Returns improvement per iteration (positive = improving)"""
        return self.improvement_rate


class AgentPrioritizer:
    """
    Agent that decides which BO prediction to trust.
    Uses consensus level, disagreement regions, and convergence to prioritize.
    """

    def __init__(self, max_budget: int = 50, risk_tolerance: float = 0.5):
        """
        Args:
            max_budget: Max iterations available
            risk_tolerance: 0=conservative, 1=aggressive
        """
        self.max_budget = max_budget
        self.risk_tolerance = risk_tolerance
        self.tracker = ConvergenceTracker()

    def decide(
        self,
        bo_predictions: Dict,  # {method: BOPrediction}
        agreement_analysis: Dict,
        iterations_remaining: Optional[int] = None,
        iteration_number: int = 1,
    ) -> AgentDecision:
        """
        Make decision on which config to evaluate next.

        Args:
            bo_predictions: Predictions from all available BO methods
            agreement_analysis: Result from MultiBoCalculator.analyze_agreement()
            iterations_remaining: Budget remaining (if None, assume 50)
            iteration_number: Which iteration is this?

        Returns: AgentDecision with chosen config and reasoning
        """

        if iterations_remaining is None:
            iterations_remaining = self.max_budget - iteration_number + 1

        if not bo_predictions:
            raise ValueError("No BO predictions available")

        consensus_level = agreement_analysis.get("agreement_level", 0.0)
        consensus_config = agreement_analysis.get("consensus_config")
        num_methods = len(bo_predictions)

        # Strategy 1: High Consensus (>67% agreement)
        if consensus_level > 0.67:
            return self._consensus_decision(
                bo_predictions,
                consensus_config,
                iterations_remaining,
                agreement_analysis
            )

        # Strategy 2: High Disagreement (all methods different)
        elif consensus_level <= 1.0 / num_methods:
            return self._exploration_decision(
                bo_predictions,
                agreement_analysis,
                iterations_remaining,
            )

        # Strategy 3: Moderate disagreement - trade-off
        else:
            return self._risk_adjusted_decision(
                bo_predictions,
                iterations_remaining,
                agreement_analysis,
            )

    def _consensus_decision(
        self,
        bo_predictions: Dict,
        consensus_config: List[int],
        iterations_remaining: int,
        agreement_analysis: Dict,
    ) -> AgentDecision:
        """
        High consensus: all methods agree on region.
        Strategy: Exploit this region with highest-predicted config.
        """

        # Find which method predicts highest J for consensus config
        best_pred = None
        best_j = -float('inf')
        best_method = None

        for method, pred in bo_predictions.items():
            # Check if this method's best_config is same or similar to consensus
            if pred.best_config == consensus_config:
                if pred.predicted_j > best_j:
                    best_j = pred.predicted_j
                    best_pred = pred
                    best_method = method

        # If no exact match, use highest J among all predictions
        if best_pred is None:
            best_method = max(bo_predictions.keys(),
                            key=lambda m: bo_predictions[m].predicted_j)
            best_pred = bo_predictions[best_method]

        decision = AgentDecision(
            strategy=DecisionStrategy.EXPLOIT_CONSENSUS,
            chosen_config=best_pred.best_config,
            source_method=best_method,
            predicted_j=best_pred.predicted_j,
            confidence=min(0.95, 0.7 + agreement_analysis["agreement_level"] * 0.25),
            expected_value=best_pred.predicted_j * 0.8,  # Confidence-weighted
            reasoning=f"""
HIGH CONSENSUS STRATEGY (agreement={agreement_analysis['agreement_level']:.0%})
  All {len(bo_predictions)} BO methods converge on region {consensus_config}.

  Decision: Evaluate {best_pred.best_config}

  Analysis:
    • {len(bo_predictions)} methods agree → high confidence
    • Consensus region signals genuine local optimum
    • Method '{best_method.upper()}' predicts highest J = {best_pred.predicted_j:.1f}
    • Low risk: agreement suggests good outcome

  Expected outcome: J ≈ {best_pred.predicted_j:.1f} (confidence: {agreement_analysis['agreement_level']:.0%})
  Iterations remaining: {iterations_remaining}
"""
        )

        return decision

    def _exploration_decision(
        self,
        bo_predictions: Dict,
        agreement_analysis: Dict,
        iterations_remaining: int,
    ) -> AgentDecision:
        """
        High disagreement: methods predict different configs.
        Strategy: Explore disagreement region (high information value).
        """

        # Pick the method that's most "unique" (least consensus)
        # Usually DNN (most aggressive) when available
        preferred_order = ["dnn", "gp", "pinn"]
        source_method = None
        for method in preferred_order:
            if method in bo_predictions:
                source_method = method
                break

        pred = bo_predictions[source_method]

        # Disagreement regions suggest uncertainty
        disagreement_regions = agreement_analysis.get("disagreement_regions", [])

        decision = AgentDecision(
            strategy=DecisionStrategy.EXPLORE_DISAGREEMENT,
            chosen_config=pred.best_config,
            source_method=source_method,
            predicted_j=pred.predicted_j,
            confidence=0.5,  # Disagreement = lower confidence
            expected_value=pred.predicted_j * 0.5,  # Risk-weighted
            reasoning=f"""
HIGH DISAGREEMENT EXPLORATION (unique configs={agreement_analysis['num_unique_configs']})
  BO methods strongly disagree on best config.

  Decision: Evaluate {pred.best_config} from {source_method.upper()}

  Analysis:
    • {len(bo_predictions)} methods disagree (each predicts different config)
    • Disagreement = high model uncertainty = knowledge gap
    • Method '{source_method.upper()}' is most aggressive/explorative
    • High information value: learning why methods disagree
    • Predicted J = {pred.predicted_j:.1f} ± {pred.uncertainty:.2f}

  Risk/Reward:
    • High reward potential (DNN sees opportunities others miss)
    • Medium risk (might not meet consensus expectations)
    • Learning value: high (will clarify disagreement)

  Expected outcome: 50% chance J>{pred.predicted_j:.1f}, 50% chance J<{pred.predicted_j-2*pred.uncertainty:.1f}
  Iterations remaining: {iterations_remaining}
"""
        )

        return decision

    def _risk_adjusted_decision(
        self,
        bo_predictions: Dict,
        iterations_remaining: int,
        agreement_analysis: Dict,
    ) -> AgentDecision:
        """
        Moderate disagreement: trade-off between aggressive (DNN) and conservative (PINN).
        Strategy: Adjust based on remaining budget and improvement rate.
        """

        # Get methods and their predictions
        gp_pred = bo_predictions.get("gp")
        dnn_pred = bo_predictions.get("dnn")
        pinn_pred = bo_predictions.get("pinn")

        # Decide based on remaining budget
        if iterations_remaining > 20:
            # Plenty of time: can afford to be aggressive
            chosen_pred = dnn_pred if dnn_pred else (gp_pred or pinn_pred)
            chosen_method = "dnn"
            risk_level = "high"
            reason = f"Plenty of budget remaining ({iterations_remaining} iterations). Can afford aggressive exploration."

        elif iterations_remaining > 10:
            # Medium budget: balanced approach
            chosen_pred = gp_pred or dnn_pred or pinn_pred
            chosen_method = "gp"
            risk_level = "medium"
            reason = f"Moderate budget remaining ({iterations_remaining} iterations). Using balanced EI-driven approach."

        else:
            # Low budget: be conservative
            chosen_pred = pinn_pred if pinn_pred else (gp_pred or dnn_pred)
            chosen_method = "pinn"
            risk_level = "low"
            reason = f"Low budget remaining ({iterations_remaining} iterations). Using physics-constrained safety approach."

        if chosen_pred is None:
            # Fallback to any available
            chosen_pred = next(iter(bo_predictions.values()))
            chosen_method = list(bo_predictions.keys())[0]

        confidence_map = {"high": 0.6, "medium": 0.7, "low": 0.8}
        expected_value_map = {"high": 0.7, "medium": 0.8, "low": 0.5}

        decision = AgentDecision(
            strategy=DecisionStrategy.RISK_ADJUSTED,
            chosen_config=chosen_pred.best_config,
            source_method=chosen_method,
            predicted_j=chosen_pred.predicted_j,
            confidence=confidence_map[risk_level],
            expected_value=chosen_pred.predicted_j * expected_value_map[risk_level],
            reasoning=f"""
RISK-ADJUSTED TRADE-OFF STRATEGY
  BO methods show mixed signals (moderate agreement).

  Decision: Evaluate {chosen_pred.best_config} from {chosen_method.upper()}

  {reason}

  Method Comparison:
    • DNN:  J≈{dnn_pred.predicted_j:.1f} if available (aggressive, high reward but risky)
    • GP:   J≈{gp_pred.predicted_j:.1f} if available (balanced, medium risk/reward)
    • PINN: J≈{pinn_pred.predicted_j:.1f} if available (conservative, safe but lower upside)

  Chosen: {chosen_method.upper()} (risk level: {risk_level})
  Predicted J: {chosen_pred.predicted_j:.1f} ± {chosen_pred.uncertainty:.2f}

  Iterations remaining: {iterations_remaining}
  Agreement level: {agreement_analysis.get('agreement_level', 0):.0%}
"""
        )

        return decision

    def log_decision(self, decision: AgentDecision, filepath: Optional[str] = None):
        """Log agent decision to file or stdout."""
        output = f"""
{'='*70}
AGENT DECISION (Iteration {self.tracker.iterations_completed + 1})
{'='*70}
Strategy: {decision.strategy.value}
Chosen Config: {decision.chosen_config}
Source Method: {decision.source_method.upper()}
Predicted J: {decision.predicted_j:.2f}
Confidence: {decision.confidence:.1%}
Expected Value: {decision.expected_value:.2f}

{decision.reasoning}

{'='*70}
"""
        print(output)

        if filepath:
            with open(filepath, "a") as f:
                f.write(output + "\n")


if __name__ == "__main__":
    print("Agent Prioritizer Module")
    print("Used by Phase 3-4 optimization loop to decide which config to evaluate next")
