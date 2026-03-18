"""
Tests for sembasmb.config — SMBConfig, FlowRates, SMBInputs, build_inputs.
"""

import sys
import pytest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from sembasmb.config import SMBConfig, FlowRates, SMBInputs, build_inputs


class TestSMBConfigDefaults:
    def test_instantiates_with_no_args(self):
        cfg = SMBConfig()
        assert cfg is not None

    def test_default_nc(self):
        cfg = SMBConfig()
        assert cfg.nc == (2, 2, 2, 2)

    def test_default_components(self):
        cfg = SMBConfig()
        assert cfg.comps == ("GA", "MA", "Water", "MeOH")

    def test_default_discretization(self):
        cfg = SMBConfig()
        assert cfg.nfex == 10
        assert cfg.nfet == 5
        assert cfg.ncp == 2

    def test_default_isotherm_type(self):
        cfg = SMBConfig()
        # Attribute is named 'isoth' not 'isth'
        assert cfg.isoth == "MLL"

    def test_is_frozen(self):
        cfg = SMBConfig()
        with pytest.raises((AttributeError, TypeError)):
            cfg.nfex = 99

    def test_custom_nc(self):
        cfg = SMBConfig(nc=(1, 2, 3, 2))
        assert cfg.nc == (1, 2, 3, 2)

    def test_custom_fidelity(self):
        cfg = SMBConfig(nfex=4, nfet=2, ncp=1)
        assert cfg.nfex == 4
        assert cfg.nfet == 2
        assert cfg.ncp == 1


class TestFlowRates:
    def test_instantiates_required_fields(self):
        f = FlowRates(F1=2.2, Fdes=1.2, Fex=0.9, Ffeed=1.3)
        assert f.F1 == 2.2
        assert f.Fdes == 1.2

    def test_is_frozen(self):
        f = FlowRates(F1=2.2, Fdes=1.2, Fex=0.9, Ffeed=1.3)
        with pytest.raises((AttributeError, TypeError)):
            f.F1 = 99.0

    def test_optional_fraf_defaults_none(self):
        f = FlowRates(F1=2.2, Fdes=1.2, Fex=0.9, Ffeed=1.3)
        assert f.Fraf is None

    def test_to_dict_contains_required_keys(self):
        f = FlowRates(F1=2.2, Fdes=1.2, Fex=0.9, Ffeed=1.3)
        d = f.to_dict()
        assert isinstance(d, dict)
        assert "F1" in d
        assert "Fdes" in d
        assert "Fex" in d
        assert "Ffeed" in d

    def test_to_dict_values_match(self):
        f = FlowRates(F1=2.2, Fdes=1.2, Fex=0.9, Ffeed=1.3, Fraf=1.6)
        d = f.to_dict()
        assert d["F1"] == 2.2
        assert d["Fraf"] == 1.6


class TestBuildInputs:
    def setup_method(self):
        self.cfg = SMBConfig(nc=(1, 2, 3, 2), nfex=4, nfet=2, ncp=1)

    def test_returns_smb_inputs(self):
        inp = build_inputs(self.cfg)
        assert isinstance(inp, SMBInputs)

    def test_nc_matches_config(self):
        inp = build_inputs(self.cfg)
        assert inp.nc == (1, 2, 3, 2)

    def test_ncols_is_sum_of_nc(self):
        inp = build_inputs(self.cfg)
        assert inp.ncols == sum(self.cfg.nc)

    def test_nsec_is_four(self):
        inp = build_inputs(self.cfg)
        assert inp.nsec == 4

    def test_ncomp_matches_comps(self):
        inp = build_inputs(self.cfg)
        assert inp.ncomp == len(self.cfg.comps)

    def test_area_is_positive(self):
        inp = build_inputs(self.cfg)
        assert inp.area > 0

    def test_eb_matches_config(self):
        inp = build_inputs(self.cfg)
        assert inp.eb == self.cfg.eb

    def test_velocities_are_positive(self):
        inp = build_inputs(self.cfg)
        assert inp.u_f > 0
        assert inp.u_d > 0
        assert inp.u_e > 0
        assert inp.u_r > 0

    def test_isotherm_dicts_have_correct_length(self):
        inp = build_inputs(self.cfg)
        ncomp = len(self.cfg.comps)
        assert len(inp.dict_kapp) == ncomp
        assert len(inp.dict_qm) == ncomp
        assert len(inp.dict_K) == ncomp
        assert len(inp.dict_H) == ncomp

    def test_custom_flow_rates_applied(self):
        flow = FlowRates(F1=3.0, Fdes=1.5, Fex=1.0, Ffeed=1.8)
        inp = build_inputs(self.cfg, flow)
        # Velocities are flow/area, so if flow changed, u_f != default
        inp_default = build_inputs(self.cfg)
        assert inp.u_f != inp_default.u_f

    def test_dict_CF_uses_integer_keys(self):
        # dict_CF is keyed by component index (1-based int), not component name string
        inp = build_inputs(self.cfg)
        ncomp = len(self.cfg.comps)
        for i in range(1, ncomp + 1):
            assert i in inp.dict_CF

    def test_tstep_positive(self):
        inp = build_inputs(self.cfg)
        assert inp.tstep > 0
