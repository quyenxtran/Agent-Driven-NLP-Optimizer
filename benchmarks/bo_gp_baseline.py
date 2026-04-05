"""
Bayesian Optimization with Gaussian Process for SMB NC configuration selection.

Provides a deterministic baseline for comparison against LLM agent and LHS methods.
Uses Expected Improvement (EI) as acquisition function.
"""

from typing import List, Dict, Tuple, Optional
import numpy as np
from dataclasses import dataclass
import json


@dataclass
class BOGPConfig:
    """Configuration for BO+GP baseline"""
    n_initial_random: int = 3  # Random points before using GP
    acquisition_type: str = "ei"  # Expected Improvement
    kernel_lengthscale: float = 2.0
    kernel_variance: float = 1.0
    noise_variance: float = 0.1
    exploration_factor: float = 2.576  # 99.5% UCB


class SimpleGPMean:
    """
    Lightweight Gaussian Process using Mean Estimator.

    In production, use sklearn.gaussian_process.GaussianProcessRegressor.
    This minimal implementation for demonstration purposes.
    """

    def __init__(self, lengthscale: float = 2.0, variance: float = 1.0, noise: float = 0.1):
        self.lengthscale = lengthscale
        self.variance = variance
        self.noise = noise
        self.X_train = []
        self.y_train = []
        self.mean_y = 0.0
        self.std_y = 1.0

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        """Fit GP to training data"""
        self.X_train = np.array(X)
        self.y_train = np.array(y)
        self.mean_y = np.mean(self.y_train)
        self.std_y = np.std(self.y_train) if np.std(self.y_train) > 0 else 1.0

    def predict(self, X: np.ndarray, return_std: bool = True) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """
        Predict mean and std at test points.
        Uses RBF kernel with Euclidean distance.
        """
        X = np.atleast_2d(np.array(X))

        if len(self.X_train) == 0:
            mean = np.full(len(X), self.mean_y)
            std = np.full(len(X), self.std_y) if return_std else None
            return (mean, std) if return_std else mean

        # Compute RBF kernel distances
        X_train = np.atleast_2d(self.X_train)
        distances = np.linalg.norm(X[:, np.newaxis, :] - X_train[np.newaxis, :, :], axis=2)
        K_test_train = self.variance * np.exp(-distances**2 / (2 * self.lengthscale**2))

        # Simple mean estimate: inverse-distance weighted average
        weights = K_test_train / (np.sum(K_test_train, axis=1, keepdims=True) + 1e-6)
        mean = np.dot(weights, self.y_train)

        # Uncertainty: higher when far from training data
        if return_std:
            std = self.std_y * (1.0 - np.max(K_test_train / self.variance, axis=1))
            std = np.maximum(std, 0.01)  # Minimum uncertainty
            return mean, std

        return mean


