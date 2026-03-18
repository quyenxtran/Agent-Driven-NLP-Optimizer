"""
Tests that all public symbols from src/sembasmb are importable.

These tests validate that the package reorganization (rename from smb_*.py
to *.py, move from SembaSMB/src to src/sembasmb) did not break imports.
"""

import sys
from pathlib import Path

# Ensure src/ is on the path (mirrors how benchmarks/run_stage.py does it)
REPO_ROOT = Path(__file__).resolve().parents[1]
SMB_SRC = str(REPO_ROOT / "src")
if SMB_SRC not in sys.path:
    sys.path.insert(0, SMB_SRC)


class TestTopLevelPackageImports:
    def test_import_sembasmb_package(self):
        import sembasmb  # noqa: F401

    def test_import_SMBConfig(self):
        from sembasmb import SMBConfig  # noqa: F401

    def test_import_FlowRates(self):
        from sembasmb import FlowRates  # noqa: F401

    def test_import_SMBInputs(self):
        from sembasmb import SMBInputs  # noqa: F401

    def test_import_build_inputs(self):
        from sembasmb import build_inputs  # noqa: F401

    def test_import_build_model(self):
        from sembasmb import build_model  # noqa: F401

    def test_import_apply_discretization(self):
        from sembasmb import apply_discretization  # noqa: F401

    def test_import_solve_model(self):
        from sembasmb import solve_model  # noqa: F401

    def test_import_default_ipopt_options(self):
        from sembasmb import default_ipopt_options  # noqa: F401

    def test_import_compute_outlet_averages(self):
        from sembasmb import compute_outlet_averages  # noqa: F401

    def test_import_compute_purity_recovery(self):
        from sembasmb import compute_purity_recovery  # noqa: F401

    def test_import_plot_profiles(self):
        from sembasmb import plot_profiles  # noqa: F401

    def test_import_add_optimization(self):
        from sembasmb import add_optimization  # noqa: F401


class TestSubmoduleImports:
    def test_import_config_module(self):
        from sembasmb import config  # noqa: F401

    def test_import_model_module(self):
        from sembasmb import model  # noqa: F401

    def test_import_isotherm_module(self):
        from sembasmb import isotherm  # noqa: F401

    def test_import_metrics_module(self):
        from sembasmb import metrics  # noqa: F401

    def test_import_solver_module(self):
        from sembasmb import solver  # noqa: F401

    def test_import_discretization_module(self):
        from sembasmb import discretization  # noqa: F401

    def test_import_optimization_module(self):
        from sembasmb import optimization  # noqa: F401

    def test_import_plotting_module(self):
        from sembasmb import plotting  # noqa: F401


class TestAllExportsPresent:
    """Verify __all__ matches actual importable names."""

    def test_all_list_defined(self):
        import sembasmb
        assert hasattr(sembasmb, "__all__")

    def test_all_symbols_importable(self):
        import sembasmb
        for name in sembasmb.__all__:
            assert hasattr(sembasmb, name), (
                f"sembasmb.__all__ lists '{name}' but it is not importable"
            )
