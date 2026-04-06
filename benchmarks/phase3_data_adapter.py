#!/usr/bin/env python3
"""
Phase 3 data adapter for current Phase 2 reference-evaluation outputs.

This module reconstructs a Phase-3-friendly dataset from raw reference-eval
seed artifacts when the old `phase2_summary.json` schema is missing, stale,
or structurally incompatible.
"""

from __future__ import annotations

import glob
import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

REPO_ROOT = Path(__file__).parent.parent
ARTIFACT_DIR = REPO_ROOT / "artifacts" / "phase2_lhs_seeding"


def _safe_metric(payload: Dict, *keys, default=0.0):
    cur = payload
    for key in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(key)
    return default if cur is None else cur


def _extract_metrics(payload: Dict) -> Dict:
    metrics = payload.get("metrics", {}) or {}
    outlets = payload.get("outlets", {}) or {}

    productivity = (
        metrics.get("productivity_ex_ga_ma")
        or metrics.get("productivity")
        or _safe_metric(outlets, "productivity_ex_ga_ma", default=0.0)
        or 0.0
    )
    purity = (
        metrics.get("purity_ex_meoh_free")
        or metrics.get("purity")
        or _safe_metric(outlets, "purity_ex_meoh_free", default=0.0)
        or 0.0
    )
    recovery_ga = (
        metrics.get("recovery_ex_GA")
        or metrics.get("recovery_ga")
        or _safe_metric(outlets, "recovery_ex_GA", default=0.0)
        or 0.0
    )
    recovery_ma = (
        metrics.get("recovery_ex_MA")
        or metrics.get("recovery_ma")
        or _safe_metric(outlets, "recovery_ex_MA", default=0.0)
        or 0.0
    )

    return {
        "productivity_ex_ga_ma": productivity,
        "purity_ex_meoh_free": purity,
        "recovery_ex_GA": recovery_ga,
        "recovery_ex_MA": recovery_ma,
    }


def build_phase3_dataset(artifact_dir: Path | None = None, prefer_job: str | None = None) -> Dict:
    artifact_dir = artifact_dir or ARTIFACT_DIR
    pattern = str(artifact_dir / "reference-eval.*.phase2_ref_nc_*.json")
    files = sorted(glob.glob(pattern))

    if prefer_job:
        files = [f for f in files if f"reference-eval.{prefer_job}." in Path(f).name]

    grouped: Dict[Tuple[int, ...], List[Dict]] = defaultdict(list)

    for path in files:
        try:
            payload = json.loads(Path(path).read_text())
        except Exception:
            continue

        nc = tuple(payload.get("nc", []))
        if not nc:
            continue

        seed_idx = payload.get("seed_idx")
        if seed_idx is None:
            name = Path(path).stem
            if "_seed_" in name:
                try:
                    seed_idx = int(name.rsplit("_seed_", 1)[1])
                except Exception:
                    seed_idx = None

        seed_record = {
            "seed_idx": seed_idx,
            "status": payload.get("status", "unknown"),
            "metrics": _extract_metrics(payload),
            "source_file": str(Path(path).relative_to(REPO_ROOT)),
        }
        grouped[nc].append(seed_record)

    results = []
    for nc, seed_records in sorted(grouped.items()):
        seed_records = sorted(seed_records, key=lambda x: (x.get("seed_idx") is None, x.get("seed_idx", 10**9)))
        ok_records = [r for r in seed_records if r.get("status") == "ok" and r.get("metrics", {}).get("productivity_ex_ga_ma", 0) > 0]

        best_seed_idx = None
        best_productivity = None
        if ok_records:
            best = max(ok_records, key=lambda r: r["metrics"].get("productivity_ex_ga_ma", 0))
            best_seed_idx = best.get("seed_idx")
            best_productivity = best["metrics"].get("productivity_ex_ga_ma")

        results.append(
            {
                "nc": list(nc),
                "n_seeds": len(seed_records),
                "best_seed_idx": best_seed_idx,
                "productivity": best_productivity,
                "best_productivity": best_productivity,
                "n_feasible": len(ok_records),
                "n_successful": len(ok_records),
                "n_evaluations": len(seed_records),
                "all_seed_results": seed_records,
            }
        )

    successful_ncs = sum(1 for r in results if r.get("n_feasible", 0) > 0)
    return {
        "status": "ok",
        "stage": "phase2_reference_eval_adapted",
        "source": "raw_reference_eval_seed_artifacts",
        "ncs_tested": len(results),
        "successful_ncs": successful_ncs,
        "results": results,
    }


def load_phase3_ready_data() -> Dict:
    """Return a normalized Phase 3 dataset.

    Preference order:
    1. Adapt from raw reference-eval artifacts if present
    2. Fall back to legacy phase2_summary.json
    """
    raw_pattern = list(ARTIFACT_DIR.glob("reference-eval.*.phase2_ref_nc_*.json"))
    if raw_pattern:
        return build_phase3_dataset()

    legacy = ARTIFACT_DIR / "phase2_summary.json"
    if legacy.exists():
        with open(legacy) as f:
            return json.load(f)

    raise FileNotFoundError("No Phase 2 data source found for Phase 3")
