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


def generate_valid_constrained_configs(target_sum: int = 8, min_val: int = 1, max_val: int = 4) -> List[List[int]]:
    """
    Generate all valid NC configurations where sum(nc) = target_sum.

    Each dimension must be in [min_val, max_val].

    Args:
        target_sum: Target sum of all four dimensions (default 8)
        min_val: Minimum value per dimension (default 1)
        max_val: Maximum value per dimension (default 4)

    Returns:
        List of all valid [nc0, nc1, nc2, nc3] configurations
    """
    configs = []
    for nc0 in range(min_val, max_val + 1):
        for nc1 in range(min_val, max_val + 1):
            for nc2 in range(min_val, max_val + 1):
                for nc3 in range(min_val, max_val + 1):
                    if nc0 + nc1 + nc2 + nc3 == target_sum:
                        configs.append([nc0, nc1, nc2, nc3])
    return configs


def generate_lhs_configs(n_samples: int = 60, seed: int = 42, target_sum: int = 8) -> List[List[int]]:
    """
    Generate Latin Hypercube stratified samples of NC configuration space.

    Generates configurations where each NC dimension [0, 1, 2, 3] is in [1, 4]
    and the total sum equals target_sum (default 8).

    LHS stratifies the valid configuration space to ensure systematic coverage
    with one sample per stratum, avoiding clustering.

    Args:
        n_samples: Number of configurations to generate (60 recommended)
        seed: Random seed for reproducibility
        target_sum: Total column count constraint (default 8)

    Returns:
        List of [nc0, nc1, nc2, nc3] configurations with sum = target_sum

    Example:
        >>> configs = generate_lhs_configs(60, seed=42, target_sum=8)
        >>> len(configs) <= 60
        True
        >>> all(sum(c) == 8 for c in configs)
        True
    """
    np.random.seed(seed)

    # Generate all valid configurations with sum = target_sum
    all_valid_configs = generate_valid_constrained_configs(target_sum)

    if len(all_valid_configs) == 0:
        raise ValueError(f"No valid configurations found with sum={target_sum}")

    # If we have fewer valid configs than requested samples, return all
    if len(all_valid_configs) <= n_samples:
        return all_valid_configs

    # Otherwise, use LHS to select a stratified subset
    # Encode each config as a position in the valid config space
    n_valid = len(all_valid_configs)

    # Generate LHS samples in [0, 1]^1 (just one dimension for selection)
    lhs_samples = latin_hypercube_samples(n_samples, n_dim=1, seed=seed)

    # Map LHS samples to indices in the valid config list
    selected_indices = set()
    for sample in lhs_samples:
        # Map [0, 1] to [0, n_valid)
        idx = int(sample[0] * n_valid)
        idx = min(idx, n_valid - 1)
        selected_indices.add(idx)

    # Select configs in order to preserve stratification
    configs = [all_valid_configs[i] for i in sorted(selected_indices)]

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


def is_valid_nc_config(nc: List[int], target_sum: int = 8) -> bool:
    """
    Check basic validity of NC configuration.

    Validates:
    - Length is 4
    - Each value in [1, 4]
    - Total columns equals target_sum (default 8)

    Note: This is a fast pre-filter. Full feasibility checked during
    physics filtering phase.

    Args:
        nc: [nc0, nc1, nc2, nc3] configuration
        target_sum: Required total column count (default 8)

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

    # Check total columns equals target_sum (CRITICAL CONSTRAINT)
    total_cols = sum(nc_int)
    if total_cols != target_sum:
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
    print("LHS Configuration Sampler - Test (Target Sum = 8)")
    print("=" * 70)
    print()

    # Generate all valid configs for reference
    all_valid = generate_valid_constrained_configs(target_sum=8)
    print(f"Total valid configurations with sum=8: {len(all_valid)}")
    print()

    # Generate samples
    configs = generate_lhs_configs(n_samples=60, seed=42, target_sum=8)
    print(f"Generated {len(configs)} LHS samples (requested 60)")
    print(f"First 5 configs: {configs[:5]}")
    print(f"Sums: {[sum(c) for c in configs[:5]]}")
    print()

    # Validate
    valid = [c for c in configs if is_valid_nc_config(c, target_sum=8)]
    print(f"Valid configs: {len(valid)}/{len(configs)}")
    print(f"All configs sum to 8: {all(sum(c) == 8 for c in valid)}")
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
