"""
Latin Hypercube Sampling for SMB NC configuration space.

Generates stratified samples of the 4D NC space to ensure systematic coverage
before agent-driven exploration begins.

Example:
    configs = generate_lhs_configs(n_samples=60, seed=42)
    valid_configs = [c for c in configs if is_valid_nc_config(c)]
"""

import numpy as np
from typing import List, Dict, Tuple


def generate_lhs_configs(n_samples: int = 60, seed: int = 42) -> List[List[int]]:
    """
    Generate Latin Hypercube stratified samples of NC configuration space.

    Each NC dimension [0, 1, 2, 3] ranges from 1 to 4 columns.
    LHS ensures each dimension is divided into n_samples equal strata
    with one sample per stratum, avoiding clustering.

    Args:
        n_samples: Number of configurations to generate (60 recommended)
        seed: Random seed for reproducibility

    Returns:
        List of [nc0, nc1, nc2, nc3] configurations where each is in [1, 4]

    Example:
        >>> configs = generate_lhs_configs(60, seed=42)
        >>> len(configs)
        60
        >>> all(1 <= nc <= 4 for c in configs for nc in c)
        True
    """
    np.random.seed(seed)

    # Number of possible values per dimension
    min_val, max_val = 1, 4
    n_values = max_val - min_val + 1  # 4 values: [1, 2, 3, 4]

    # Generate Latin Hypercube samples in [0, 1]^4
    lhs_samples = latin_hypercube_samples(n_samples, n_dim=4, seed=seed)

    configs = []
    for sample in lhs_samples:
        # Map [0, 1] to [1, 4] for each dimension
        nc = []
        for dim_val in sample:
            # Divide [0, 1] into strata
            stratum_idx = int(dim_val * n_values)
            # Clamp to valid range
            stratum_idx = min(stratum_idx, n_values - 1)
            nc_val = min_val + stratum_idx
            nc.append(nc_val)

        configs.append(nc)

    return configs


def latin_hypercube_samples(
    n_samples: int, n_dim: int = 4, seed: int = 42
) -> np.ndarray:
    """
    Generate Latin Hypercube samples in [0, 1]^n_dim.

    Ensures that each dimension is partitioned into n_samples equal bins
    with exactly one sample per bin, providing stratified coverage.

    Args:
        n_samples: Number of samples
        n_dim: Number of dimensions (default 4 for NC space)
        seed: Random seed

    Returns:
        Array of shape (n_samples, n_dim) with values in [0, 1]
    """
    np.random.seed(seed)

    # Create stratified samples: one per stratum in each dimension
    samples = np.zeros((n_samples, n_dim))

    for dim in range(n_dim):
        # Generate n_samples positions in [0, 1]
        # Stratum i contains values in [i/n_samples, (i+1)/n_samples]
        strata = np.arange(n_samples) / n_samples
        stratum_widths = 1.0 / n_samples

        # Random offset within each stratum
        offsets = np.random.uniform(0, stratum_widths, n_samples)
        samples[:, dim] = strata + offsets

    # Shuffle each column independently to avoid correlation
    for dim in range(n_dim):
        samples[:, dim] = np.random.permutation(samples[:, dim])

    return samples


def is_valid_nc_config(nc: List[int]) -> bool:
    """
    Check basic validity of NC configuration.

    Validates:
    - Length is 4
    - Each value in [1, 4]
    - Total columns reasonable (3-16)

    Note: This is a fast pre-filter. Full feasibility checked during
    physics filtering phase.

    Args:
        nc: [nc0, nc1, nc2, nc3] configuration

    Returns:
        True if configuration passes basic validity checks
    """
    if not isinstance(nc, (list, tuple)) or len(nc) != 4:
        return False

    if not all(isinstance(x, (int, float)) for x in nc):
        return False

    # Convert to int if needed
    nc_int = [int(x) for x in nc]

    # Check ranges
    if not all(1 <= x <= 4 for x in nc_int):
        return False

    # Check total columns reasonable
    total_cols = sum(nc_int)
    if total_cols < 3 or total_cols > 16:
        return False

    return True


def get_config_stats(configs: List[List[int]]) -> Dict[str, float]:
    """
    Compute coverage statistics for generated configs.

    Args:
        configs: List of [nc0, nc1, nc2, nc3] configurations

    Returns:
        Dict with statistics like mean, std, min, max per dimension
    """
    configs_array = np.array(configs)

    stats = {}
    for dim in range(4):
        dim_vals = configs_array[:, dim]
        stats[f"dim{dim}_mean"] = float(np.mean(dim_vals))
        stats[f"dim{dim}_std"] = float(np.std(dim_vals))
        stats[f"dim{dim}_min"] = int(np.min(dim_vals))
        stats[f"dim{dim}_max"] = int(np.max(dim_vals))

    stats["total_configs"] = len(configs)
    stats["unique_configs"] = len(set(tuple(c) for c in configs))

    return stats


if __name__ == "__main__":
    # Test LHS sampler
    print("=" * 70)
    print("LHS Configuration Sampler - Test")
    print("=" * 70)
    print()

    # Generate samples
    configs = generate_lhs_configs(n_samples=60, seed=42)
    print(f"Generated {len(configs)} LHS samples")
    print(f"First 5 configs: {configs[:5]}")
    print()

    # Validate
    valid = [c for c in configs if is_valid_nc_config(c)]
    print(f"Valid configs: {len(valid)}/{len(configs)}")
    print()

    # Statistics
    stats = get_config_stats(valid)
    print("Coverage Statistics (valid configs):")
    for key, val in sorted(stats.items()):
        if isinstance(val, float):
            print(f"  {key}: {val:.2f}")
        else:
            print(f"  {key}: {val}")
    print()

    # Dimension coverage
    print("Dimension Coverage (valid configs):")
    valid_array = np.array(valid)
    for dim in range(4):
        values = sorted(valid_array[:, dim])
        counts = {1: 0, 2: 0, 3: 0, 4: 0}
        for v in values:
            counts[v] += 1
        print(f"  dim{dim}: {counts}")
