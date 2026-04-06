#!/usr/bin/env python3
"""Utilities for Phase 3 finalist multi-start validation."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from statistics import mean, pstdev
from typing import Dict, List

REPO_ROOT = Path(__file__).parent.parent


def run_high_fidelity_once(
    nc: List[int],
    run_name: str,
    artifact_dir: str,
    start_index: int = 0,
    nfex: int = 10,
    nfet: int = 5,
    ncp: int = 2,
    purity_min: float = 0.20,
    recovery_ga_min: float = 0.20,
    recovery_ma_min: float = 0.20,
    max_pump_flow: float = 3.0,
    timeout: int = 900,
) -> Dict:
    nc_str = f"[{nc[0]},{nc[1]},{nc[2]},{nc[3]}]"

    cmd = [
        sys.executable,
        "-m",
        "benchmarks.run_stage",
        "--stage",
        "optimize-layouts",
        "--run-name",
        run_name,
        "--artifact-dir",
        artifact_dir,
        "--nc",
        nc_str,
        "--solver-name",
        "auto",
        "--linear-solver",
        "ma97",
        "--nfex",
        str(nfex),
        "--nfet",
        str(nfet),
        "--ncp",
        str(ncp),
        "--purity-min",
        str(purity_min),
        "--recovery-ga-min",
        str(recovery_ga_min),
        "--recovery-ma-min",
        str(recovery_ma_min),
        "--max-pump-flow",
        str(max_pump_flow),
        "--random-starts",
        "1",
        "--random-start-index",
        str(start_index),
    ]

    try:
        result = subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode == 0:
            for line in result.stdout.split("\n"):
                if '"artifact"' in line:
                    artifact_path = json.loads(line).get("artifact")
                    if artifact_path and Path(artifact_path).exists():
                        with open(artifact_path) as f:
                            artifact = json.load(f)
                        return {
                            "status": "ok",
                            "nc": nc,
                            "run_name": run_name,
                            "start_index": start_index,
                            "productivity": artifact.get("J_validated"),
                            "purity": artifact.get("metrics", {}).get("purity_ex_meoh_free"),
                            "recovery_ga": artifact.get("metrics", {}).get("recovery_ex_GA"),
                            "recovery_ma": artifact.get("metrics", {}).get("recovery_ex_MA"),
                            "artifact": artifact_path,
                        }
        return {
            "status": "error",
            "nc": nc,
            "run_name": run_name,
            "start_index": start_index,
            "error": result.stderr[:300],
        }
    except subprocess.TimeoutExpired:
        return {
            "status": "timeout",
            "nc": nc,
            "run_name": run_name,
            "start_index": start_index,
        }
    except Exception as e:
        return {
            "status": "exception",
            "nc": nc,
            "run_name": run_name,
            "start_index": start_index,
            "error": str(e),
        }


def summarize_multistart(results: List[Dict]) -> Dict:
    ok = [r for r in results if r.get("status") == "ok" and r.get("productivity") is not None]
    vals = [float(r["productivity"]) for r in ok]
    if not vals:
        return {
            "n_runs": len(results),
            "n_successful": 0,
            "best_productivity": None,
            "mean_productivity": None,
            "std_productivity": None,
        }
    return {
        "n_runs": len(results),
        "n_successful": len(ok),
        "best_productivity": max(vals),
        "mean_productivity": mean(vals),
        "std_productivity": pstdev(vals) if len(vals) > 1 else 0.0,
    }
