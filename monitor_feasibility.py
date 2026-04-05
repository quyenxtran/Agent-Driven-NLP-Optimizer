#!/usr/bin/env python3
"""
Real-time Phase 2 Feasibility Monitor

Tracks:
  - Completed (NC, seed) pairs
  - Feasible vs infeasible results
  - Success rate by NC
  - Overall statistics
  - Live progress with ETA
"""

import json
import sys
import subprocess
from pathlib import Path
from collections import defaultdict
from datetime import datetime
import time

ARTIFACT_DIR = Path("artifacts/phase2_lhs_seeding")
IPOPT_LOGS_DIR = ARTIFACT_DIR / "ipopt_logs"
CHECKPOINT_FILE = ARTIFACT_DIR / "phase2_checkpoint_stochastic.json"

def count_ipopt_logs():
    """Count total IPOPT logs (indicator of progress)"""
    if not IPOPT_LOGS_DIR.exists():
        return 0
    return len(list(IPOPT_LOGS_DIR.glob("*.log")))

def load_checkpoint():
    """Load checkpoint with completed pairs"""
    if not CHECKPOINT_FILE.exists():
        return {"completed_pairs": []}
    with open(CHECKPOINT_FILE) as f:
        return json.load(f)

def parse_ipopt_logs():
    """Analyze IPOPT logs for feasibility"""
    if not IPOPT_LOGS_DIR.exists():
        return {}, {}, {}

    feasibility_by_nc = defaultdict(lambda: {"feasible": 0, "infeasible": 0, "error": 0})
    seed_results = defaultdict(list)

    logs = list(IPOPT_LOGS_DIR.glob("*.log"))

    for log_file in logs:
        # Extract NC and seed from filename
        # Format: ipopt_phase2_stoch_nc_[1,1,2,4]_seed_42_...log
        name = log_file.stem

        # Simple extraction
        if "seed_" not in name:
            continue

        parts = name.split("seed_")
        if len(parts) < 2:
            continue

        seed_str = parts[1].split("_")[0]
        try:
            seed_idx = int(seed_str)
        except ValueError:
            continue

        # Extract NC
        nc_part = parts[0].split("nc_")
        if len(nc_part) < 2:
            continue
        nc_str = nc_part[1].rstrip("_")

        # Check feasibility
        with open(log_file) as f:
            content = f.read()

        if "Optimal Solution Found" in content:
            feasibility_by_nc[nc_str]["feasible"] += 1
            seed_results[nc_str].append(("feasible", seed_idx))
        elif "Converged to a point of local infeasibility" in content:
            feasibility_by_nc[nc_str]["infeasible"] += 1
            seed_results[nc_str].append(("infeasible", seed_idx))
        else:
            feasibility_by_nc[nc_str]["error"] += 1

    return feasibility_by_nc, seed_results, logs

def get_job_status(job_id="6284727"):
    """Get SLURM job status"""
    try:
        result = subprocess.run(
            ["squeue", "-j", job_id, "--format=%T,%i,%C,%M"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            if len(lines) >= 2:
                parts = lines[1].split(",")
                if len(parts) >= 4:
                    state = parts[0]
                    cpus = parts[2]
                    elapsed = parts[3]
                    return {"state": state, "cpus": cpus, "elapsed": elapsed}
    except:
        pass
    return None

def print_status(job_id="6284727"):
    """Print formatted status"""
    print("\n" + "=" * 80)
    print(f"PHASE 2 FEASIBILITY MONITOR - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # Job status
    job_status = get_job_status(job_id)
    if job_status:
        print(f"\n📋 Job Status:")
        print(f"  Job ID: {job_id}")
        print(f"  State: {job_status['state']}")
        print(f"  CPUs: {job_status['cpus']}")
        print(f"  Elapsed: {job_status['elapsed']}")

    # IPOPT logs
    total_logs = count_ipopt_logs()
    print(f"\n📊 IPOPT Logs:")
    print(f"  Total logs: {total_logs}")

    # Checkpoint
    checkpoint = load_checkpoint()
    completed_pairs = checkpoint.get("completed_pairs", [])
    print(f"  Completed (NC, seed) pairs: {len(completed_pairs)}")

    # Feasibility analysis
    feasibility_by_nc, seed_results, logs = parse_ipopt_logs()

    if feasibility_by_nc:
        print(f"\n✅ Feasibility Analysis ({len(logs)} IPOPT logs analyzed):")
        print(f"  {'NC':<20} {'Feasible':<10} {'Infeasible':<12} {'Error':<8} {'Rate':<8}")
        print(f"  {'-' * 20} {'-' * 10} {'-' * 12} {'-' * 8} {'-' * 8}")

        total_feasible = 0
        total_infeasible = 0

        for nc in sorted(feasibility_by_nc.keys()):
            stats = feasibility_by_nc[nc]
            feas = stats["feasible"]
            infeas = stats["infeasible"]
            errs = stats["error"]
            total = feas + infeas + errs

            if total > 0:
                rate = 100 * feas / total
                total_feasible += feas
                total_infeasible += infeas

                bar_len = 20
                filled = int(bar_len * feas / total)
                bar = "█" * filled + "░" * (bar_len - filled)

                print(f"  {nc:<20} {feas:<10} {infeas:<12} {errs:<8} {rate:>6.1f}%")

        # Overall stats
        total_all = total_feasible + total_infeasible
        if total_all > 0:
            overall_rate = 100 * total_feasible / total_all
            print(f"  {'-' * 20} {'-' * 10} {'-' * 12} {'-' * 8} {'-' * 8}")
            print(f"  {'TOTAL':<20} {total_feasible:<10} {total_infeasible:<12} {'':<8} {overall_rate:>6.1f}%")
    else:
        print(f"\n⏳ Waiting for IPOPT logs... (job may still be initializing)")

    # Progress estimate
    if total_logs > 0:
        print(f"\n📈 Progress Estimate:")
        logs_per_minute = total_logs / (max(int(job_status["elapsed"].split(":")[0]) * 60 + int(job_status["elapsed"].split(":")[1]), 1) if job_status else 1)
        estimated_total_logs = 3200 * 30  # Rough estimate: 30 logs per seed
        if logs_per_minute > 0:
            remaining_minutes = (estimated_total_logs - total_logs) / logs_per_minute
            print(f"  IPOPT logs/minute: {logs_per_minute:.1f}")
            print(f"  Estimated total logs: {estimated_total_logs:,}")
            print(f"  Est. remaining time: {remaining_minutes:.0f} minutes (~{remaining_minutes/60:.1f} hours)")

    print("\n" + "=" * 80 + "\n")

def watch_mode(interval=10):
    """Continuous monitoring mode"""
    print(f"Starting continuous monitoring (updating every {interval} seconds)...")
    print("Press Ctrl+C to stop\n")

    try:
        while True:
            print("\033[2J\033[H")  # Clear screen
            print_status()
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n✅ Monitoring stopped")

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Phase 2 Feasibility Monitor")
    parser.add_argument("--job-id", default="6284727", help="SLURM job ID")
    parser.add_argument("--watch", action="store_true", help="Continuous monitoring mode")
    parser.add_argument("--interval", type=int, default=10, help="Update interval (seconds)")

    args = parser.parse_args()

    if args.watch:
        watch_mode(args.interval)
    else:
        print_status(args.job_id)

if __name__ == "__main__":
    main()
