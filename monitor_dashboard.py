#!/usr/bin/env python3
"""
Phase 2 Feasibility Dashboard

Shows:
  - Real-time progress with ETA
  - Per-NC feasibility breakdown
  - Success vs failure rates
  - Throughput metrics
  - Job status integration
"""

import json
import subprocess
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timedelta
import time
import re

ARTIFACT_DIR = Path("artifacts/phase2_lhs_seeding")
IPOPT_DIR = ARTIFACT_DIR / "ipopt_logs"
JOB_ID = "6284727"

def get_elapsed_minutes():
    """Get job elapsed time in minutes"""
    try:
        result = subprocess.run(
            ["squeue", "-j", JOB_ID, "--format=%M", "-h"],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            time_str = result.stdout.strip()
            parts = time_str.split(":")
            if len(parts) == 3:  # HH:MM:SS
                hours, mins, secs = map(int, parts)
                return hours * 60 + mins + secs / 60
            elif len(parts) == 2:  # MM:SS
                mins, secs = map(int, parts)
                return mins + secs / 60
    except:
        pass
    return 0

def analyze_feasibility():
    """Analyze IPOPT logs for feasibility by NC and seed"""
    if not IPOPT_DIR.exists():
        return defaultdict(lambda: {"feasible": 0, "infeasible": 0, "error": 0}), 0, 0

    feasibility = defaultdict(lambda: {"feasible": 0, "infeasible": 0, "error": 0})
    total_feasible = 0
    total_infeasible = 0

    logs = list(IPOPT_DIR.glob("*.log"))

    for log_file in logs:
        name = log_file.stem

        # Extract NC: "ipopt_phase2_stoch_nc_[1,1,2,4]_seed_..."
        nc_match = re.search(r"nc_(\[[\d,]+\])", name)
        if not nc_match:
            continue
        nc = nc_match.group(1)

        # Check log content
        with open(log_file) as f:
            content = f.read()

        if "Optimal Solution Found" in content:
            feasibility[nc]["feasible"] += 1
            total_feasible += 1
        elif "Converged to a point of local infeasibility" in content:
            feasibility[nc]["infeasible"] += 1
            total_infeasible += 1
        else:
            feasibility[nc]["error"] += 1

    return feasibility, total_feasible, total_infeasible

def print_dashboard():
    """Print formatted dashboard"""
    elapsed = get_elapsed_minutes()
    feasibility, total_feasible, total_infeasible = analyze_feasibility()

    print("\n" + "╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "PHASE 2 FEASIBILITY DASHBOARD" + " " * 30 + "║")
    print("╚" + "═" * 78 + "╝")

    # Header with timestamp
    print(f"\n⏱️  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Elapsed: {elapsed:.1f} min | Job: {JOB_ID}")

    # Progress metrics
    total_logs = len(list(IPOPT_DIR.glob("*.log"))) if IPOPT_DIR.exists() else 0
    total_all = total_feasible + total_infeasible

    print(f"\n📊 Overall Statistics:")
    print(f"   IPOPT Logs: {total_logs:,} (indicates ~{total_logs//30:.0f} seeds in progress)")
    print(f"   Feasible: {total_feasible:,} | Infeasible: {total_infeasible:,}")

    if total_all > 0:
        feasibility_rate = 100 * total_feasible / total_all
        print(f"   Success Rate: {feasibility_rate:.1f}% ({total_feasible}/{total_all})")

        # Progress bar
        bar_len = 40
        filled = int(bar_len * feasibility_rate / 100)
        bar = "▓" * filled + "░" * (bar_len - filled)
        print(f"   [{bar}] {feasibility_rate:.1f}%")
    else:
        print(f"   Still initializing... (waiting for logs)")

    # Per-NC breakdown
    if feasibility:
        print(f"\n🔍 Per-NC Feasibility Breakdown:")
        print(f"   {'NC':<15} {'Feasible':<10} {'Infeasible':<12} {'Success %':<12}")
        print(f"   {'-' * 15} {'-' * 10} {'-' * 12} {'-' * 12}")

        sorted_ncs = sorted(feasibility.keys(), key=lambda x: int(x.split(",")[0].strip("[]")))

        for nc in sorted_ncs[:10]:  # Show first 10
            stats = feasibility[nc]
            f = stats["feasible"]
            inf = stats["infeasible"]
            total = f + inf + stats["error"]

            if total > 0:
                rate = 100 * f / total
                print(f"   {nc:<15} {f:<10} {inf:<12} {rate:>10.1f}%")

        if len(feasibility) > 10:
            print(f"   ... and {len(feasibility) - 10} more NCs ...")

    # Throughput estimation
    if elapsed > 0 and total_logs > 0:
        logs_per_minute = total_logs / elapsed
        estimated_total_logs = 3200 * 30  # Each seed ~30 logs
        remaining_logs = estimated_total_logs - total_logs
        eta_minutes = remaining_logs / logs_per_minute

        print(f"\n⚡ Performance Metrics:")
        print(f"   Throughput: {logs_per_minute:.1f} logs/min")
        print(f"   Est. completion: {eta_minutes:.0f} min ({eta_minutes/60:.1f} hours)")
        print(f"   Est. finish time: {(datetime.now() + timedelta(minutes=eta_minutes)).strftime('%H:%M:%S')}")

    print(f"\n💡 Tips:")
    print(f"   • Watch live: python monitor_feasibility.py --watch")
    print(f"   • Quick check: bash show_feasibility.sh")
    print(f"   • Check logs: tail -50 logs/smb-phase2-stoch-32cpu-*.out")
    print(f"   • View job: squeue -j {JOB_ID} -l\n")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--watch":
        interval = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        try:
            while True:
                print("\033[2J\033[H")  # Clear screen
                print_dashboard()
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n✅ Monitoring stopped")
    else:
        print_dashboard()
