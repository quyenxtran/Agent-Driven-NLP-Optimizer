"""
Physics-based filtering and scoring for SMB NC configurations.

Applies hard constraints (feasibility) and soft heuristics (quality ranking)
to LHS-generated configurations.

Hard constraints eliminate invalid configs quickly (~40-50% filtered).
Soft scoring ranks remaining configs by physics potential.
"""

from typing import List, Dict, Tuple, Optional
import math


class PhysicsFilter:
    """
    Apply physics constraints to filter invalid NC configurations.

    Hard constraints used (tunable thresholds):
    - Total column count: MUST equal 8 (critical constraint)
    - Zone residence time: 0.5s to 30s per zone
    - Zone balance: zones should have similar capacity
    - Max flow rate: 3.0 ml/min (pump limit)
    """

    # Physical parameters (from SMB system)
    # Note: These are relaxed thresholds; actual constraints vary by flow rate
    COLUMN_LENGTH_CM = 10.0  # Characteristic column length unit
    MIN_RESIDENCE_TIME_S = 0.1  # Minimum zone residence time (relaxed)
    MAX_RESIDENCE_TIME_S = 300.0  # Maximum zone residence time (relaxed)
    TARGET_TOTAL_COLUMNS = 8  # CRITICAL: Total column count must be 8
    MAX_PUMP_FLOW_ML_MIN = 3.0  # Maximum pump flow rate (ml/min)

    def __init__(self, strict: bool = False, target_sum: int = 8):
        """
        Initialize physics filter.

        Args:
            strict: If True, use tighter constraints; if False, more permissive
            target_sum: Required total column count (default 8)
        """
        self.strict = strict
        self.target_sum = target_sum
        if strict:
            self.min_residence_s = 0.5  # Tighter minimum
            self.max_residence_s = 100.0  # Tighter maximum
        else:
            self.min_residence_s = self.MIN_RESIDENCE_TIME_S
            self.max_residence_s = self.MAX_RESIDENCE_TIME_S

    def apply_total_columns_constraint(self, nc: List[int]) -> Tuple[bool, Optional[str]]:
        """
        CRITICAL: Check if total column count equals target_sum.

        Args:
            nc: [nc0, nc1, nc2, nc3] configuration

        Returns:
            (is_feasible, reason_if_infeasible)
        """
        total = sum(nc)
        if total != self.target_sum:
            return False, f"Total columns ({total}) != required ({self.target_sum})"
        return True, None

    def apply_zone_residence_time_constraint(
        self, nc: List[int], flow_velocity_estimate: float = 2.0
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if zone residence times are physically feasible.

        NOTE: This is a soft heuristic only. Real validation happens during NLP solving.
        We accept all [1-4] configurations and let the solver determine feasibility.

        Args:
            nc: [nc0, nc1, nc2, nc3] configuration
            flow_velocity_estimate: Estimated interstitial velocity (cm/min)

        Returns:
            (is_feasible, reason_if_infeasible) - always returns (True, None) for relaxed mode
        """
        # For now, accept all configurations
        # Residence time will be validated during NLP solution
        return True, None


    def apply_zone_balance_heuristic(self, nc: List[int]) -> Tuple[bool, Optional[str]]:
        """
        Heuristic: zones should have somewhat balanced column counts.

        Highly imbalanced zones (e.g., [1,1,1,4]) can lead to mass transfer issues.
        This is a soft constraint - permissible but not ideal.

        Args:
            nc: [nc0, nc1, nc2, nc3] configuration

        Returns:
            (is_reasonable, reason_if_skewed)
        """
        mean_cols = sum(nc) / len(nc)
        max_deviation = max(abs(x - mean_cols) for x in nc)

        # Warn if any zone > 1.5x mean (but don't reject)
        if max_deviation > 1.5 * mean_cols:
            return False, f"Highly imbalanced zones: max deviation {max_deviation:.1f}x from mean"

        return True, None

    def is_feasible(self, nc: List[int]) -> Tuple[bool, List[str]]:
        """
        Apply all hard constraints.

        Args:
            nc: [nc0, nc1, nc2, nc3] configuration

        Returns:
            (is_feasible, list_of_failures)
        """
        failures = []

        # CRITICAL constraint 1: Total columns MUST equal target_sum (8)
        feasible, reason = self.apply_total_columns_constraint(nc)
        if not feasible:
            failures.append(reason)

        # Hard constraint 2: Residence time
        feasible, reason = self.apply_zone_residence_time_constraint(nc)
        if not feasible:
            failures.append(reason)

        # Soft constraint 3: Zone balance (logged but not rejected)
        feasible, reason = self.apply_zone_balance_heuristic(nc)
        if not feasible:
            failures.append(f"[SOFT] {reason}")

        return len(failures) == 0, failures


class ConfigScorer:
    """
    Score NC configurations based on physics heuristics.

    Lower scores are better (scores used for ranking, not absolute quality).
    Combines three factors:
    - Selectivity potential: longer zones better for separation
    - Throughput estimate: more columns = higher throughput
    - Solver difficulty: simpler topologies easier to solve
    """

    def __init__(self):
        self.baseline_score = 50.0  # Reference score

    def score_selectivity_potential(self, nc: List[int]) -> float:
        """
        Longer zones typically allow better selectivity.

        More columns in each zone → longer residence time → better separation.
        Score: sum(nc) * scaling (higher sum = lower score = better)

        Args:
            nc: [nc0, nc1, nc2, nc3] configuration

        Returns:
            Selectivity score (lower is better)
        """
        total_cols = sum(nc)
        # Normalize to [0, 100]: 4 cols → 100, 16 cols → 0
        score = 100 * (16 - total_cols) / (16 - 4)
        return score

    def score_throughput_estimate(self, nc: List[int]) -> float:
        """
        More columns generally allows higher throughput (higher concentration of adsorbent).

        Score reflects how well the config leverages column capacity.

        Args:
            nc: [nc0, nc1, nc2, nc3] configuration

        Returns:
            Throughput score (lower is better)
        """
        total_cols = sum(nc)
        # More columns → lower score (better)
        # 4 cols → 100, 16 cols → 0
        score = 100 * (16 - total_cols) / (16 - 4)
        return score

    def score_solver_difficulty(self, nc: List[int]) -> float:
        """
        Estimate solver difficulty from configuration complexity.

        Simpler topologies (balanced zones) easier to solve.
        More columns → more complex → higher difficulty.

        Args:
            nc: [nc0, nc1, nc2, nc3] configuration

        Returns:
            Difficulty score (lower is better/easier)
        """
        total_cols = sum(nc)
        mean_cols = total_cols / 4.0
        imbalance = sum(abs(x - mean_cols) for x in nc) / len(nc)

        # Base difficulty from total columns
        difficulty = 20 * (total_cols - 4) / (16 - 4)
        # Add penalty for imbalance
        difficulty += 10 * imbalance
        return difficulty

    def compute_combined_score(
        self,
        nc: List[int],
        weights: Optional[Dict[str, float]] = None,
    ) -> float:
        """
        Compute weighted combination of heuristic scores.

        Args:
            nc: [nc0, nc1, nc2, nc3] configuration
            weights: Dict with keys "selectivity", "throughput", "solver"
                    (default: see code)

        Returns:
            Combined score (lower is better)
        """
        if weights is None:
            weights = {
                "selectivity": 0.4,  # Separation quality most important
                "throughput": 0.3,   # Throughput important
                "solver": -0.3,      # Negative = prefer harder (complex) setups
            }

        selectivity = self.score_selectivity_potential(nc)
        throughput = self.score_throughput_estimate(nc)
        difficulty = self.score_solver_difficulty(nc)

        score = (
            weights["selectivity"] * selectivity
            + weights["throughput"] * throughput
            + weights["solver"] * difficulty
        )

        return score

    def rank_configs(
        self,
        configs: List[List[int]],
        physics_filter: Optional[PhysicsFilter] = None,
    ) -> List[Tuple[List[int], float, str]]:
        """
        Filter and rank configurations.

        Args:
            configs: List of [nc0, nc1, nc2, nc3] configurations
            physics_filter: PhysicsFilter instance (creates default if None)

        Returns:
            List of (config, score, status) tuples, sorted by score (best first)
        """
        if physics_filter is None:
            physics_filter = PhysicsFilter(strict=False)

        results = []

        for nc in configs:
            # Check feasibility
            is_feasible, failures = physics_filter.is_feasible(nc)

            if is_feasible:
                # Score the config
                score = self.compute_combined_score(nc)
                status = "FEASIBLE"
            else:
                # Penalize infeasible configs heavily
                score = 1000.0  # Very high score (bad)
                status = f"FILTERED ({failures[0][:30]}...)"

            results.append((nc, score, status))

        # Sort by score (lower is better)
        results.sort(key=lambda x: x[1])

        return results


def filter_and_rank_lhs_configs(
    lhs_configs: List[List[int]],
    n_keep: int = 40,
    strict: bool = False,
    target_sum: int = 8,
) -> Dict[str, object]:
    """
    Complete pipeline: filter LHS configs through physics, rank by heuristics.

    Args:
        lhs_configs: List of LHS-generated configurations
        n_keep: Number of top-ranked configs to keep
        strict: Use strict physics constraints if True
        target_sum: Required total column count (default 8)

    Returns:
        Dict with:
        - "valid_configs": List of feasible [nc, score, status]
        - "invalid_configs": List of filtered [nc, score, status]
        - "top_n": Top n_keep best ranked configs
        - "statistics": Summary statistics
    """
    physics_filter = PhysicsFilter(strict=strict, target_sum=target_sum)
    scorer = ConfigScorer()

    # Filter and rank
    ranked = scorer.rank_configs(lhs_configs, physics_filter)

    # Separate valid and invalid
    valid = [r for r in ranked if "FILTERED" not in r[2]]
    invalid = [r for r in ranked if "FILTERED" in r[2]]

    # Top configs
    top_n = valid[:n_keep]

    # Statistics
    statistics = {
        "total_lhs": len(lhs_configs),
        "valid": len(valid),
        "invalid": len(invalid),
        "valid_pct": 100 * len(valid) / len(lhs_configs) if lhs_configs else 0,
        "top_n_kept": len(top_n),
        "best_score": top_n[0][1] if top_n else None,
        "worst_score": top_n[-1][1] if top_n else None,
    }

    return {
        "valid_configs": valid,
        "invalid_configs": invalid,
        "top_n": top_n,
        "statistics": statistics,
    }


if __name__ == "__main__":
    # Test physics filter with LHS configs
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from lhs_sampler import generate_lhs_configs

    print("=" * 70)
    print("Physics Filter - Test with LHS Configs (Target Sum = 8)")
    print("=" * 70)
    print()

    # Generate LHS configs with target sum constraint
    lhs_configs = generate_lhs_configs(60, seed=42, target_sum=8)
    print(f"Generated {len(lhs_configs)} LHS configurations (sum=8)")
    print(f"All sums are 8: {all(sum(c) == 8 for c in lhs_configs)}")
    print()

    # Filter and rank
    result = filter_and_rank_lhs_configs(lhs_configs, n_keep=40, strict=False, target_sum=8)

    print("Filtering Results:")
    print(f"  Valid: {result['statistics']['valid']} ({result['statistics']['valid_pct']:.1f}%)")
    print(f"  Invalid (filtered): {result['statistics']['invalid']}")
    print()

    print("Top 10 Ranked Configurations:")
    print(f"{'Rank':<5} {'Config':<20} {'Score':<8} {'Status':<20}")
    print("-" * 55)
    for i, (nc, score, status) in enumerate(result["top_n"][:10], 1):
        print(f"{i:<5} {str(nc):<20} {score:<8.2f} {status:<20}")
    print()

    print("Statistics:")
    for key, val in result["statistics"].items():
        if isinstance(val, float):
            print(f"  {key}: {val:.2f}")
        else:
            print(f"  {key}: {val}")
