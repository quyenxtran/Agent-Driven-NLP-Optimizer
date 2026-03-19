#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


REPO_ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Benchmark LLM context growth over time from agent conversation logs "
            "(full or compact mode)."
        )
    )
    parser.add_argument(
        "--input-paths",
        nargs="+",
        default=[str(REPO_ROOT / "artifacts")],
        help="Files or directories containing agent-runner.*.conversations.jsonl logs.",
    )
    parser.add_argument(
        "--glob",
        default="agent-runner.*.conversations.jsonl",
        help="Glob pattern used when scanning input directories.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(REPO_ROOT / "artifacts" / "analysis" / "context_growth"),
    )
    parser.add_argument(
        "--chars-per-token",
        type=float,
        default=4.0,
        help="Heuristic conversion used for token estimates (default: 4 chars/token).",
    )
    parser.add_argument(
        "--algo-regex",
        default=r"^(.*?)(?:_\d{8}_\d{6})$",
        help=(
            "Regex used to normalize run_name into algorithm label. "
            "Group 1 is used as label when matched."
        ),
    )
    parser.add_argument(
        "--limit-files",
        type=int,
        default=0,
        help="Optional cap on number of files processed (0 = no cap).",
    )
    return parser.parse_args()


def iter_jsonl_files(paths: Iterable[str], pattern: str) -> Iterable[Path]:
    for raw in paths:
        path = Path(raw)
        if not path.exists():
            continue
        if path.is_file() and path.name.endswith(".jsonl"):
            yield path
            continue
        if path.is_dir():
            for item in sorted(path.rglob(pattern)):
                yield item


def parse_log_name(path: Path) -> Tuple[str, str]:
    # agent-runner.<job>.<run_name>.conversations.jsonl
    m = re.match(r"^agent-runner\.([^.]+)\.(.+)\.conversations\.jsonl$", path.name)
    if not m:
        return "unknown", path.stem
    return m.group(1), m.group(2)


def infer_algo_label(run_name: str, algo_re: re.Pattern[str]) -> str:
    m = algo_re.match(run_name)
    if m and m.groups():
        label = (m.group(1) or "").strip()
        if label:
            return label
    return run_name


def estimate_tokens(char_count: int, chars_per_token: float) -> float:
    cpt = chars_per_token if chars_per_token > 0 else 4.0
    return float(char_count) / cpt