class BOGPSelector:
    """
    Bayesian Optimization with Gaussian Process for NC configuration selection.

    Selects next configuration to evaluate based on Expected Improvement (EI).
    """

    def __init__(self, config_space: List[Tuple[int, int, int, int]], cfg: BOGPConfig):
        """
        Initialize BO+GP selector.

        Args:
            config_space: List of valid [nc0, nc1, nc2, nc3] configurations
            cfg: BOGPConfig with BO hyperparameters
        """
        self.config_space = config_space
        self.cfg = cfg
        self.gp = SimpleGPMean(cfg.kernel_lengthscale, cfg.kernel_variance, cfg.noise_variance)
        self.evaluated_configs = []
        self.evaluated_values = []
        self.config_to_idx = {tuple(c): i for i, c in enumerate(config_space)}

    def select_initial(self, n_init: int = 3) -> Tuple[int, Tuple[int, int, int, int]]:
        """Select initial random configurations"""
        # Return first N configs (deterministic for reproducibility)
        idx = min(len(self.evaluated_configs), n_init - 1)
        if idx < len(self.config_space):
            config = self.config_space[idx]
            return idx, config
        return 0, self.config_space[0]

    def select_next(self) -> Tuple[int, Tuple[int, int, int, int]]:
        """
        Select next configuration using Expected Improvement (EI).

        Returns:
            (config_index, configuration)
        """
        if len(self.evaluated_values) < self.cfg.n_initial_random:
            # Use random/sequential selection for initial points
            return self.select_initial(self.cfg.n_initial_random)

        # Fit GP to observed data
        X_train = np.array(self.evaluated_configs)
        y_train = np.array(self.evaluated_values)
        self.gp.fit(X_train, y_train)

        # Predict on all configs in space
        X_test = np.array(self.config_space, dtype=float)
        mean, std = self.gp.predict(X_test, return_std=True)

        # Compute Expected Improvement (EI)
        f_best = np.max(y_train)
        ei = self._expected_improvement(mean, std, f_best)

        # Select configuration with highest EI
        # Break ties by selecting unexplored config
        best_idx = np.argmax(ei)

        # Ensure we don't select already-evaluated config
        evaluated_set = set(tuple(c) for c in self.evaluated_configs)
        for idx in np.argsort(-ei):  # Sort by descending EI
            config = self.config_space[idx]
            if tuple(config) not in evaluated_set:
                best_idx = idx
                break

        config = self.config_space[best_idx]
        return best_idx, config

    def _expected_improvement(self, mean: np.ndarray, std: np.ndarray, f_best: float) -> np.ndarray:
        """Compute Expected Improvement acquisition function"""
        # Avoid division by zero
        improvement = mean - f_best
        Z = improvement / (std + 1e-6)

        # EI = improvement * Phi(Z) + std * phi(Z)
        from scipy.stats import norm
        ei = improvement * norm.cdf(Z) + std * norm.pdf(Z)
        ei = np.where(std > 0, ei, 0)  # Zero EI where uncertainty is zero

        return np.maximum(ei, 0)

    def observe(self, config: Tuple[int, int, int, int], value: float) -> None:
        """Record an observation from evaluating a configuration"""
        config_list = list(config)
        self.evaluated_configs.append(config_list)
        self.evaluated_values.append(value)

    def get_best_config(self) -> Optional[Tuple[int, int, int, int]]:
        """Return the best configuration found so far"""
        if not self.evaluated_values:
            return None
        best_idx = np.argmax(self.evaluated_values)
        return tuple(self.evaluated_configs[best_idx])


def create_bo_gp_baseline(
    config_space: List[Tuple[int, int, int, int]] = None,
    cfg: BOGPConfig = None,
) -> BOGPSelector:
    """
    Create a BO+GP baseline selector.

    Args:
        config_space: 31 valid NC configurations (default: generate from sum=8)
        cfg: BO hyperparameters

    Returns:
        Initialized BOGPSelector
    """
    if config_space is None:
        from .lhs_sampler import generate_valid_constrained_configs
        config_space = generate_valid_constrained_configs(target_sum=8)

    if cfg is None:
        cfg = BOGPConfig()

    return BOGPSelector(config_space, cfg)


if __name__ == "__main__":
    import sys
    sys.path.insert(0, 'benchmarks')

    from lhs_sampler import generate_valid_constrained_configs

    print("=" * 70)
    print("BO+GP Baseline - Demonstration")
    print("=" * 70)
    print()

    # Generate config space
    config_space = generate_valid_constrained_configs(target_sum=8)
    print(f"Config space: {len(config_space)} valid configurations")
    print()

    # Create selector
    selector = create_bo_gp_baseline(config_space)
    print(f"BO+GP initialized:")
    print(f"  Kernel lengthscale: {selector.cfg.kernel_lengthscale}")
    print(f"  Initial random: {selector.cfg.n_initial_random}")
    print()

    # Simulate some evaluations
    print("Simulating 10 evaluations...")
    for iteration in range(10):
        config_idx, config = selector.select_next()

        # Simulate noisy objective: prefer balanced configs
        imbalance = max(config) - min(config)
        score = 50.0 - imbalance * 2 + np.random.normal(0, 1)

        selector.observe(config, score)

        best = selector.get_best_config()
        best_val = max(selector.evaluated_values) if selector.evaluated_values else 0

        print(f"  Iter {iteration+1}: config={config}, score={score:.2f}, best_so_far={best_val:.2f}")

    print()
    print(f"Best configuration found: {selector.get_best_config()}")
    print(f"Best value: {max(selector.evaluated_values):.2f}")
