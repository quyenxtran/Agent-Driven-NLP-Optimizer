#!/usr/bin/env python3
"""
Phase 2 Recovery and Aggregation

If Phase 2 job runs out of walltime, this script:
1. Identifies which NCs were fully completed
2. Aggregates results from completed NCs
3. Creates a continuation job for incomplete NCs
4. Merges results at the end for a complete Phase 2 summary

Usage:
  python phase2_recovery_and_aggregate.py --check-progress
  python phase2_recovery_and_aggregate.py --aggregate-results
  python phase2_recovery_and_aggregate.py --prepare-continuation
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

REPO_ROOT = Path(__file__).parent
ARTIFACT_DIR = REPO_ROOT / "artifacts" / "phase2_lhs_seeding"

# All NCs that need to be processed
ALL_NCS = [
    "[1,1,2,4]", "[1,1,3,3]", "[1,1,4,2]", "[1,2,1,4]", "[1,2,4,1]",
    "[1,3,1,3]", "[1,3,2,2]", "[2,1,2,3]", "[2,2,1,3]", "[2,2,2,2]",
    "[1,1,1,5]", "[1,1,5,1]", "[1,5,1,1]", "[5,1,1,1]", "[1,2,2,3]",
    "[1,2,3,2]", "[1,3,2,1]", "[2,1,1,4]", "[2,1,3,2]", "[2,1,4,1]",
    "[2,2,3,1]", "[2,3,1,2]", "[2,3,2,1]", "[3,1,1,3]", "[3,1,2,2]",
    "[3,1,3,1]", "[3,2,1,2]", "[3,2,2,1]", "[3,3,1,1]", "[4,1,1,2]",
    "[4,1,2,1]", "[4,2,1,1]",
]


def check_progress() -> Tuple[int, Set[str], Dict[str, int]]:
    """
    Check which NCs have been started and how many seeds per NC.

    Returns: (total_seeds, ncs_started, seeds_per_nc)
    """
    if not ARTIFACT_DIR.exists():
        return 0, set(), {}

    ipopt_logs = list(ARTIFACT_DIR.glob("ipopt_logs/*.log"))

    # Extract NC and seed info from filenames
    # Example: ipopt_phase2_opt_nc_[1,1,2,4]_seed_0_...
    nc_seeds = {}
    for log in ipopt_logs:
        name = log.stem
        parts = name.split("seed_")
        if len(parts) > 1:
            seed_info = parts[1].split("_nc_")[0]
            nc_part = parts[0].split("nc_")[1]
            # Remove trailing underscore
            if nc_part.endswith("_"):
                nc_part = nc_part[:-1]

            if nc_part not in nc_seeds:
                nc_seeds[nc_part] = set()
            nc_seeds[nc_part].add(int(seed_info))

    total_seeds = sum(len(seeds) for seeds in nc_seeds.values())
    ncs_started = set(nc_seeds.keys())

    # Convert seed sets to max seed ID (which is seeds completed - 1)
    seeds_per_nc = {nc: max(seeds) + 1 for nc, seeds in nc_seeds.items()}

    return total_seeds, ncs_started, seeds_per_nc


def report_progress():
    """Print human-readable progress report."""
    total_logs = len(list(ARTIFACT_DIR.glob("ipopt_logs/*.log"))) if ARTIFACT_DIR.exists() else 0
    total_seeds, ncs_started, seeds_per_nc = check_progress()

    print("=" * 70)
    print("PHASE 2 PROGRESS REPORT")
    print("=" * 70)
    print(f"IPOPT logs: {total_logs}")
    print(f"Unique seeds started: {total_seeds}")
    print(f"NCs started: {len(ncs_started)} / {len(ALL_NCS)}")

    if seeds_per_nc:
        # Find first incomplete NC
        for nc in ALL_NCS:
            if nc not in seeds_per_nc:
                print(f"\nFirst incomplete NC: {nc} (0 seeds)")
                break
            elif seeds_per_nc[nc] < 100:
                print(f"\nCurrent NC in progress: {nc} ({seeds_per_nc[nc]} / 100 seeds)")
                break

        print("\nDetailed progress:")
        for nc in ALL_NCS:
            if nc in seeds_per_nc:
                n = seeds_per_nc[nc]
                pct = 100 * n / 100
                bar_len = 30
                filled = int(bar_len * n / 100)
                bar = "█" * filled + "░" * (bar_len - filled)
                print(f"  {nc:15} [{bar}] {n:3}/100 ({pct:5.1f}%)")
            else:
                print(f"  {nc:15} [{'░' * 30}]   0/100 (  0.0%)")

    # Summary
    total_expected = len(ALL_NCS) * 100
    pct_complete = 100 * total_seeds / total_expected
    print(f"\nTotal progress: {total_seeds} / {total_expected} seeds ({pct_complete:.1f}%)")


def aggregate_results():
    """
    Aggregate results from all completed optimizations into a summary JSON.

    This processes the raw IPOPT logs and run_stage outputs to extract
    productivity scores and metrics.
    """
    print("⚠️  Aggregation not yet implemented")
    print("Will implement after job completes or needs continuation")


def prepare_continuation_job(remaining_ncs: List[str]) -> str:
    """
    Create a SLURM job script that continues Phase 2 for remaining NCs.

    Returns: path to generated SLURM script
    """
    print(f"⚠️  Continuation not yet implemented")
    print(f"Will implement if job runs out of walltime")
    return ""


def main():
    parser = argparse.ArgumentParser(description="Phase 2 Recovery and Aggregation")
    parser.add_argument(
        "--check-progress",
        action="store_true",
        help="Check job progress"
    )
    parser.add_argument(
        "--aggregate-results",
        action="store_true",
        help="Aggregate completed results into summary JSON"
    )
    parser.add_argument(
        "--prepare-continuation",
        action="store_true",
        help="Prepare a continuation job for incomplete NCs"
    )

    args = parser.parse_args()

    if args.check_progress:
        report_progress()
    elif args.aggregate_results:
        aggregate_results()
    elif args.prepare_continuation:
        _, ncs_started, seeds_per_nc = check_progress()
        remaining = [nc for nc in ALL_NCS if nc not in ncs_started or seeds_per_nc.get(nc, 0) < 100]
        if remaining:
            print(f"Remaining NCs to process: {len(remaining)}")
            for nc in remaining[:3]:
                print(f"  - {nc}")
            if len(remaining) > 3:
                print(f"  ... and {len(remaining) - 3} more")
            prepare_continuation_job(remaining)
        else:
            print("✅ All NCs have been started!")
    else:
        # Default: show progress
        report_progress()

    return 0


if __name__ == "__main__":
    sys.exit(main())
