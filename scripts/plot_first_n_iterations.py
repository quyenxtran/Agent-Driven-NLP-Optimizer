#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import matplotlib.pyplot as plt


REPO_ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plot the first N search iterations from an agent-runner artifact."
    )
    parser.add_argument(
        "--artifact",
        default="",
        help="Path to agent-runner.*.json artifact. If omitted, auto-discover from filters.",
    )
    parser.add_argument(
        "--artifact-dir",
        default=str(REPO_ROOT / "artifacts" / "agent_runs"),
        help="Directory to scan when --artifact is not provided.",
    )
    parser.add_argument("--job-id", default="", help="Optional SLURM/PACE job id filter.")
    parser.add_argument("--run-name-contains", default="", help="Optional run-name substring filter.")
    parser.add_argument("--n", type=int, default=10, help="Number of first search iterations to include.")
    parser.add_argument(
        "--output-dir",
        default=str(REPO_ROOT / "artifacts" / "analysis" / "iteration_plots"),
    )
    parser.add_argument("--target-purity", type=float, default=0.60)
    parser.add_argument("--target-recovery-ga", type=float, default=0.75)
    parser.add_argument("--target-recovery-ma", type=float, default=0.75)
    return parser.parse_args()


def find_artifact(args: argparse.Namespace) -> Optional[Path]:
    if args.artifact:
        path = Path(args.artifact)
        return path if path.exists() else None

    root = Path(args.artifact_dir)
    if not root.exists():
        return None

    candidates = sorted(root.glob("agent-runner.*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if args.job_id:
        token = f"agent-runner.{args.job_id}."
        candidates = [p for p in candidates if token in p.name]
    if args.run_name_contains:
        candidates = [p for p in candidates if args.run_name_contains in p.name]
    return candidates[0] if candidates else None


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def extract_metrics(item: Dict[str, Any]) -> Tuple[Optional[Dict[str, float]], bool]:
    metrics = item.get("metrics")
    if isinstance(metrics, dict):
        out: Dict[str, float] = {}
        for k, v in metrics.items():
            try:
                out[k] = float(v)
            except Exception:
                continue
        return out, True
    provisional = item.get("provisional")
    if isinstance(provisional, dict):
        p_metrics = provisional.get("metrics")
        if isinstance(p_metrics, dict):
            out: Dict[str, float] = {}
            for k, v in p_metrics.items():
                try:
                    out[k] = float(v)
                except Exception:
                    continue
            return out, False
    return None, False


def as_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def build_iteration_rows(artifact: Dict[str, Any], n: int) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    search_results = artifact.get("search_results")
    if not isinstance(search_results, list):
        return rows

    best_feasible = float("-inf")
    cum_wall = 0.0
    for idx, item in enumerate(search_results[: max(0, n)], start=1):
        if not isinstance(item, dict):
            continue
        metrics, validated = extract_metrics(item)
        slacks = item.get("constraint_slacks") if isinstance(item.get("constraint_slacks"), dict) else {}
        timing = item.get("timing") if isinstance(item.get("timing"), dict) else {}

        prod = as_float((metrics or {}).get("productivity_ex_ga_ma"))
        purity = as_float((metrics or {}).get("purity_ex_meoh_free"))
        rga = as_float((metrics or {}).get("recovery_ex_GA"))
        rma = as_float((metrics or {}).get("recovery_ex_MA"))
        viol = as_float(slacks.get("normalized_total_violation")) if isinstance(slacks, dict) else None
        wall_s = as_float(timing.get("wall_seconds")) or 0.0
        cum_wall += wall_s
        feasible = bool(item.get("feasible", False))
        if feasible and prod is not None:
            best_feasible = max(best_feasible, prod)

        rows.append(
            {
                "iteration": idx,
                "run_name": str(item.get("run_name", f"search_{idx:03d}")),
                "status": str(item.get("status", "")),
                "validated_metrics": bool(validated),
                "feasible": feasible,
                "productivity": prod,
                "best_feasible_productivity": (best_feasible if best_feasible != float("-inf") else None),
                "purity": purity,
                "recovery_ga": rga,
                "recovery_ma": rma,
                "violation": viol,
                "wall_seconds": wall_s,
                "cum_wall_seconds": cum_wall,
            }
        )
    return rows


def plot_rows(rows: List[Dict[str, Any]], args: argparse.Namespace, title: str, out_png: Path) -> None:
    xs = [int(r["iteration"]) for r in rows]
    prod = [r["productivity"] for r in rows]
    best_prod = [r["best_feasible_productivity"] for r in rows]
    purity = [r["purity"] for r in rows]
    rga = [r["recovery_ga"] for r in rows]
    rma = [r["recovery_ma"] for r in rows]
    viol = [r["violation"] for r in rows]
    wall = [float(r["wall_seconds"] or 0.0) for r in rows]
    cum_wall = [float(r["cum_wall_seconds"] or 0.0) for r in rows]

    fig, axes = plt.subplots(2, 2, figsize=(14, 9), constrained_layout=True)

    ax = axes[0, 0]
    ax.plot(xs, prod, marker="o", label="Productivity")
    ax.plot(xs, best_prod, marker="s", label="Best feasible productivity")
    ax.set_title("Productivity (First N Iterations)")
    ax.set_xlabel("Iteration")
    ax.set_ylabel("productivity_ex_ga_ma")
    ax.grid(True, alpha=0.3)
    ax.legend()

    ax = axes[0, 1]
    ax.plot(xs, purity, marker="o", label="Purity")
    ax.plot(xs, rga, marker="o", label="Recovery GA")
    ax.plot(xs, rma, marker="o", label="Recovery MA")
    ax.axhline(args.target_purity, linestyle="--", label=f"Purity target={args.target_purity:.2f}")
    ax.axhline(args.target_recovery_ga, linestyle="--", label=f"Recovery targets={args.target_recovery_ga:.2f}/{args.target_recovery_ma:.2f}")
    ax.set_title("Quality Metrics")
    ax.set_xlabel("Iteration")
    ax.set_ylabel("Metric")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8)

    ax = axes[1, 0]
    safe_viol = [max(v, 1e-12) if v is not None else None for v in viol]
    ax.plot(xs, safe_viol, marker="o", label="Normalized violation")
    ax.set_yscale("log")
    ax.set_title("Constraint Violation (log scale)")
    ax.set_xlabel("Iteration")
    ax.set_ylabel("normalized_total_violation")
    ax.grid(True, alpha=0.3)
    ax.legend()

    ax = axes[1, 1]
    ax.bar(xs, wall, alpha=0.7, label="Wall seconds per iter")
    ax2 = ax.twinx()
    ax2.plot(xs, cum_wall, color="tab:red", marker="o", label="Cumulative wall seconds")
    ax.set_title("Runtime")
    ax.set_xlabel("Iteration")
    ax.set_ylabel("wall seconds")
    ax2.set_ylabel("cum wall seconds", color="tab:red")
    ax.grid(True, alpha=0.3)
    lines, labels = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines + lines2, labels + labels2, loc="upper left", fontsize=8)

    fig.suptitle(title)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=150)
    plt.close(fig)


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
    artifact_path = find_artifact(args)
    if artifact_path is None:
        print("ERROR: could not find agent-runner artifact. Use --artifact or adjust --artifact-dir/filters.")
        return 2

    artifact = load_json(artifact_path)
    rows = build_iteration_rows(artifact, args.n)
    if not rows:
        print(f"ERROR: no search_results found in {artifact_path}")
        return 3

    run_name = str(artifact.get("run_name", artifact_path.stem))
    out_dir = Path(args.output_dir)
    out_png = out_dir / f"{run_name}.first_{args.n}_iterations.png"
    out_csv = out_dir / f"{run_name}.first_{args.n}_iterations.csv"

    title = f"{run_name} - First {min(args.n, len(rows))} Iterations"
    plot_rows(rows, args, title, out_png)
    write_csv(out_csv, rows)

    payload = {
        "artifact": str(artifact_path.resolve()),
        "run_name": run_name,
        "iterations_plotted": len(rows),
        "output_png": str(out_png.resolve()),
        "output_csv": str(out_csv.resolve()),
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
