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


def _extract_artifact_path(stdout: str, stderr: str) -> str | None:
    for stream in (stdout, stderr):
        for line in stream.splitlines():
            line = line.strip()
            if not line:
                continue
            if '"artifact"' in line:
                try:
                    return json.loads(line).get("artifact")
                except Exception:
                    continue
    return None


def _artifact_to_result(artifact: Dict, nc: List[int], run_name: str, start_index: int, artifact_path: str, returncode: int) -> Dict:
    solver = artifact.get("solver", {}) if isinstance(artifact, dict) else {}
    metrics = artifact.get("metrics", {}) if isinstance(artifact, dict) else {}
    status = artifact.get("status", "error")
    result = {
        "status": status,
        "nc": nc,
        "run_name": run_name,
        "start_index": start_index,
        "productivity": artifact.get("J_validated"),
        "purity": metrics.get("purity_ex_meoh_free"),
        "recovery_ga": metrics.get("recovery_ex_GA"),
        "recovery_ma": metrics.get("recovery_ex_MA"),
        "artifact": artifact_path,
        "returncode": returncode,
        "solver_status": solver.get("status"),
        "termination_condition": solver.get("termination_condition"),
        "solver_message": solver.get("message") or artifact.get("error"),
    }
    return result


def run_high_fidelity_once(
    nc: List[int],
    run_name: str,
    artifact_dir: str,
    start_index: int = 0,
    nfex: int = 10,
    nfet: int = 5,
    ncp: int = 2,
    purity_min: float = 0.05,
    recovery_ga_min: float = 0.10,
    recovery_ma_min: float = 0.15,
    max_pump_flow: float = 3.0,
    timeout: int = 3600,
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
    ]

    try:
        result = subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        artifact_path = _extract_artifact_path(result.stdout, result.stderr)
        if artifact_path and Path(artifact_path).exists():
            with open(artifact_path) as f:
                artifact = json.load(f)
            return _artifact_to_result(artifact, nc, run_name, start_index, artifact_path, result.returncode)
        return {
            "status": "error",
            "nc": nc,
            "run_name": run_name,
            "start_index": start_index,
            "returncode": result.returncode,
            "stdout_tail": result.stdout[-1000:],
            "error": result.stderr[-1000:],
        }
    except subprocess.TimeoutExpired as e:
        artifact_path = _extract_artifact_path(e.stdout or "", e.stderr or "")
        return {
            "status": "timeout",
            "nc": nc,
            "run_name": run_name,
            "start_index": start_index,
            "timeout": timeout,
            "artifact": artifact_path,
            "stdout_tail": (e.stdout or "")[-1000:],
            "error": (e.stderr or "")[-1000:],
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
