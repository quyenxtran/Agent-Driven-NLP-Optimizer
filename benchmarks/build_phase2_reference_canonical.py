#!/usr/bin/env python3
"""Build a canonical Phase 2 summary from raw reference-eval artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from benchmarks.phase3_data_adapter import build_phase3_dataset
ARTIFACT_DIR = REPO_ROOT / "artifacts" / "phase2_lhs_seeding"
OUT_PATH = ARTIFACT_DIR / "phase2_reference_canonical.json"
LEGACY_COMPAT_PATH = ARTIFACT_DIR / "phase2_summary.canonical.json"


def main() -> int:
    data = build_phase3_dataset(ARTIFACT_DIR, prefer_job="6289854")
    successful_seed_total = sum(r.get("n_successful", 0) for r in data.get("results", []))
    payload = {
        **data,
        "canonicalized_from": "raw_reference_eval_seed_artifacts",
        "statistics": {
            "ncs_tested": data.get("ncs_tested"),
            "successful_ncs": data.get("successful_ncs"),
            "successful_seed_total": successful_seed_total,
            "total_seed_records": sum(r.get("n_evaluations", 0) for r in data.get("results", [])),
        },
    }
    OUT_PATH.write_text(json.dumps(payload, indent=2))
    LEGACY_COMPAT_PATH.write_text(json.dumps(payload, indent=2))
    print(f"Wrote canonical reference summary: {OUT_PATH}")
    print(f"Wrote legacy-compatible canonical summary: {LEGACY_COMPAT_PATH}")
    print(json.dumps(payload["statistics"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