def percentile(values: List[float], p: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return float(values[0])
    vals = sorted(float(v) for v in values)
    idx = (len(vals) - 1) * p
    lo = int(idx)
    hi = min(lo + 1, len(vals) - 1)
    frac = idx - lo
    return vals[lo] * (1.0 - frac) + vals[hi] * frac


def extract_prompt_chars(record: Dict[str, Any]) -> int:
    stats = record.get("prompt_stats")
    if isinstance(stats, dict):
        system_chars = int(stats.get("system_chars", 0) or 0)
        user_chars = int(stats.get("user_chars", 0) or 0)
        return max(0, system_chars + user_chars)

    messages = record.get("messages")
    total = 0
    if isinstance(messages, list):
        for msg in messages:
            if isinstance(msg, dict):
                total += len(str(msg.get("content", "")))
    return max(0, total)


def extract_assistant_chars(record: Dict[str, Any]) -> int:
    if "assistant_response_chars" in record:
        return int(record.get("assistant_response_chars", 0) or 0)
    if "assistant_response" in record:
        return len(str(record.get("assistant_response", "")))
    if "assistant_response_preview" in record:
        return len(str(record.get("assistant_response_preview", "")))
    return 0


def parse_attempt_status(record: Dict[str, Any]) -> Tuple[bool, str]:
    attempts = record.get("attempts")
    if isinstance(attempts, list) and attempts:
        any_success = any(bool(a.get("success")) for a in attempts if isinstance(a, dict))
        last_error = ""
        for a in reversed(attempts):
            if isinstance(a, dict):
                last_error = str(a.get("error", "") or "")
                break
        return any_success, last_error
    if "assistant_response" in record or "assistant_response_preview" in record:
        return True, ""
    return False, ""


def read_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            text = line.strip()
            if not text:
                continue
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                yield payload


def build_call_rows(path: Path, algo_re: re.Pattern[str], chars_per_token: float) -> List[Dict[str, Any]]:
    job_id, run_name = parse_log_name(path)
    algo = infer_algo_label(run_name, algo_re)

    rows: List[Dict[str, Any]] = []
    cumulative_prompt = 0
    cumulative_total = 0
    call_idx = 0

    for rec in read_jsonl(path):
        call_idx += 1
        role = str(rec.get("role", "unknown"))
        backend = str(rec.get("final_backend", "none"))
        prompt_chars = extract_prompt_chars(rec)
        assistant_chars = extract_assistant_chars(rec)
        success, last_error = parse_attempt_status(rec)
        prompt_tokens = estimate_tokens(prompt_chars, chars_per_token)
        assistant_tokens = estimate_tokens(assistant_chars, chars_per_token)
        total_tokens = prompt_tokens + assistant_tokens

        cumulative_prompt += prompt_chars
        cumulative_total += prompt_chars + assistant_chars

        meta = rec.get("metadata")
        iteration = None
        if isinstance(meta, dict) and "iteration" in meta:
            try:
                iteration = int(meta.get("iteration"))
            except Exception:
                iteration = None

        rows.append(
            {
                "job_id": job_id,
                "run_name": run_name,
                "algo_label": algo,
                "file": str(path),
                "call_index": call_idx,
                "call_id": rec.get("call_id", call_idx),
                "timestamp_utc": rec.get("timestamp_utc"),
                "role": role,
                "iteration": iteration,
                "backend": backend,
                "success": success,
                "error": last_error,
                "prompt_chars": prompt_chars,
                "assistant_chars": assistant_chars,
                "prompt_tokens_est": round(prompt_tokens, 3),
                "assistant_tokens_est": round(assistant_tokens, 3),
                "total_tokens_est": round(total_tokens, 3),
                "cum_prompt_chars": cumulative_prompt,
                "cum_total_chars": cumulative_total,
                "cum_prompt_tokens_est": round(estimate_tokens(cumulative_prompt, chars_per_token), 3),
                "cum_total_tokens_est": round(estimate_tokens(cumulative_total, chars_per_token), 3),
            }
        )

    return rows


def summarize_run(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not rows:
        return {}
    prompt_tokens = [float(r["prompt_tokens_est"]) for r in rows]
    total_tokens = [float(r["total_tokens_est"]) for r in rows]
    successes = [r for r in rows if bool(r.get("success"))]
    timeout_calls = [r for r in rows if "timeout" in str(r.get("error", "")).lower()]
    by_role: Dict[str, int] = {}
    for r in rows:
        by_role[str(r["role"])] = by_role.get(str(r["role"]), 0) + 1

    first = rows[0]
    last = rows[-1]
    growth = float(last["prompt_tokens_est"]) - float(first["prompt_tokens_est"])
    growth_pct = (growth / float(first["prompt_tokens_est"]) * 100.0) if float(first["prompt_tokens_est"]) > 0 else 0.0

    return {
        "job_id": first["job_id"],
        "run_name": first["run_name"],
        "algo_label": first["algo_label"],
        "file": first["file"],
        "calls": len(rows),
        "successful_calls": len(successes),
        "timeout_calls": len(timeout_calls),
        "first_prompt_tokens_est": round(float(first["prompt_tokens_est"]), 3),
        "last_prompt_tokens_est": round(float(last["prompt_tokens_est"]), 3),
        "prompt_growth_tokens_est": round(growth, 3),
        "prompt_growth_pct": round(growth_pct, 3),
        "prompt_tokens_p50": round(percentile(prompt_tokens, 0.50), 3),
        "prompt_tokens_p90": round(percentile(prompt_tokens, 0.90), 3),
        "prompt_tokens_peak": round(max(prompt_tokens) if prompt_tokens else 0.0, 3),
        "total_tokens_p50": round(percentile(total_tokens, 0.50), 3),
        "total_tokens_p90": round(percentile(total_tokens, 0.90), 3),
        "total_tokens_peak": round(max(total_tokens) if total_tokens else 0.0, 3),
        "cum_prompt_tokens_est": float(last["cum_prompt_tokens_est"]),
        "cum_total_tokens_est": float(last["cum_total_tokens_est"]),
        "calls_by_role": by_role,
    }


def summarize_algorithm(run_summaries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for item in run_summaries:
        label = str(item.get("algo_label", "unknown"))
        grouped.setdefault(label, []).append(item)

    out: List[Dict[str, Any]] = []
    for label, items in sorted(grouped.items(), key=lambda kv: kv[0]):
        calls = [int(i["calls"]) for i in items]
        peaks = [float(i["prompt_tokens_peak"]) for i in items]
        growth = [float(i["prompt_growth_tokens_est"]) for i in items]
        timeout_calls = [int(i["timeout_calls"]) for i in items]
        cum_prompt = [float(i["cum_prompt_tokens_est"]) for i in items]

        out.append(
            {
                "algo_label": label,
                "runs": len(items),
                "avg_calls": round(sum(calls) / len(calls), 3),
                "avg_prompt_peak_tokens_est": round(sum(peaks) / len(peaks), 3),
                "avg_prompt_growth_tokens_est": round(sum(growth) / len(growth), 3),
                "avg_cum_prompt_tokens_est": round(sum(cum_prompt) / len(cum_prompt), 3),
                "avg_timeout_calls": round(sum(timeout_calls) / len(timeout_calls), 3),
                "max_prompt_peak_tokens_est": round(max(peaks), 3),
                "max_cum_prompt_tokens_est": round(max(cum_prompt), 3),
            }
        )
    return out


def write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    headers = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    args = parse_args()
    algo_re = re.compile(args.algo_regex)
    files = list(iter_jsonl_files(args.input_paths, args.glob))
    if args.limit_files > 0:
        files = files[: args.limit_files]

    all_call_rows: List[Dict[str, Any]] = []
    run_summaries: List[Dict[str, Any]] = []
    for file_path in files:
        call_rows = build_call_rows(file_path, algo_re, args.chars_per_token)
        if not call_rows:
            continue
        all_call_rows.extend(call_rows)
        run_summaries.append(summarize_run(call_rows))

    algo_summaries = summarize_algorithm(run_summaries)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    calls_csv = output_dir / "context_growth_calls.csv"
    runs_csv = output_dir / "context_growth_runs.csv"
    algos_csv = output_dir / "context_growth_algorithms.csv"
    report_json = output_dir / "context_growth_report.json"

    write_csv(calls_csv, all_call_rows)
    write_csv(runs_csv, run_summaries)
    write_csv(algos_csv, algo_summaries)

    report = {
        "input_files_scanned": len(files),
        "runs_analyzed": len(run_summaries),
        "calls_analyzed": len(all_call_rows),
        "chars_per_token": float(args.chars_per_token),
        "outputs": {
            "calls_csv": str(calls_csv.resolve()),
            "runs_csv": str(runs_csv.resolve()),
            "algorithms_csv": str(algos_csv.resolve()),
        },
        "top_algorithms_by_avg_peak_prompt_tokens": sorted(
            algo_summaries, key=lambda x: float(x["avg_prompt_peak_tokens_est"]), reverse=True
        )[:10],
    }
    report_json.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
