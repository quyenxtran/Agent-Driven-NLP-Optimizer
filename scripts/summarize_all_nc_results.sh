#!/usr/bin/env bash
# Summarize optimize-layouts artifacts from SMB stage runs.
#
# Usage examples:
#   bash AutoResearch-SMB/scripts/summarize_all_nc_results.sh
#   bash AutoResearch-SMB/scripts/summarize_all_nc_results.sh \
#     --artifact-dir /storage/home/hcoda1/4/qtran47/AutoResearch-SMB/artifacts/smb_stage_runs \
#     --run-filter minlp_all_nc_5h
#
# Outputs:
#   artifacts/reports/all_nc_candidates_<timestamp>.csv
#   artifacts/reports/all_nc_artifacts_<timestamp>.csv
#   artifacts/reports/all_nc_summary_<timestamp>.md

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

ARTIFACT_DIR="${REPO_ROOT}/artifacts/smb_stage_runs"
OUT_DIR="${REPO_ROOT}/artifacts/reports"
RUN_FILTER=""
GLOB_PATTERN="optimize-layouts.*.json"

usage() {
  cat <<EOF
Usage: $(basename "$0") [options]

Options:
  --artifact-dir <path>    Directory containing stage artifacts
  --out-dir <path>         Output directory for summary files
  --run-filter <text>      Keep only artifacts whose filename contains <text>
  --glob <pattern>         Filename glob pattern (default: ${GLOB_PATTERN})
  -h, --help               Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --artifact-dir)
      ARTIFACT_DIR="$2"
      shift 2
      ;;
    --out-dir)
      OUT_DIR="$2"
      shift 2
      ;;
    --run-filter)
      RUN_FILTER="$2"
      shift 2
      ;;
    --glob)
      GLOB_PATTERN="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ ! -d "${ARTIFACT_DIR}" ]]; then
  echo "Artifact directory not found: ${ARTIFACT_DIR}" >&2
  exit 1
fi

mkdir -p "${OUT_DIR}"

mapfile -t ARTIFACT_FILES < <(find "${ARTIFACT_DIR}" -maxdepth 1 -type f -name "${GLOB_PATTERN}" | sort)

if [[ -n "${RUN_FILTER}" ]]; then
  mapfile -t ARTIFACT_FILES < <(printf '%s\n' "${ARTIFACT_FILES[@]}" | grep -F "${RUN_FILTER}" || true)
fi

