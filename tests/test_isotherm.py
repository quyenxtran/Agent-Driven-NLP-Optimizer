"""
Tests for sembasmb.isotherm — isotherm parameter lookup.
"""

import sys
import pytest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from sembasmb.isotherm import IsothermParams, get_isotherm_params


class TestIsothermParams:
    def test_is_frozen_dataclass(self):
        params = IsothermParams(qm=(1.0,), K=(2.0,), H=(3.0,))
        with pytest.raises((AttributeError, TypeError)):
            params.qm = (9.9,)

    def test_fields_are_tuples(self):
        params = get_isotherm_params("MLL")
        assert isinstance(params.qm, tuple)
        assert isinstance(params.K, tuple)
        assert isinstance(params.H, tuple)


class TestGetIsothermParams:
    def test_mll_returns_four_components(self):
        p = get_isotherm_params("MLL")
        assert len(p.qm) == 4
        assert len(p.K) == 4
        assert len(p.H) == 4

    def test_mlle_returns_four_components(self):
        p = get_isotherm_params("MLLE")
        assert len(p.qm) == 4
        assert len(p.K) == 4
        assert len(p.H) == 4

    def test_linear_returns_three_components(self):
        p = get_isotherm_params("L")
        assert len(p.qm) == 3
        assert len(p.K) == 3
        assert len(p.H) == 3

    def test_unknown_raises_value_error(self):
        with pytest.raises(ValueError):
            get_isotherm_params("NONEXISTENT")

    def test_mll_all_positive_values(self):
        p = get_isotherm_params("MLL")
        assert all(v > 0 for v in p.qm)
        assert all(v > 0 for v in p.K)
        assert all(v > 0 for v in p.H)

    def test_mlle_all_positive_values(self):
        p = get_isotherm_params("MLLE")
        assert all(v > 0 for v in p.qm)
        assert all(v > 0 for v in p.K)
        assert all(v > 0 for v in p.H)

    def test_mll_and_mlle_differ(self):
        p_mll = get_isotherm_params("MLL")
        p_mlle = get_isotherm_params("MLLE")
        # They may share qm/K but differ in H bounds by definition
        assert p_mll != p_mlle

    def test_deterministic(self):
        """Same call returns same values every time."""
        assert get_isotherm_params("MLL") == get_isotherm_params("MLL")
        assert get_isotherm_params("L") == get_isotherm_params("L")
