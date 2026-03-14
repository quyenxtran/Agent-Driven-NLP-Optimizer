#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import textwrap
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple
from urllib import error, request

from . import run_stage as rs


REPO_ROOT = Path(__file__).resolve().parents[1]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the two-scientist SMB agent benchmark.")
    parser.add_argument("--run-name", default=os.environ.get("SMB_EXPERIMENT_NAME", "qwen_smb_two_scientists"))
    parser.add_argument("--artifact-dir", default=str(REPO_ROOT / "artifacts" / "agent_runs"))
    parser.add_argument("--conversation-log", default=os.environ.get("SMB_CONVERSATION_LOG", ""))
    parser.add_argument("--conversation-stream-log", default=os.environ.get("SMB_CONVERSATION_STREAM_LOG", ""))
    parser.add_argument("--sqlite-db", default=os.environ.get("SMB_SQLITE_DB", str(REPO_ROOT / "artifacts" / "agent_runs" / "smb_agent_context.sqlite")))
    parser.add_argument("--research-md", default=os.environ.get("SMB_RESEARCH_MD", str(REPO_ROOT / "research.md")))
    parser.add_argument("--research-tail-chars", type=int, default=int(os.environ.get("SMB_RESEARCH_TAIL_CHARS", "6000")))
    parser.add_argument("--reset-research-section", action="store_true", default=os.environ.get("SMB_RESEARCH_RESET_SECTION", "0") == "1")
    parser.add_argument("--nc-library", default=os.environ.get("SMB_NC_LIBRARY", "1,2,3,2;2,2,2,2;1,3,2,2"))
    parser.add_argument("--seed-library", default=os.environ.get("SMB_SEED_LIBRARY", "notebook"))
    parser.add_argument("--solver-name", default=os.environ.get("SMB_SOLVER_NAME", "auto"))
    parser.add_argument("--linear-solver", default=os.environ.get("SMB_LINEAR_SOLVER", "mumps"))
    parser.add_argument("--benchmark-hours", type=float, default=float(os.environ.get("SMB_BENCHMARK_HOURS", "5.0")))
    parser.add_argument("--search-hours", type=float, default=float(os.environ.get("SMB_SEARCH_BUDGET_HOURS", "4.0")))
    parser.add_argument("--validation-hours", type=float, default=float(os.environ.get("SMB_VALIDATION_BUDGET_HOURS", "1.0")))
    parser.add_argument("--max-search-evals", type=int, default=int(os.environ.get("SMB_AGENT_MAX_SEARCH_EVALS", "18")))
    parser.add_argument("--max-validations", type=int, default=int(os.environ.get("SMB_AGENT_MAX_VALIDATIONS", "3")))
    parser.add_argument("--tee", action="store_true", default=os.environ.get("SMB_AGENT_TEE", "0") == "1")
    parser.add_argument("--llm-enabled", action="store_true", default=os.environ.get("SMB_AGENT_LLM_ENABLED", "1") == "1")
    parser.add_argument("--llm-base-url", default=os.environ.get("OLLAMA_BASE_URL", ""))
    parser.add_argument("--llm-model", default=os.environ.get("OLLAMA_MODEL", os.environ.get("SMB_LOCAL_LLM_MODEL", "qwen3.5:9b")))
    parser.add_argument("--llm-api-key", default=os.environ.get("OLLAMA_API_KEY", "ollama"))
    parser.add_argument(
        "--fallback-llm-enabled",
        action="store_true",
        default=os.environ.get("SMB_FALLBACK_LLM_ENABLED", "1") == "1",
    )
    parser.add_argument(
        "--fallback-llm-base-url",
        default=os.environ.get("SMB_FALLBACK_LLM_BASE_URL", os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")),
    )
    parser.add_argument("--fallback-llm-model", default=os.environ.get("SMB_FALLBACK_LLM_MODEL", "gpt-5-nano"))
    parser.add_argument(
        "--fallback-llm-api-key",
        default=os.environ.get("SMB_FALLBACK_LLM_API_KEY", os.environ.get("OPENAI_API_KEY", "")),
    )
    parser.add_argument("--objectives-file", default=os.environ.get("SMB_OBJECTIVES_FILE", str(REPO_ROOT / "Objectives.md")))
    parser.add_argument("--llm-soul-file", default=os.environ.get("SMB_LLM_SOUL_FILE", str(REPO_ROOT / "LLM_SOUL.md")))
    parser.add_argument("--ipopt-resource-file", default=os.environ.get("SMB_IPOPT_RESOURCE_FILE", str(REPO_ROOT / "IPOPT_SOLVER_RESOURCES.md")))
    return parser


def make_stage_args(stage: str) -> argparse.Namespace:
    return rs.build_parser().parse_args(["--stage", stage])


def env_or_default(name: str, default: str) -> str:
    value = os.environ.get(name)
    return value if value not in {None, ""} else default


def as_float(value: object) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def layout_text(nc: object) -> str:
    if isinstance(nc, (list, tuple)) and len(nc) == 4:
        return ",".join(str(int(v)) for v in nc)
    return ""


def extract_metrics_with_validity(result: Dict[str, object]) -> Tuple[Dict[str, object], Optional[bool]]:
    metrics = result.get("metrics")
    if isinstance(metrics, dict):
        return metrics, True
    provisional = result.get("provisional")
    if isinstance(provisional, dict):
        provisional_metrics = provisional.get("metrics")
        if isinstance(provisional_metrics, dict):
            return provisional_metrics, False
    return {}, None


def open_sqlite_db(path: str) -> sqlite3.Connection:
    db_path = Path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS simulation_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            agent_run_name TEXT NOT NULL,
            phase TEXT NOT NULL,
            source_stage TEXT,
            candidate_run_name TEXT NOT NULL,
            nc TEXT,
            seed_name TEXT,
            status TEXT,
            feasible INTEGER,
            j_validated REAL,
            productivity REAL,
            purity REAL,
            recovery_ga REAL,
            recovery_ma REAL,
            normalized_total_violation REAL,
            metrics_validated INTEGER,
            solver_name TEXT,
            linear_solver TEXT,
            termination_condition TEXT,
            wall_seconds REAL,
            cpu_hours REAL,
            ffeed REAL,
            f1 REAL,
            fdes REAL,
            fex REAL,
            fraf REAL,
            tstep REAL,
            raw_json TEXT,
            UNIQUE(agent_run_name, phase, candidate_run_name)
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_sim_created ON simulation_results(created_at DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_sim_feasible ON simulation_results(feasible)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_sim_jval ON simulation_results(j_validated DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_sim_violation ON simulation_results(normalized_total_violation ASC)")
    conn.commit()
    return conn


def persist_result_to_sqlite(conn: sqlite3.Connection, agent_run_name: str, phase: str, result: Dict[str, object]) -> None:
    metrics, metrics_validated = extract_metrics_with_validity(result)
    flow = effective_flow(result) or {}
    slacks = result.get("constraint_slacks")
    if not isinstance(slacks, dict):
        slacks = {}
    solver = result.get("solver")
    if not isinstance(solver, dict):
        solver = {}
    solver_options = solver.get("solver_options")
    if not isinstance(solver_options, dict):
        solver_options = {}
    timing = result.get("timing")
    if not isinstance(timing, dict):
        timing = {}

    conn.execute(
        """
        INSERT INTO simulation_results (
            agent_run_name, phase, source_stage, candidate_run_name, nc, seed_name, status, feasible, j_validated,
            productivity, purity, recovery_ga, recovery_ma, normalized_total_violation, metrics_validated,
            solver_name, linear_solver, termination_condition, wall_seconds, cpu_hours, ffeed, f1, fdes, fex,
            fraf, tstep, raw_json
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
        ON CONFLICT(agent_run_name, phase, candidate_run_name) DO UPDATE SET
            created_at = datetime('now'),
            source_stage = excluded.source_stage,
            nc = excluded.nc,
            seed_name = excluded.seed_name,
            status = excluded.status,
            feasible = excluded.feasible,
            j_validated = excluded.j_validated,
            productivity = excluded.productivity,
            purity = excluded.purity,
            recovery_ga = excluded.recovery_ga,
            recovery_ma = excluded.recovery_ma,
            normalized_total_violation = excluded.normalized_total_violation,
            metrics_validated = excluded.metrics_validated,
            solver_name = excluded.solver_name,
            linear_solver = excluded.linear_solver,
            termination_condition = excluded.termination_condition,
            wall_seconds = excluded.wall_seconds,
            cpu_hours = excluded.cpu_hours,
            ffeed = excluded.ffeed,
            f1 = excluded.f1,
            fdes = excluded.fdes,
            fex = excluded.fex,
            fraf = excluded.fraf,
            tstep = excluded.tstep,
            raw_json = excluded.raw_json
        """,
        (
            agent_run_name,
            phase,
            str(result.get("stage", "")),
            str(result.get("run_name", "")),
            layout_text(result.get("nc")),
            str(result.get("seed_name", "")),
            str(result.get("status", "")),
            1 if bool(result.get("feasible", False)) else 0,
            as_float(result.get("J_validated")),
            as_float(metrics.get("productivity_ex_ga_ma")),
            as_float(metrics.get("purity_ex_meoh_free")),
            as_float(metrics.get("recovery_ex_GA")),
            as_float(metrics.get("recovery_ex_MA")),
            as_float(slacks.get("normalized_total_violation")),
            1 if metrics_validated is True else (0 if metrics_validated is False else None),
            str(solver.get("solver_name", "")),
            str(solver_options.get("linear_solver", "")),
            str(solver.get("termination_condition", "")),
            as_float(timing.get("wall_seconds")),
            as_float(timing.get("cpu_hours_accounted")),
            as_float(flow.get("Ffeed")),
            as_float(flow.get("F1")),
            as_float(flow.get("Fdes")),
            as_float(flow.get("Fex")),
            as_float(flow.get("Fraf")),
            as_float(flow.get("tstep")),
            json.dumps(result, separators=(",", ":"), ensure_ascii=True),
        ),
    )
    conn.commit()


def sqlite_history_context(conn: sqlite3.Connection, max_feasible: int = 5, max_near: int = 5, max_recent: int = 6) -> str:
    counts = conn.execute(
        """
        SELECT COUNT(*) AS total, COALESCE(SUM(CASE WHEN feasible=1 THEN 1 ELSE 0 END), 0) AS feasible_count
        FROM simulation_results
        """
    ).fetchone()
    total = int(counts[0]) if counts else 0
    feasible_count = int(counts[1]) if counts else 0

    feasible_rows = conn.execute(
        """
        SELECT candidate_run_name, nc, seed_name, j_validated, productivity
        FROM simulation_results
        WHERE feasible=1 AND j_validated IS NOT NULL
        ORDER BY j_validated DESC, productivity DESC, id DESC
        LIMIT ?
        """,
        (max_feasible,),
    ).fetchall()

    near_rows = conn.execute(
        """
        SELECT candidate_run_name, nc, seed_name, normalized_total_violation, productivity
        FROM simulation_results
        WHERE feasible=0 AND normalized_total_violation IS NOT NULL
        ORDER BY normalized_total_violation ASC, productivity DESC, id DESC
        LIMIT ?
        """,
        (max_near,),
    ).fetchall()

    recent_rows = conn.execute(
        """
        SELECT candidate_run_name, nc, status, feasible, productivity, normalized_total_violation
        FROM simulation_results
        ORDER BY id DESC
        LIMIT ?
        """,
        (max_recent,),
    ).fetchall()

    lines = [
        f"SQLite context: total_records={total}, feasible_records={feasible_count}",
        "Top feasible records by J_validated:",
    ]
    if feasible_rows:
        for row in feasible_rows:
            lines.append(
                f"- {row[0]} nc={row[1]} seed={row[2]} J={row[3]} prod={row[4]}"
            )
    else:
        lines.append("- none")

    lines.append("Top near-feasible records by normalized violation:")
    if near_rows:
        for row in near_rows:
            lines.append(
                f"- {row[0]} nc={row[1]} seed={row[2]} viol={row[3]} prod={row[4]}"
            )
    else:
        lines.append("- none")

    lines.append("Most recent records:")
    if recent_rows:
        for row in recent_rows:
            lines.append(
                f"- {row[0]} nc={row[1]} status={row[2]} feasible={bool(row[3])} prod={row[4]} viol={row[5]}"
            )
    else:
        lines.append("- none")

    return "\n".join(lines)


def sqlite_record_count(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COUNT(*) FROM simulation_results").fetchone()
    return int(row[0]) if row else 0


def sqlite_layout_trend_table(conn: sqlite3.Connection, max_rows: int = 10) -> str:
    rows = conn.execute(
        """
        SELECT
            COALESCE(nc, '') AS nc,
            COUNT(*) AS n_total,
            COALESCE(SUM(CASE WHEN feasible=1 THEN 1 ELSE 0 END), 0) AS n_feasible,
            MIN(normalized_total_violation) AS best_violation,
            MAX(productivity) AS best_productivity,
            MAX(j_validated) AS best_j_validated
        FROM simulation_results
        GROUP BY nc
        ORDER BY
            COALESCE(MAX(j_validated), -1e99) DESC,
            COALESCE(MAX(productivity), -1e99) DESC,
            COALESCE(MIN(normalized_total_violation), 1e99) ASC,
            nc ASC
        LIMIT ?
        """,
        (max_rows,),
    ).fetchall()
    if not rows:
        return "No layout trends yet."

    lines = [
        "| nc | n_total | n_feasible | best_violation | best_productivity | best_J_validated |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for nc, n_total, n_feasible, best_violation, best_productivity, best_j_validated in rows:
        lines.append(
            "| "
            + f"{nc or '<none>'} | {int(n_total)} | {int(n_feasible)} | "
            + f"{best_violation if best_violation is not None else ''} | "
            + f"{best_productivity if best_productivity is not None else ''} | "
            + f"{best_j_validated if best_j_validated is not None else ''} |"
        )
    return "\n".join(lines)


def configure_stage_args(base: argparse.Namespace, args: argparse.Namespace) -> argparse.Namespace:
    stage_args = argparse.Namespace(**vars(base))
    stage_args.solver_name = args.solver_name
    stage_args.linear_solver = args.linear_solver
    stage_args.tee = args.tee
    stage_args.nc_library = args.nc_library
    stage_args.seed_library = args.seed_library
    stage_args.max_iter = 5000
    stage_args.tol = 1e-6
    stage_args.acceptable_tol = 1e-5
    stage_args.nfex = int(env_or_default("SMB_NFEX", str(stage_args.nfex)))
    stage_args.nfet = int(env_or_default("SMB_NFET", str(stage_args.nfet)))
    stage_args.ncp = int(env_or_default("SMB_NCP", str(stage_args.ncp)))
    stage_args.ffeed_bounds = env_or_default("SMB_FFEED_BOUNDS", stage_args.ffeed_bounds)
    stage_args.f1_bounds = env_or_default("SMB_F1_BOUNDS", stage_args.f1_bounds)
    stage_args.fdes_bounds = env_or_default("SMB_FDES_BOUNDS", stage_args.fdes_bounds)
    stage_args.fex_bounds = env_or_default("SMB_FEX_BOUNDS", stage_args.fex_bounds)
    stage_args.fraf_bounds = env_or_default("SMB_FRAF_BOUNDS", stage_args.fraf_bounds)
    stage_args.tstep_bounds = env_or_default("SMB_TSTEP_BOUNDS", stage_args.tstep_bounds)
    stage_args.max_pump_flow = float(env_or_default("SMB_MAX_PUMP_FLOW_ML_MIN", str(stage_args.max_pump_flow)))
    stage_args.f1_max_flow = float(env_or_default("SMB_F1_MAX_FLOW", str(stage_args.f1_max_flow)))
    stage_args.f1_max = float(env_or_default("SMB_F1_MAX_FLOW", str(stage_args.f1_max_flow)))
    stage_args.purity_min = float(env_or_default("SMB_TARGET_PURITY_EX_MEOH_FREE", str(stage_args.purity_min)))
    stage_args.recovery_ga_min = float(env_or_default("SMB_TARGET_RECOVERY_GA", str(stage_args.recovery_ga_min)))
    stage_args.recovery_ma_min = float(env_or_default("SMB_TARGET_RECOVERY_MA", str(stage_args.recovery_ma_min)))
    stage_args.meoh_max_raff_wt = float(env_or_default("SMB_MEOH_MAX_RAFF_WT", str(stage_args.meoh_max_raff_wt)))
    stage_args.water_max_ex_wt = float(env_or_default("SMB_WATER_MAX_EX_WT", str(stage_args.water_max_ex_wt)))
    stage_args.water_max_zone1_entry_wt = float(
        env_or_default("SMB_WATER_MAX_ZONE1_ENTRY_WT", str(stage_args.water_max_zone1_entry_wt))
    )
    return stage_args


class OpenAICompatClient:
    def __init__(
        self,
        base_url: str,
        model: str,
        enabled: bool,
        api_key: str = "ollama",
        fallback_enabled: bool = False,
        fallback_base_url: str = "",
        fallback_model: str = "",
        fallback_api_key: str = "",
        conversation_stream_path: Optional[Path] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.enabled = enabled and bool(self.base_url) and bool(self.model)
        self.fallback_base_url = fallback_base_url.rstrip("/")
        self.fallback_model = fallback_model
        self.fallback_api_key = fallback_api_key
        self.fallback_enabled = (
            fallback_enabled
            and bool(self.fallback_base_url)
            and bool(self.fallback_model)
            and bool(self.fallback_api_key)
        )
        self.last_backend = "none"
        self.call_counter = 0
        self.conversations: List[Dict[str, object]] = []
        self.conversation_stream_path = conversation_stream_path

    def _append_conversation_stream(self, record: Dict[str, object]) -> None:
        if self.conversation_stream_path is None:
            return
        try:
            self.conversation_stream_path.parent.mkdir(parents=True, exist_ok=True)
            with self.conversation_stream_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=True) + "\n")
        except Exception:
            # Streaming is best-effort; full transcript is still persisted at run end.
            return

    def _chat_once(
        self,
        base_url: str,
        model: str,
        api_key: str,
        system_prompt: str,
        user_prompt: str,
    ) -> Tuple[Optional[str], str]:
        if not base_url or not model:
            return None, "missing_base_url_or_model"
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        }
        req = request.Request(
            f"{base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=120) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            return body["choices"][0]["message"]["content"], ""
        except error.HTTPError as exc:
            return None, f"http_error_{exc.code}"
        except error.URLError as exc:
            return None, f"url_error_{str(exc.reason)}"
        except TimeoutError:
            return None, "timeout"
        except KeyError:
            return None, "missing_choices_message_content"
        except json.JSONDecodeError:
            return None, "invalid_json_response"
        except Exception as exc:  # pragma: no cover - defensive fallback
            return None, f"unexpected_error_{type(exc).__name__}"

    def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        conversation_role: str = "generic",
        metadata: Optional[Dict[str, object]] = None,
    ) -> Optional[str]:
        self.call_counter += 1
        record: Dict[str, object] = {
            "call_id": self.call_counter,
            "timestamp_utc": utc_now_text(),
            "role": conversation_role,
            "metadata": metadata or {},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "attempts": [],
        }

        if self.enabled:
            content, err = self._chat_once(self.base_url, self.model, self.api_key, system_prompt, user_prompt)
            record["attempts"].append(
                {
                    "backend": "primary",
                    "base_url": self.base_url,
                    "model": self.model,
                    "success": content is not None,
                    "error": err,
                }
            )
            if content is not None:
                self.last_backend = "primary"
                record["final_backend"] = self.last_backend
                record["assistant_response"] = content
                self.conversations.append(record)
                self._append_conversation_stream(record)
                return content
        if self.fallback_enabled:
            content, err = self._chat_once(
                self.fallback_base_url,
                self.fallback_model,
                self.fallback_api_key,
                system_prompt,
                user_prompt,
            )
            record["attempts"].append(
                {
                    "backend": "fallback",
                    "base_url": self.fallback_base_url,
                    "model": self.fallback_model,
                    "success": content is not None,
                    "error": err,
                }
            )
            if content is not None:
                self.last_backend = "fallback"
                record["final_backend"] = self.last_backend
                record["assistant_response"] = content
                self.conversations.append(record)
                self._append_conversation_stream(record)
                return content
        self.last_backend = "none"
        record["final_backend"] = self.last_backend
        self.conversations.append(record)
        self._append_conversation_stream(record)
        return None

    @staticmethod
    def extract_json(text: Optional[str]) -> Optional[Dict[str, object]]:
        if not text:
            return None
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None


def read_doc_excerpt(path: str, max_chars: int = 4000) -> str:
    p = Path(path)
    if not p.exists():
        return f"Missing file: {path}"
    return p.read_text(encoding="utf-8")[:max_chars]


def utc_now_text() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def normalize_text_list(value: object, max_items: int = 8) -> List[str]:
    items: List[str] = []
    if isinstance(value, list):
        for entry in value:
            if isinstance(entry, str):
                text = " ".join(entry.split())
                if text:
                    items.append(text)
    elif isinstance(value, str):
        for entry in value.splitlines():
            text = " ".join(entry.split())
            if text:
                items.append(text)
    return items[:max_items]


def parse_constraint_names(source: str) -> List[str]:
    names = re.findall(r"m\.(\w+)\s*=\s*Constraint", source)
    return sorted(set(names))


def read_file_or_missing(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def build_codebase_context() -> Dict[str, object]:
    optimization_file = REPO_ROOT / "SembaSMB" / "src" / "smb_optimization.py"
    model_file = REPO_ROOT / "SembaSMB" / "src" / "smb_model.py"
    metrics_file = REPO_ROOT / "SembaSMB" / "src" / "smb_metrics.py"
    run_stage_file = REPO_ROOT / "benchmarks" / "run_stage.py"
    config_file = REPO_ROOT / "SembaSMB" / "src" / "smb_config.py"
    solver_file = REPO_ROOT / "SembaSMB" / "src" / "smb_solver.py"

    optimization_text = read_file_or_missing(optimization_file)
    model_text = read_file_or_missing(model_file)
    metrics_text = read_file_or_missing(metrics_file)
    run_stage_text = read_file_or_missing(run_stage_file)
    config_text = read_file_or_missing(config_file)
    solver_text = read_file_or_missing(solver_file)

    objective_match = re.search(r"m\.obj\s*=\s*Objective\((.+)\)", optimization_text)
    objective_line = objective_match.group(0).strip() if objective_match else "objective line not detected"
    stage_match = re.search(r'choices=\[(.*?)\]', run_stage_text, flags=re.DOTALL)
    stage_list = []
    if stage_match:
        stage_list = [item.strip().strip("'\"") for item in stage_match.group(1).split(",")]

    flow_linked = "RaffinateConsistency" in optimization_text
    map_solver = "solve_model" in solver_text
    metric_keys = re.findall(r"'([a-zA-Z0-9_]+)'\s*:", metrics_text)
    metric_keys = sorted({key for key in metric_keys if key.startswith(("purity", "recovery", "productivity", "Frec"))})
    config_symbols = re.findall(r"^\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:", config_text, flags=re.MULTILINE)
    config_symbols = sorted(set(config_symbols))[:12]

    return {
        "optimization_file": str(optimization_file),
        "model_file": str(model_file),
        "metrics_file": str(metrics_file),
        "run_stage_file": str(run_stage_file),
        "constraint_names_optimization": parse_constraint_names(optimization_text),
        "constraint_names_model": parse_constraint_names(model_text),
        "objective_expression": objective_line,
        "flow_consistency_constraint_present": flow_linked,
        "solver_entrypoint_present": map_solver,
        "known_metric_keys": metric_keys,
        "known_config_fields": config_symbols,
        "available_stages": stage_list,
    }


def codebase_context_text(context: Dict[str, object]) -> str:
    lines = [
        f"Optimization file: {context.get('optimization_file')}",
        f"Model file: {context.get('model_file')}",
        f"Metrics file: {context.get('metrics_file')}",
        f"Benchmark stage driver: {context.get('run_stage_file')}",
        f"Optimization constraints: {context.get('constraint_names_optimization')}",
        f"Model constraints: {context.get('constraint_names_model')}",
        f"Objective expression: {context.get('objective_expression')}",
        f"Flow-consistency in optimization: {context.get('flow_consistency_constraint_present')}",
        f"Solver entrypoint present: {context.get('solver_entrypoint_present')}",
        f"Metrics available in code: {context.get('known_metric_keys')}",
        f"Key config fields: {context.get('known_config_fields')}",
        f"Benchmark stages: {context.get('available_stages')}",
    ]
    return "\n".join(lines)


def default_initial_priority_plan(args: argparse.Namespace) -> Dict[str, object]:
    return {
        "mode": "deterministic",
        "priorities": [
            "Feasibility-first: reduce normalized_total_violation before maximizing productivity.",
            "Respect hard bounds and flow consistency: keep flows in configured bounds and treat raffinate as derived.",
            "Screen layouts quickly at medium fidelity, then validate top candidates at high fidelity.",
            f"Use solver stack {args.solver_name}/{args.linear_solver} and track termination_condition per run.",
            "Use provisional metrics only as direction signals; prefer validated metrics for ranking.",
        ],
        "proposed_simulations": [
            "Run each nc layout with notebook seeds and identify near-feasible candidates.",
            "Perturb feed/desorbent/extract around best near-feasible point to reduce violation.",
            "Promote top candidates to high-fidelity validation.",
        ],
        "risks": [
            "Local infeasibility from tight purity/recovery constraints.",
            "Solver-status 'other' without usable primal variables.",
            "Bounds clipping on internal velocities when tstep/flows are inconsistent.",
        ],
    }


def initial_priority_plan(
    client: OpenAICompatClient,
    args: argparse.Namespace,
    objectives_excerpt: str,
    soul_excerpt: str,
    codebase_excerpt: str,
    sqlite_excerpt: str,
) -> Dict[str, object]:
    default_plan = default_initial_priority_plan(args)
    prompt = textwrap.dedent(
        f"""
        You are generating the initial research plan for a two-scientist SMB campaign.
        Objective context:
        {objectives_excerpt}

        Scientist operating rules:
        {soul_excerpt}

        Codebase context:
        {codebase_excerpt}

        Existing SQLite run history:
        {sqlite_excerpt}

        Respond with JSON only:
        {{
          "priorities": ["..."],
          "proposed_simulations": ["..."],
          "risks": ["..."],
          "reason": "..."
        }}
        """
    ).strip()
    raw = client.chat(
        "You are a principal SMB process scientist. Return JSON only.",
        prompt,
        conversation_role="initial_priority_plan",
        metadata={
            "phase": "planning",
            "solver_name": args.solver_name,
            "linear_solver": args.linear_solver,
            "nc_library": args.nc_library,
            "seed_library": args.seed_library,
        },
    )
    data = client.extract_json(raw)
    if not isinstance(data, dict):
        return default_plan
    priorities = normalize_text_list(data.get("priorities"), max_items=8)
    simulations = normalize_text_list(data.get("proposed_simulations"), max_items=8)
    risks = normalize_text_list(data.get("risks"), max_items=8)
    if not priorities:
        return default_plan
    return {
        "mode": "llm",
        "priorities": priorities,
        "proposed_simulations": simulations or default_plan["proposed_simulations"],
        "risks": risks or default_plan["risks"],
        "reason": str(data.get("reason", "")),
        "raw": raw,
    }


def read_research_tail(path: Path, max_chars: int) -> str:
    if not path.exists():
        return "No research log yet."
    text = path.read_text(encoding="utf-8")
    if len(text) <= max_chars:
        return text
    return text[-max_chars:]


def append_research(path: Path, section: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(section)


def reset_research_run_section(path: Path, run_name: str) -> None:
    if not path.exists():
        return
    marker = f"\n## Run: {run_name}\n"
    text = path.read_text(encoding="utf-8")
    idx = text.find(marker)
    if idx == -1:
        return
    path.write_text(text[:idx].rstrip() + "\n", encoding="utf-8")


def start_research_log(
    path: Path,
    args: argparse.Namespace,
    code_context_text_block: str,
    initial_plan: Dict[str, object],
    sqlite_excerpt: str,
    layout_trends: str,
) -> None:
    if not path.exists():
        append_research(
            path,
            "# SMB Two-Scientist Research Log\n\n"
            "This file captures planning, priorities, findings, and proposed simulation updates.\n",
        )
    section = [
        f"\n## Run: {args.run_name}\n",
        f"- started_utc: {utc_now_text()}",
        f"- benchmark_hours: {args.benchmark_hours}",
        f"- search_hours: {args.search_hours}",
        f"- validation_hours: {args.validation_hours}",
        f"- solver_name: {args.solver_name}",
        f"- linear_solver: {args.linear_solver}",
        f"- nc_library: {args.nc_library}",
        f"- seed_library: {args.seed_library}",
        f"- sqlite_db: {args.sqlite_db}",
        "",
        "### Codebase Context Snapshot",
        "```text",
        code_context_text_block,
        "```",
        "",
        "### Existing History Snapshot",
        "```text",
        sqlite_excerpt,
        "```",
        "",
        "### Initial Priorities",
    ]
    for item in normalize_text_list(initial_plan.get("priorities"), max_items=12):
        section.append(f"- {item}")
    section.append("")
    section.append("### Initial Proposed Simulations")
    for item in normalize_text_list(initial_plan.get("proposed_simulations"), max_items=12):
        section.append(f"- {item}")
    section.append("")
    section.append("### Initial Risks")
    for item in normalize_text_list(initial_plan.get("risks"), max_items=12):
        section.append(f"- {item}")
    section.append("")
    section.append("### Insights and Trends (Rolling)")
    section.append(layout_trends)
    section.append("")
    append_research(path, "\n".join(section) + "\n")


def append_iteration_research(
    path: Path,
    iteration: int,
    task: Dict[str, object],
    a_note: Dict[str, object],
    b_note: Dict[str, object],
) -> None:
    lines = [
        f"\n### Search Iteration {iteration:02d}",
        f"- timestamp_utc: {utc_now_text()}",
        f"- candidate_nc: {task.get('nc')}",
        f"- candidate_seed: {task.get('seed_name')}",
        f"- scientist_a_reason: {a_note.get('reason')}",
        f"- scientist_a_mode: {a_note.get('mode')}",
        f"- scientist_a_llm_backend: {a_note.get('llm_backend', '')}",
        f"- scientist_b_decision: {b_note.get('decision')}",
        f"- scientist_b_reason: {b_note.get('reason')}",
        f"- scientist_b_mode: {b_note.get('mode')}",
        f"- scientist_b_llm_backend: {b_note.get('llm_backend', '')}",
    ]
    a_updates = normalize_text_list(a_note.get("priority_updates"), max_items=6)
    b_updates = normalize_text_list(b_note.get("priority_updates"), max_items=6)
    if a_updates or b_updates:
        lines.append("- priority_updates:")
        for item in a_updates + b_updates:
            lines.append(f"  - {item}")
    append_research(path, "\n".join(lines) + "\n")


def append_result_research(path: Path, result: Dict[str, object], phase: str) -> None:
    flow = effective_flow(result) or {}
    metrics = result.get("metrics")
    if not isinstance(metrics, dict):
        provisional = result.get("provisional")
        metrics = provisional.get("metrics") if isinstance(provisional, dict) else {}
        if not isinstance(metrics, dict):
            metrics = {}
    slacks = result.get("constraint_slacks")
    if not isinstance(slacks, dict):
        slacks = {}

    lines = [
        f"- {phase}_result_run: {result.get('run_name')}",
        f"  - status: {result.get('status')}",
        f"  - feasible: {result.get('feasible')}",
        f"  - termination: {(result.get('solver') or {}).get('termination_condition') if isinstance(result.get('solver'), dict) else ''}",
        f"  - productivity_ex_ga_ma: {metrics.get('productivity_ex_ga_ma')}",
        f"  - purity_ex_meoh_free: {metrics.get('purity_ex_meoh_free')}",
        f"  - recovery_ex_GA: {metrics.get('recovery_ex_GA')}",
        f"  - recovery_ex_MA: {metrics.get('recovery_ex_MA')}",
        f"  - normalized_total_violation: {slacks.get('normalized_total_violation')}",
        f"  - flow: {flow}",
    ]
    append_research(path, "\n".join(lines) + "\n")


def append_final_research(
    path: Path,
    best_result: Optional[Dict[str, object]],
    ranked_search: List[Dict[str, object]],
    ranked_validation: List[Dict[str, object]],
) -> None:
    lines = [
        "\n### Run Closing Summary",
        f"- finished_utc: {utc_now_text()}",
        f"- best_result: {best_result.get('run_name') if isinstance(best_result, dict) else 'none'}",
        f"- best_status: {best_result.get('status') if isinstance(best_result, dict) else 'n/a'}",
        f"- search_results_count: {len(ranked_search)}",
        f"- validation_results_count: {len(ranked_validation)}",
        "",
        "### Proposed Next Simulations",
    ]
    if ranked_search:
        top = ranked_search[:3]
        for item in top:
            flow = effective_flow(item) or {}
            lines.append(
                f"- Probe around run={item.get('run_name')} nc={item.get('nc')} "
                f"with +/- small perturbations on Ffeed/Fdes/Fex while preserving flow consistency. Base flow={flow}"
            )
    else:
        lines.append("- Re-run layout/seed screening with broader nc and notebook seeds; no valid search record yet.")
    append_research(path, "\n".join(lines) + "\n")


def merge_priority_board(current: List[str], *notes: Dict[str, object]) -> List[str]:
    merged: List[str] = []
    seen: set[str] = set()
    for item in current:
        text = " ".join(str(item).split())
        if text and text not in seen:
            seen.add(text)
            merged.append(text)
    for note in notes:
        for item in normalize_text_list(note.get("priority_updates"), max_items=8):
            if item not in seen:
                seen.add(item)
                merged.append(item)
    return merged[:16]


def safe_result_metric(result: Dict[str, object], key: str) -> Optional[float]:
    if result.get("status") == "ok":
        metrics = result.get("metrics") or {}
        if key in metrics:
            return float(metrics[key])  # type: ignore[arg-type]
    provisional = result.get("provisional") or {}
    metrics = provisional.get("metrics") or {}
    if key in metrics:
        return float(metrics[key])  # type: ignore[arg-type]
    return None


def effective_flow(result: Dict[str, object]) -> Optional[Dict[str, float]]:
    for key in ("optimized_flow", "provisional_optimized_flow", "initial_flow", "flow"):
        value = result.get(key)
        if isinstance(value, dict):
            return {k: float(v) for k, v in value.items()}
    return None


def effective_violation(result: Dict[str, object]) -> float:
    slacks = result.get("constraint_slacks")
    if isinstance(slacks, dict) and "normalized_total_violation" in slacks:
        return float(slacks["normalized_total_violation"])
    provisional = result.get("provisional")
    if isinstance(provisional, dict):
        metrics = provisional.get("metrics") or {}
        return -float(metrics.get("productivity_ex_ga_ma", 0.0))
    return 1e9


def search_score(result: Dict[str, object]) -> Tuple[int, float, float]:
    feasible = 1 if result.get("feasible") else 0
    productivity = safe_result_metric(result, "productivity_ex_ga_ma") or float("-inf")
    violation = effective_violation(result)
    return feasible, productivity, -violation


def summarize_result(result: Dict[str, object]) -> str:
    flow = effective_flow(result) or {}
    productivity = safe_result_metric(result, "productivity_ex_ga_ma")
    purity = safe_result_metric(result, "purity_ex_meoh_free")
    rga = safe_result_metric(result, "recovery_ex_GA")
    rma = safe_result_metric(result, "recovery_ex_MA")
    return (
        f"run={result.get('run_name')} nc={result.get('nc')} status={result.get('status')} "
        f"feasible={result.get('feasible')} "
        f"prod={productivity} purity={purity} rGA={rga} rMA={rma} "
        f"flow={flow}"
    )


def deterministic_select(tasks: List[Dict[str, object]], tried: set[Tuple[Tuple[int, ...], str]]) -> int:
    for idx, task in enumerate(tasks):
        key = (tuple(task["nc"]), str(task["seed_name"]))
        if key not in tried:
            return idx
    return 0


def deterministic_review(candidate: Dict[str, object], best_result: Optional[Dict[str, object]]) -> Dict[str, object]:
    if best_result and candidate["nc"] == best_result.get("nc") and candidate["seed_name"] == best_result.get("seed_name"):
        return {
            "decision": "reject",
            "reason": "Already evaluated this layout and seed.",
            "priority_updates": ["Avoid duplicate nc/seed evaluations unless bounds or fidelity changed."],
        }
    return {
        "decision": "approve",
        "reason": "Candidate is within current bounds and still untested.",
        "priority_updates": ["Continue feasibility-first screening, then rank by productivity among low-violation runs."],
    }


def rank_any_results(results: List[Dict[str, object]]) -> List[Dict[str, object]]:
    ranked = sorted(results, key=search_score, reverse=True)
    for idx, item in enumerate(ranked, start=1):
        item["rank_any"] = idx
    return ranked


def build_search_tasks(args: argparse.Namespace) -> List[Dict[str, object]]:
    nc_library = rs.parse_nc_library(args.nc_library)
    seed_library = rs.parse_seed_library(args.seed_library)
    tasks: List[Dict[str, object]] = []
    for nc in nc_library:
        for seed in seed_library:
            tasks.append({"nc": list(nc), "seed_name": str(seed["name"]), "seed": seed})
    return tasks


def scientist_a_pick(
    client: OpenAICompatClient,
    candidate_tasks: List[Dict[str, object]],
    results: List[Dict[str, object]],
    tried: set[Tuple[Tuple[int, ...], str]],
    args: argparse.Namespace,
    objectives_excerpt: str,
    soul_excerpt: str,
    codebase_context_excerpt: str,
    research_excerpt: str,
    current_priorities: List[str],
    sqlite_context_excerpt: str,
    budget_used: float,
    iteration: int,
) -> Tuple[int, Dict[str, object]]:
    remaining = [task for task in candidate_tasks if (tuple(task["nc"]), str(task["seed_name"])) not in tried]
    shortlist = remaining[: min(len(remaining), 8)]
    default_index = deterministic_select(candidate_tasks, tried)
    if not shortlist:
        return default_index, {"mode": "deterministic", "reason": "No remaining tasks."}

    best = rank_any_results(results)[0] if results else None
    prompt = textwrap.dedent(
        f"""
        You are Scientist_A for an SMB optimization benchmark.
        Objective summary:
        {objectives_excerpt}

        Scientist rules summary:
        {soul_excerpt}

        Codebase context summary:
        {codebase_context_excerpt}

        Current research log tail:
        {research_excerpt}

        Current priority board:
        {json.dumps(current_priorities, indent=2)}

        Historical simulation context (queried from SQLite):
        {sqlite_context_excerpt}

        Counted benchmark budget is 5.0 SMB hours with 4.0 search hours and 1.0 validation hour.
        Search wall-hours used so far: {budget_used:.4f}

        Current best result:
        {summarize_result(best) if best else "None yet."}

        Remaining candidate shortlist:
        {json.dumps(shortlist, indent=2)}

        Respond with JSON only:
        {{
          "candidate_index": <0-based index into shortlist>,
          "reason": "<brief reason>",
          "fidelity": "medium",
          "priority_updates": ["..."],
          "proposed_followups": ["..."]
        }}
        """
    ).strip()
    raw = client.chat(
        "You are a concise optimization scientist. Return JSON only.",
        prompt,
        conversation_role="scientist_a_pick",
        metadata={
            "iteration": iteration,
            "search_hours_used": budget_used,
            "shortlist_size": len(shortlist),
            "remaining_count": len(remaining),
            "tried_count": len(tried),
        },
    )
    data = client.extract_json(raw)
    if data and isinstance(data.get("candidate_index"), int):
        idx = int(data["candidate_index"])
        if 0 <= idx < len(shortlist):
            chosen = shortlist[idx]
            absolute_idx = candidate_tasks.index(chosen)
            return absolute_idx, {"mode": "llm", "llm_backend": client.last_backend, "raw": raw, **data}
    return default_index, {
        "mode": "deterministic",
        "reason": "Falling back to deterministic candidate choice.",
        "priority_updates": [
            "Use deterministic task order when model output is unavailable; collect more observations before strategy changes."
        ],
    }


def scientist_b_review(
    client: OpenAICompatClient,
    task: Dict[str, object],
    best_result: Optional[Dict[str, object]],
    args: argparse.Namespace,
    codebase_context_excerpt: str,
    research_excerpt: str,
    current_priorities: List[str],
    sqlite_context_excerpt: str,
    iteration: int,
) -> Dict[str, object]:
    default = deterministic_review(task, best_result)
    prompt = textwrap.dedent(
        f"""
        You are Scientist_B. Review this proposed SMB medium-fidelity optimization attempt.
        Proposed task:
        {json.dumps(task, indent=2)}

        Current best result:
        {summarize_result(best_result) if best_result else "None yet."}

        Codebase context summary:
        {codebase_context_excerpt}

        Current research log tail:
        {research_excerpt}

        Current priority board:
        {json.dumps(current_priorities, indent=2)}

        Historical simulation context (queried from SQLite):
        {sqlite_context_excerpt}

        Hard bounds include:
        - F1 in {args.f1_bounds}
        - Ffeed, Fdes, Fex, Fraf in {args.ffeed_bounds}, {args.fdes_bounds}, {args.fex_bounds}, {args.fraf_bounds}
        - tstep in {args.tstep_bounds}

        Respond with JSON only:
        {{
          "decision": "approve" or "reject",
          "reason": "<brief reason>",
          "priority_updates": ["..."],
          "risk_flags": ["..."]
        }}
        """
    ).strip()
    raw = client.chat(
        "You are a skeptical numerical scientist. Return JSON only.",
        prompt,
        conversation_role="scientist_b_review",
        metadata={
            "iteration": iteration,
            "candidate_nc": task.get("nc"),
            "candidate_seed_name": task.get("seed_name"),
            "has_best_result": best_result is not None,
        },
    )
    data = client.extract_json(raw)
    if data and str(data.get("decision", "")).lower() in {"approve", "reject"}:
        return {"mode": "llm", "llm_backend": client.last_backend, "raw": raw, **data}
    return {"mode": "deterministic", **default}


def execute_search_task(args: argparse.Namespace, task: Dict[str, object]) -> Dict[str, object]:
    base = configure_stage_args(make_stage_args("optimize-layouts"), args)
    tstep_bounds = rs.parse_bounds(base.tstep_bounds)
    ffeed_bounds = rs.parse_bounds(base.ffeed_bounds)
    fdes_bounds = rs.parse_bounds(base.fdes_bounds)
    fex_bounds = rs.parse_bounds(base.fex_bounds)
    fraf_bounds = rs.parse_bounds(base.fraf_bounds)
    f1_bounds = rs.parse_bounds(base.f1_bounds)
    candidate_args = rs.apply_seed_to_args(
        base,
        task["seed"],
        tstep_bounds=tstep_bounds,
        ffeed_bounds=ffeed_bounds,
        fdes_bounds=fdes_bounds,
        fex_bounds=fex_bounds,
        fraf_bounds=fraf_bounds,
        f1_bounds=f1_bounds,
    )
    candidate_args.run_name = f"{args.run_name}_search_nc_{'-'.join(str(v) for v in task['nc'])}_{candidate_args.seed_name}"
    return rs.evaluate_optimized_layout(candidate_args, tuple(task["nc"]))


def build_validation_candidates(results: List[Dict[str, object]], max_items: int) -> List[Dict[str, object]]:
    ranked = rank_any_results(results)
    selected: List[Dict[str, object]] = []
    seen: set[Tuple[Tuple[int, ...], float, float, float, float, float]] = set()
    for item in ranked:
        flow = effective_flow(item)
        if flow is None:
            continue
        key = (
            tuple(item["nc"]),
            flow["Ffeed"],
            flow["F1"],
            flow["Fdes"],
            flow["Fex"],
            flow["tstep"],
        )
        if key in seen:
            continue
        seen.add(key)
        selected.append(item)
        if len(selected) >= max_items:
            break
    return selected


def execute_validation(args: argparse.Namespace, result: Dict[str, object], ordinal: int) -> Dict[str, object]:
    flow = effective_flow(result)
    if flow is None:
        raise RuntimeError("Validation candidate does not expose a usable flow.")
    base = configure_stage_args(make_stage_args("reference-eval"), args)
    base.run_name = f"{args.run_name}_validate_{ordinal:02d}"
    base.nc = ",".join(str(v) for v in result["nc"])
    base.nfex = 10
    base.nfet = 5
    base.ncp = 2
    base.ffeed = flow["Ffeed"]
    base.f1 = flow["F1"]
    base.fdes = flow["Fdes"]
    base.fex = flow["Fex"]
    base.fraf = flow["Fraf"]
    base.tstep = flow["tstep"]
    return rs.evaluate_candidate(base, tuple(result["nc"]))


def artifact_path(args: argparse.Namespace) -> Path:
    job_id = os.environ.get("SLURM_JOB_ID", "local")
    return Path(args.artifact_dir) / f"agent-runner.{job_id}.{args.run_name}.json"


def conversation_log_path(args: argparse.Namespace) -> Path:
    if args.conversation_log:
        return Path(args.conversation_log)
    job_id = os.environ.get("SLURM_JOB_ID", "local")
    return Path(args.artifact_dir) / f"agent-runner.{job_id}.{args.run_name}.conversations.json"


def conversation_stream_log_path(args: argparse.Namespace, conversation_path: Path) -> Path:
    if args.conversation_stream_log:
        return Path(args.conversation_stream_log)
    if conversation_path.suffix:
        return conversation_path.with_suffix(".jsonl")
    return Path(str(conversation_path) + ".jsonl")


def initialize_conversation_stream(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")


def write_artifact(path: Path, payload: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="ascii")


def write_conversation_log(path: Path, payload: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    artifact = artifact_path(args)
    conversation_artifact = conversation_log_path(args)
    conversation_stream_artifact = conversation_stream_log_path(args, conversation_artifact)
    research_path = Path(args.research_md)
    objectives_excerpt = read_doc_excerpt(args.objectives_file, max_chars=5000)
    soul_excerpt = read_doc_excerpt(args.llm_soul_file, max_chars=4000)
    ipopt_excerpt = read_doc_excerpt(args.ipopt_resource_file, max_chars=2500)
    client = OpenAICompatClient(
        args.llm_base_url,
        args.llm_model,
        args.llm_enabled,
        api_key=args.llm_api_key,
        fallback_enabled=args.fallback_llm_enabled,
        fallback_base_url=args.fallback_llm_base_url,
        fallback_model=args.fallback_llm_model,
        fallback_api_key=args.fallback_llm_api_key,
        conversation_stream_path=conversation_stream_artifact,
    )
    sqlite_conn = open_sqlite_db(args.sqlite_db)
    optimize_stage_args = configure_stage_args(make_stage_args("optimize-layouts"), args)
    code_context = build_codebase_context()
    code_context_excerpt = codebase_context_text(code_context)

    search_results: List[Dict[str, object]] = []
    validation_results: List[Dict[str, object]] = []
    scientist_a_log: List[Dict[str, object]] = []
    scientist_b_log: List[Dict[str, object]] = []
    ledger: List[Dict[str, object]] = []
    tried: set[Tuple[Tuple[int, ...], str]] = set()

    try:
        initialize_conversation_stream(conversation_stream_artifact)
        if args.reset_research_section:
            reset_research_run_section(research_path, args.run_name)
        initial_sqlite_excerpt = sqlite_history_context(sqlite_conn)
        initial_plan = initial_priority_plan(
            client,
            args,
            objectives_excerpt,
            soul_excerpt,
            code_context_excerpt,
            initial_sqlite_excerpt,
        )
        current_priorities = normalize_text_list(initial_plan.get("priorities"), max_items=16)
        start_research_log(
            research_path,
            args,
            code_context_excerpt,
            initial_plan,
            initial_sqlite_excerpt,
            sqlite_layout_trend_table(sqlite_conn),
        )

        solver_check = rs.run_solver_check(configure_stage_args(make_stage_args("solver-check"), args))
        search_tasks = build_search_tasks(args)
        search_hours_used = 0.0
        validation_hours_used = 0.0
        search_iteration = 0

        while (
            len(tried) < len(search_tasks)
            and len(search_results) < args.max_search_evals
            and search_hours_used < args.search_hours
        ):
            search_iteration += 1
            sqlite_excerpt = sqlite_history_context(sqlite_conn)
            research_excerpt = read_research_tail(research_path, args.research_tail_chars)
            idx, a_note = scientist_a_pick(
                client,
                search_tasks,
                search_results,
                tried,
                optimize_stage_args,
                objectives_excerpt,
                soul_excerpt,
                code_context_excerpt,
                research_excerpt,
                current_priorities,
                sqlite_excerpt,
                search_hours_used,
                search_iteration,
            )
            task = search_tasks[idx]
            task_key = (tuple(task["nc"]), str(task["seed_name"]))
            if task_key in tried:
                break
            scientist_a_log.append({"task": task, "decision": a_note})

            best_so_far = rank_any_results(search_results)[0] if search_results else None
            b_note = scientist_b_review(
                client,
                task,
                best_so_far,
                optimize_stage_args,
                code_context_excerpt,
                research_excerpt,
                current_priorities,
                sqlite_excerpt,
                search_iteration,
            )
            scientist_b_log.append({"task": task, "decision": b_note})
            current_priorities = merge_priority_board(current_priorities, a_note, b_note)
            append_iteration_research(research_path, search_iteration, task, a_note, b_note)
            tried.add(task_key)
            if str(b_note.get("decision", "approve")).lower() != "approve":
                append_research(
                    research_path,
                    f"- search_result_run: skipped_by_scientist_b at {utc_now_text()} for task={task}\n",
                )
                continue

            result = execute_search_task(args, task)
            search_results.append(result)
            persist_result_to_sqlite(sqlite_conn, args.run_name, "search", result)
            append_result_research(research_path, result, "search")
            append_research(
                research_path,
                "\n#### Insights and Trends Update\n"
                f"- timestamp_utc: {utc_now_text()}\n"
                + sqlite_layout_trend_table(sqlite_conn)
                + "\n",
            )
            ledger.append(
                {
                    "phase": "search",
                    "run_name": result.get("run_name"),
                    "status": result.get("status"),
                    "timing": result.get("timing"),
                }
            )
            timing = result.get("timing") or {}
            search_hours_used += float(timing.get("wall_seconds", 0.0)) / 3600.0

        validation_pool = build_validation_candidates(search_results, args.max_validations)
        for ordinal, candidate in enumerate(validation_pool, start=1):
            if validation_hours_used >= args.validation_hours:
                break
            validation = execute_validation(args, candidate, ordinal)
            validation_results.append(validation)
            persist_result_to_sqlite(sqlite_conn, args.run_name, "validation", validation)
            append_result_research(research_path, validation, "validation")
            append_research(
                research_path,
                "\n#### Insights and Trends Update\n"
                f"- timestamp_utc: {utc_now_text()}\n"
                + sqlite_layout_trend_table(sqlite_conn)
                + "\n",
            )
            ledger.append(
                {
                    "phase": "validation",
                    "source_run": candidate.get("run_name"),
                    "run_name": validation.get("run_name"),
                    "status": validation.get("status"),
                    "timing": validation.get("timing"),
                }
            )
            timing = validation.get("timing") or {}
            validation_hours_used += float(timing.get("wall_seconds", 0.0)) / 3600.0

        ranked_search = rank_any_results(search_results) if search_results else []
        ranked_validation = rs.rank_results([item for item in validation_results if item.get("status") == "ok"]) if validation_results else []
        final_best = ranked_validation[0] if ranked_validation else (ranked_search[0] if ranked_search else None)
        append_final_research(research_path, final_best, ranked_search, ranked_validation)

        payload = {
            "status": "ok",
            "run_name": args.run_name,
            "mode": "llm-assisted" if (client.enabled or client.fallback_enabled) else "deterministic-fallback",
            "llm": {
                "primary_enabled": client.enabled,
                "primary_base_url": args.llm_base_url,
                "primary_model": args.llm_model,
                "fallback_enabled": client.fallback_enabled,
                "fallback_base_url": args.fallback_llm_base_url if client.fallback_enabled else "",
                "fallback_model": args.fallback_llm_model if client.fallback_enabled else "",
                "last_backend_used": client.last_backend,
            },
            "llm_conversations": {
                "path": str(conversation_artifact.resolve()),
                "stream_path": str(conversation_stream_artifact.resolve()),
                "count": len(client.conversations),
            },
            "benchmark_budget": {
                "total_hours": args.benchmark_hours,
                "search_hours": args.search_hours,
                "validation_hours": args.validation_hours,
                "search_hours_used": search_hours_used,
                "validation_hours_used": validation_hours_used,
            },
            "compute_summary": os.environ.get("SMB_COMPUTE_SUMMARY", ""),
            "solver_check": solver_check,
            "docs": {
                "objectives_file": args.objectives_file,
                "llm_soul_file": args.llm_soul_file,
                "ipopt_resource_file": args.ipopt_resource_file,
                "objectives_excerpt": objectives_excerpt,
                "llm_soul_excerpt": soul_excerpt,
                "ipopt_resource_excerpt": ipopt_excerpt,
            },
            "sqlite": {
                "db_path": str(Path(args.sqlite_db).resolve()),
                "record_count": sqlite_record_count(sqlite_conn),
            },
            "research": {
                "path": str(research_path.resolve()),
                "tail_excerpt": read_research_tail(research_path, min(args.research_tail_chars, 3000)),
                "initial_plan": initial_plan,
                "current_priorities": current_priorities,
                "layout_trends_current": sqlite_layout_trend_table(sqlite_conn),
            },
            "codebase_context": code_context,
            "scientist_a_log": scientist_a_log,
            "scientist_b_log": scientist_b_log,
            "search_results": search_results,
            "validation_results": validation_results,
            "ranked_search_results": ranked_search,
            "ranked_validation_results": ranked_validation,
            "best_result": final_best,
            "ledger": ledger,
        }
        write_conversation_log(
            conversation_artifact,
            {
                "status": "ok",
                "run_name": args.run_name,
                "generated_at_utc": utc_now_text(),
                "llm": {
                    "primary_enabled": client.enabled,
                    "primary_base_url": args.llm_base_url,
                    "primary_model": args.llm_model,
                    "fallback_enabled": client.fallback_enabled,
                    "fallback_base_url": args.fallback_llm_base_url if client.fallback_enabled else "",
                    "fallback_model": args.fallback_llm_model if client.fallback_enabled else "",
                },
                "stream_path": str(conversation_stream_artifact.resolve()),
                "conversations": client.conversations,
            },
        )
        write_artifact(artifact, payload)
        print(json.dumps({"artifact": str(artifact), "status": "ok", "run_name": args.run_name}, indent=2))
        return 0
    except Exception as exc:
        try:
            write_conversation_log(
                conversation_artifact,
                {
                    "status": "error",
                    "run_name": args.run_name,
                    "generated_at_utc": utc_now_text(),
                    "error": str(exc),
                    "stream_path": str(conversation_stream_artifact.resolve()),
                    "conversations": client.conversations,
                },
            )
        except Exception:
            pass
        payload = {
            "status": "error",
            "run_name": args.run_name,
            "error": str(exc),
            "traceback": traceback.format_exc(),
            "llm_conversations": {
                "path": str(conversation_artifact.resolve()),
                "stream_path": str(conversation_stream_artifact.resolve()),
                "count": len(client.conversations),
            },
        }
        write_artifact(artifact, payload)
        print(json.dumps({"artifact": str(artifact), "status": "error", "run_name": args.run_name}, indent=2))
        return 1
    finally:
        sqlite_conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