if [[ ${#ARTIFACT_FILES[@]} -eq 0 ]]; then
  echo "No artifacts matched in ${ARTIFACT_DIR} (glob=${GLOB_PATTERN}, run_filter=${RUN_FILTER:-<none>})."
  exit 0
fi

PYTHON_BIN="$(command -v python || true)"
if [[ -z "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="$(command -v python3 || true)"
fi
if [[ -z "${PYTHON_BIN}" ]]; then
  echo "Neither python nor python3 is available on PATH." >&2
  exit 1
fi

"${PYTHON_BIN}" - "${OUT_DIR}" "${RUN_FILTER}" "${ARTIFACT_FILES[@]}" <<'PY'
import csv
import json
import math
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

out_dir = Path(sys.argv[1])
run_filter = sys.argv[2]
artifact_paths = [Path(p) for p in sys.argv[3:]]

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
candidate_csv = out_dir / f"all_nc_candidates_{timestamp}.csv"
artifact_csv = out_dir / f"all_nc_artifacts_{timestamp}.csv"
summary_md = out_dir / f"all_nc_summary_{timestamp}.md"


def as_float(value):
    if value is None:
        return None
    try:
        f = float(value)
    except Exception:
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return f


def to_layout(nc):
    if isinstance(nc, (list, tuple)) and len(nc) == 4:
        return "-".join(str(int(x)) for x in nc)
    return ""


def pick_metrics(result):
    metrics = result.get("metrics")
    if isinstance(metrics, dict):
        return metrics, True
    provisional = result.get("provisional")
    if isinstance(provisional, dict):
        provisional_metrics = provisional.get("metrics")
        if isinstance(provisional_metrics, dict):
            return provisional_metrics, False
    return {}, None


def pick_flow(result):
    for key in ("optimized_flow", "provisional_optimized_flow", "initial_flow", "flow"):
        flow = result.get(key)
        if isinstance(flow, dict):
            return flow
    return {}


def sort_key(row):
    feasible = 1 if row.get("feasible") else 0
    j = row.get("J_validated")
    score = j if isinstance(j, float) else float("-inf")
    viol = row.get("normalized_total_violation")
    viol_score = -viol if isinstance(viol, float) else float("-inf")
    return (feasible, score, viol_score)


candidate_rows = []
artifact_rows = []

for path in artifact_paths:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        artifact_rows.append(
            {
                "artifact_file": str(path),
                "stage": "",
                "run_name": "",
                "status": "error",
                "error": f"json_load_failed: {exc}",
                "num_results": 0,
                "num_feasible": 0,
                "num_solver_error": 0,
                "num_error": 0,
                "best_feasible": "",
                "best_j_validated": "",
                "best_total_violation": "",
            }
        )
        continue

    stage = payload.get("stage", "")
    run_name = ""
    m = re.match(r"^[^.]+\.[^.]+\.(.+)\.json$", path.name)
    if m:
        run_name = m.group(1)

    results = payload.get("results")
    if not isinstance(results, list):
        results = []

    status_counts = Counter()
    feasible_count = 0
    best_row_for_artifact = None

    for idx, result in enumerate(results, start=1):
        if not isinstance(result, dict):
            continue

        status = str(result.get("status", ""))
        status_counts[status] += 1

        metrics, validated = pick_metrics(result)
        flow = pick_flow(result)
        slacks = result.get("constraint_slacks")
        if not isinstance(slacks, dict):
            slacks = {}

        feasible = bool(result.get("feasible", False))
        if feasible:
            feasible_count += 1

        row = {
            "artifact_file": str(path),
            "stage": stage,
            "run_name": run_name,
            "candidate_idx": idx,
            "candidate_run_name": result.get("run_name", ""),
            "layout": to_layout(result.get("nc")),
            "seed_name": result.get("seed_name", ""),
            "status": status,
            "solver_name": (result.get("solver") or {}).get("solver_name", "") if isinstance(result.get("solver"), dict) else "",
            "linear_solver": ((result.get("solver") or {}).get("solver_options", {}) or {}).get("linear_solver", "") if isinstance(result.get("solver"), dict) else "",
            "termination_condition": (result.get("solver") or {}).get("termination_condition", "") if isinstance(result.get("solver"), dict) else "",
            "solver_message": (result.get("solver") or {}).get("message", "") if isinstance(result.get("solver"), dict) else "",
            "feasible": feasible,
            "J_validated": as_float(result.get("J_validated")),
            "normalized_total_violation": as_float(slacks.get("normalized_total_violation")),
            "productivity_ex_ga_ma": as_float(metrics.get("productivity_ex_ga_ma")),
            "purity_ex_meoh_free": as_float(metrics.get("purity_ex_meoh_free")),
            "recovery_ex_GA": as_float(metrics.get("recovery_ex_GA")),
            "recovery_ex_MA": as_float(metrics.get("recovery_ex_MA")),
            "metrics_validated": validated,
            "Ffeed": as_float(flow.get("Ffeed")),
            "F1": as_float(flow.get("F1")),
            "Fdes": as_float(flow.get("Fdes")),
            "Fex": as_float(flow.get("Fex")),
            "Fraf": as_float(flow.get("Fraf")),
            "tstep": as_float(flow.get("tstep")),
            "cpu_hours_accounted": as_float(((result.get("timing") or {}).get("cpu_hours_accounted")) if isinstance(result.get("timing"), dict) else None),
            "wall_seconds": as_float(((result.get("timing") or {}).get("wall_seconds")) if isinstance(result.get("timing"), dict) else None),
            "error": result.get("error", ""),
        }
        candidate_rows.append(row)

        if best_row_for_artifact is None or sort_key(row) > sort_key(best_row_for_artifact):
            best_row_for_artifact = row

    artifact_rows.append(
        {
            "artifact_file": str(path),
            "stage": stage,
            "run_name": run_name,
            "status": payload.get("status", ""),
            "error": payload.get("error", ""),
            "num_results": len(results),
            "num_feasible": feasible_count,
            "num_solver_error": status_counts.get("solver_error", 0),
            "num_error": status_counts.get("error", 0),
            "best_feasible": best_row_for_artifact.get("feasible", False) if best_row_for_artifact else "",
            "best_j_validated": best_row_for_artifact.get("J_validated", "") if best_row_for_artifact else "",
            "best_total_violation": best_row_for_artifact.get("normalized_total_violation", "") if best_row_for_artifact else "",
            "best_productivity": best_row_for_artifact.get("productivity_ex_ga_ma", "") if best_row_for_artifact else "",
            "best_layout": best_row_for_artifact.get("layout", "") if best_row_for_artifact else "",
            "best_seed_name": best_row_for_artifact.get("seed_name", "") if best_row_for_artifact else "",
        }
    )


candidate_fields = [
    "artifact_file",
    "stage",
    "run_name",
    "candidate_idx",
    "candidate_run_name",
    "layout",
    "seed_name",
    "status",
    "solver_name",
    "linear_solver",
    "termination_condition",
    "solver_message",
    "feasible",
    "J_validated",
    "normalized_total_violation",
    "productivity_ex_ga_ma",
    "purity_ex_meoh_free",
    "recovery_ex_GA",
    "recovery_ex_MA",
    "metrics_validated",
    "Ffeed",
    "F1",
    "Fdes",
    "Fex",
    "Fraf",
    "tstep",
    "cpu_hours_accounted",
    "wall_seconds",
    "error",
]

artifact_fields = [
    "artifact_file",
    "stage",
    "run_name",
    "status",
    "error",
    "num_results",
    "num_feasible",
    "num_solver_error",
    "num_error",
    "best_feasible",
    "best_j_validated",
    "best_total_violation",
    "best_productivity",
    "best_layout",
    "best_seed_name",
]

candidate_rows_sorted = sorted(candidate_rows, key=sort_key, reverse=True)
artifact_rows_sorted = sorted(artifact_rows, key=lambda r: (r.get("num_feasible", 0), as_float(r.get("best_j_validated")) or float("-inf")), reverse=True)

with candidate_csv.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=candidate_fields)
    writer.writeheader()
    writer.writerows(candidate_rows_sorted)

with artifact_csv.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=artifact_fields)
    writer.writeheader()
    writer.writerows(artifact_rows_sorted)

top_candidates = candidate_rows_sorted[:10]
feasible_count_total = sum(1 for r in candidate_rows if r.get("feasible"))

with summary_md.open("w", encoding="utf-8") as f:
    f.write("# SMB all-nc Summary\n\n")
    f.write(f"- generated_at: {datetime.now().isoformat(timespec='seconds')}\n")
    f.write(f"- artifact_count: {len(artifact_rows)}\n")
    f.write(f"- candidate_count: {len(candidate_rows)}\n")
    f.write(f"- feasible_candidate_count: {feasible_count_total}\n")
    f.write(f"- run_filter: {run_filter if run_filter else '<none>'}\n")
    f.write("\n## Top 10 candidates (ranked)\n\n")
    for idx, r in enumerate(top_candidates, start=1):
        f.write(
            f"{idx}. run={r.get('run_name')} candidate={r.get('candidate_run_name')} "
            f"layout={r.get('layout')} seed={r.get('seed_name')} "
            f"feasible={r.get('feasible')} J={r.get('J_validated')} "
            f"viol={r.get('normalized_total_violation')} prod={r.get('productivity_ex_ga_ma')}\n"
        )
    f.write("\n## Files\n\n")
    f.write(f"- candidate_csv: {candidate_csv}\n")
    f.write(f"- artifact_csv: {artifact_csv}\n")
    f.write(f"- summary_md: {summary_md}\n")

print(f"Wrote candidate CSV: {candidate_csv}")
print(f"Wrote artifact CSV: {artifact_csv}")
print(f"Wrote summary MD: {summary_md}")
print(f"Artifacts: {len(artifact_rows)} | Candidates: {len(candidate_rows)} | Feasible candidates: {feasible_count_total}")
PY
