"""
Tests for sembasmb.solver — default options and availability check.

Note: solve_model() is not tested here as it requires a working IPOPT
installation. Use the manual verification steps in implementation_plan.md
for end-to-end solver testing.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from sembasmb.solver import default_ipopt_options, check_solver_available


class TestDefaultIpoptOptions:
    def test_returns_dict(self):
        opts = default_ipopt_options()
        assert isinstance(opts, dict)

    def test_contains_linear_solver(self):
        opts = default_ipopt_options()
        assert "linear_solver" in opts

    def test_contains_max_iter(self):
        opts = default_ipopt_options()
        assert "max_iter" in opts

    def test_contains_tol(self):
        opts = default_ipopt_options()
        assert "tol" in opts

    def test_max_iter_is_positive_int(self):
        opts = default_ipopt_options()
        assert isinstance(opts["max_iter"], int)
        assert opts["max_iter"] > 0

    def test_tol_is_positive_float(self):
        opts = default_ipopt_options()
        assert isinstance(opts["tol"], float)
        assert opts["tol"] > 0

    def test_acceptable_tol_looser_than_tol(self):
        opts = default_ipopt_options()
        if "acceptable_tol" in opts:
            assert opts["acceptable_tol"] >= opts["tol"]

    def test_is_fresh_dict_each_call(self):
        """Mutating one result should not affect the next."""
        opts1 = default_ipopt_options()
        opts1["max_iter"] = 9999999
        opts2 = default_ipopt_options()
        assert opts2["max_iter"] != 9999999


class TestCheckSolverAvailable:
    def test_returns_bool(self):
        result = check_solver_available("ipopt")
        assert isinstance(result, bool)

    def test_nonexistent_solver_returns_false(self):
        result = check_solver_available("totally_fake_solver_xyz_123")
        assert result is False
