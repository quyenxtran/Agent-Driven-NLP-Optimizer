"""
Tests for repository structure and reorganization correctness.

Verifies that:
- agents/ directory contains all 8 MD files
- src/sembasmb/ contains all expected modules
- Old SembaSMB/ and _sembasmb_git_backup/ directories are gone
- slurm/ directory has all SLURM scripts
- Root-level MD files were removed
- pyproject.toml, requirements.txt exist at root
"""

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
AGENTS_DIR = REPO_ROOT / "agents"
SRC_DIR = REPO_ROOT / "src" / "sembasmb"
SLURM_DIR = REPO_ROOT / "slurm"


class TestAgentsDirectory:
    EXPECTED_FILES = [
        "Objectives.md",
        "LLM_SOUL.md",
        "IPOPT_SOLVER_RESOURCES.md",
        "SKILLS.md",
        "BENCHMARK_FAIRNESS.md",
        "Problem_definition.md",
        # Structured JSON replacements for the deprecated .md versions:
        "hypotheses.json",
        "failures.json",
    ]

    def test_agents_dir_exists(self):
        assert AGENTS_DIR.is_dir(), "agents/ directory must exist"

    def test_all_agent_md_files_present(self):
        for fname in self.EXPECTED_FILES:
            assert (AGENTS_DIR / fname).is_file(), f"agents/{fname} missing"

    def test_no_agent_md_files_at_root(self):
        for fname in self.EXPECTED_FILES:
            assert not (REPO_ROOT / fname).is_file(), (
                f"{fname} should not exist at repo root — should be in agents/"
            )


class TestSembaSMBPackage:
    EXPECTED_MODULES = [
        "__init__.py",
        "config.py",
        "model.py",
        "discretization.py",
        "isotherm.py",
        "metrics.py",
        "optimization.py",
        "plotting.py",
        "solver.py",
    ]

    def test_src_sembasmb_dir_exists(self):
        assert SRC_DIR.is_dir(), "src/sembasmb/ directory must exist"

    def test_all_modules_present(self):
        for fname in self.EXPECTED_MODULES:
            assert (SRC_DIR / fname).is_file(), f"src/sembasmb/{fname} missing"

    def test_no_old_smb_prefix_files(self):
        """Old smb_*.py files should not exist in src/sembasmb/."""
        old_files = list(SRC_DIR.glob("smb_*.py"))
        assert old_files == [], (
            f"Old smb_-prefixed files still exist: {old_files}"
        )


class TestOldDirectoriesDeleted:
    def test_sembasmb_dir_deleted(self):
        assert not (REPO_ROOT / "SembaSMB").exists(), (
            "SembaSMB/ should have been deleted"
        )

    def test_git_backup_deleted(self):
        assert not (REPO_ROOT / "_sembasmb_git_backup").exists(), (
            "_sembasmb_git_backup/ should have been deleted"
        )


class TestSlurmDirectory:
    EXPECTED_SCRIPTS = [
        "local_command.md",
        "pace_graph_orchestrator_dev.slurm",
        "pace_smb_comparable_3runs.slurm",
        "pace_smb_minlp_cpu_24h.slurm",
        "pace_smb_single_scientist_24h.slurm",
        "pace_smb_stage_runner.slurm",
        "pace_smb_two_scientists_24h.slurm",
        "pace_smb_two_scientists_qwen.slurm",
    ]

    def test_slurm_dir_exists(self):
        assert SLURM_DIR.is_dir(), "slurm/ directory must exist"

    def test_all_slurm_scripts_present(self):
        for fname in self.EXPECTED_SCRIPTS:
            assert (SLURM_DIR / fname).is_file(), f"slurm/{fname} missing"


class TestRootPackagingFiles:
    def test_pyproject_toml_exists(self):
        assert (REPO_ROOT / "pyproject.toml").is_file()

    def test_requirements_txt_exists(self):
        assert (REPO_ROOT / "requirements.txt").is_file()

    def test_requirements_optional_txt_exists(self):
        assert (REPO_ROOT / "requirements-optional.txt").is_file()


class TestBenchmarksPackage:
    def test_benchmarks_init_exists(self):
        assert (REPO_ROOT / "benchmarks" / "__init__.py").is_file()

    def test_agent_runner_exists(self):
        assert (REPO_ROOT / "benchmarks" / "agent_runner.py").is_file()

    def test_run_stage_exists(self):
        assert (REPO_ROOT / "benchmarks" / "run_stage.py").is_file()


class TestTestsPackage:
    def test_tests_init_exists(self):
        assert (REPO_ROOT / "tests" / "__init__.py").is_file()


class TestSlurmNoBrokenPaths:
    """Verify SLURM files no longer reference old SembaSMB paths."""

    def _read_slurm(self, fname):
        return (SLURM_DIR / fname).read_text(encoding="utf-8")

    def test_stage_runner_no_sembaSMB_dir_check(self):
        content = self._read_slurm("pace_smb_stage_runner.slurm")
        # Old detection checked for -d .../SembaSMB; new checks for src/sembasmb
        assert '-d "${REPO_ROOT}/SembaSMB"' not in content
        assert 'src/sembasmb' in content

    def test_stage_runner_smb_root_uses_src(self):
        content = self._read_slurm("pace_smb_stage_runner.slurm")
        assert 'SMB_ROOT="${AUTORESEARCH_ROOT}/src"' in content

    def test_qwen_no_sembaSMB_dir_check(self):
        content = self._read_slurm("pace_smb_two_scientists_qwen.slurm")
        assert '-d "${REPO_ROOT}/SembaSMB"' not in content
        assert 'src/sembasmb' in content

    def test_qwen_smb_root_uses_src(self):
        content = self._read_slurm("pace_smb_two_scientists_qwen.slurm")
        assert 'SMB_ROOT="${AUTORESEARCH_ROOT}/src"' in content

    def test_qwen_objectives_points_to_agents(self):
        content = self._read_slurm("pace_smb_two_scientists_qwen.slurm")
        assert 'agents/Objectives.md' in content

    def test_qwen_llm_soul_points_to_agents(self):
        content = self._read_slurm("pace_smb_two_scientists_qwen.slurm")
        assert 'agents/LLM_SOUL.md' in content

    def test_qwen_ipopt_resource_points_to_agents(self):
        content = self._read_slurm("pace_smb_two_scientists_qwen.slurm")
        assert 'agents/IPOPT_SOLVER_RESOURCES.md' in content
