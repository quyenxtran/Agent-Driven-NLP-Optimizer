"""
Tests that benchmarks/agent_runner.py and benchmarks/run_stage.py
reference the correct paths after the repository reorganization.
"""

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BENCHMARKS_DIR = REPO_ROOT / "benchmarks"


def _read(fname):
    return (BENCHMARKS_DIR / fname).read_text(encoding="utf-8")


class TestAgentRunnerPaths:
    """agent_runner.py default paths must point to agents/ directory."""

    def test_objectives_file_default_points_to_agents(self):
        src = _read("agent_runner.py")
        assert 'agents" / "Objectives.md"' in src or '"agents" / "Objectives.md"' in src or \
               'agents/Objectives.md' in src or \
               '"agents", "Objectives.md"' in src, \
               "agent_runner.py --objectives-file default must reference agents/Objectives.md"

    def test_llm_soul_file_default_points_to_agents(self):
        src = _read("agent_runner.py")
        assert 'agents' in src and 'LLM_SOUL.md' in src, \
            "agent_runner.py --llm-soul-file default must reference agents/LLM_SOUL.md"

    def test_ipopt_resource_file_default_points_to_agents(self):
        src = _read("agent_runner.py")
        assert 'agents' in src and 'IPOPT_SOLVER_RESOURCES.md' in src, \
            "agent_runner.py --ipopt-resource-file default must reference agents/IPOPT_SOLVER_RESOURCES.md"

    def test_no_root_level_objectives_default(self):
        src = _read("agent_runner.py")
        # Should not reference REPO_ROOT / "Objectives.md" at root (without agents/)
        # The pattern REPO_ROOT / "Objectives.md" (without agents) should be absent
        assert 'REPO_ROOT / "Objectives.md"' not in src, \
            "agent_runner.py must not default --objectives-file to repo root"

    def test_no_root_level_llm_soul_default(self):
        src = _read("agent_runner.py")
        assert 'REPO_ROOT / "LLM_SOUL.md"' not in src, \
            "agent_runner.py must not default --llm-soul-file to repo root"

    def test_no_root_level_ipopt_resource_default(self):
        src = _read("agent_runner.py")
        assert 'REPO_ROOT / "IPOPT_SOLVER_RESOURCES.md"' not in src, \
            "agent_runner.py must not default --ipopt-resource-file to repo root"


class TestRunStagePaths:
    """run_stage.py must use src/ for its sys.path insertion."""

    def test_smb_root_points_to_src(self):
        src = _read("run_stage.py")
        assert '"src"' in src or "'src'" in src, \
            'run_stage.py must set SMB_ROOT to REPO_ROOT / "src"'

    def test_no_sembaSMB_sys_path(self):
        src = _read("run_stage.py")
        assert "SembaSMB" not in src, \
            "run_stage.py must not reference old SembaSMB/ path in sys.path"


class TestBenchmarksImportable:
    """benchmarks package itself must be importable from repo root."""

    def test_benchmarks_is_package(self):
        sys.path.insert(0, str(REPO_ROOT))
        try:
            import benchmarks  # noqa: F401
        finally:
            sys.path.pop(0)
