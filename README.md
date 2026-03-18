# AutoResearch-SMB: AI-Driven Simulated Moving Bed Optimization

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://python.org)
[![Pyomo](https://img.shields.io/badge/Pyomo-6.0+-orange.svg)](https://pyomo.org)
[![IPOPT](https://img.shields.io/badge/IPOPT-3.14+-green.svg)](https://coin-or.github.io/Ipopt/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

AI-driven optimization framework for Simulated Moving Bed (SMB) chromatography. Combines a Pyomo DAE model with a three-scientist LLM agent loop to maximize organic acid (GA/MA) productivity while satisfying purity (≥60%) and recovery (≥75%) constraints.

## Installation

```bash
git clone https://github.com/your-org/AutoResearch-SMB.git
cd AutoResearch-SMB
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -e ".[dev]"          # includes pytest, ruff, mypy
```

IPOPT must be on `PATH`. Optional linear solvers: MA57, MA97, MUMPS, Pardiso (see `agents/IPOPT_SOLVER_RESOURCES.md`).

For local LLM inference, install [Ollama](https://ollama.com/) and pull a Qwen model. See `slurm/local_command.md` for PACE cluster submission commands.

## Quick Start

### Run a single optimization stage

```bash
python -m benchmarks.run_stage --help
python -m benchmarks.agent_runner --help
```

### Python API

```python
from sembasmb import SMBConfig, FlowRates, build_inputs, build_model
from sembasmb import apply_discretization, add_optimization, solve_model
from sembasmb import compute_outlet_averages, compute_purity_recovery

config = SMBConfig(nc=(1, 2, 3, 2), nfex=10, nfet=5, ncp=2)
flow   = FlowRates(F1=2.5, Fdes=1.5, Fex=1.0, Ffeed=1.2, tstep=9.4)

inputs = build_inputs(config, flow)
model  = build_model(config, inputs)
apply_discretization(model, inputs)
add_optimization(model, inputs)
results = solve_model(model, solver_name="ipopt_sens", linear_solver="ma57")
```

### Multi-fidelity ladder

| Level  | nfex | nfet | ncp | Use case |
|--------|------|------|-----|----------|
| Low    | 4–5  | 2    | 1   | Fast screening |
| Medium | 6    | 3    | 2   | Candidate refinement |
| High   | 10   | 5    | 2   | Final validation |

Never skip levels — going low → high directly risks numerical instability.

## AI Agent Architecture

Three agents share a SQLite experiment database (`smb_agent_context.sqlite`):

- **Scientist_A** (proposer) — reads `agents/` knowledge files + SQLite history, proposes next candidate
- **Scientist_B** (reviewer) — independently validates A's proposal against physics and prior data
- **Scientist_Executive** — fires when A and B deadlock, forces execution of a diagnostic run

```bash
# Two-scientist mode (recommended)
python -m benchmarks.agent_runner --single-scientist-mode 0 \
    --run-name my_run --sqlite-db artifacts/agent_runs/context.sqlite

# Single-scientist baseline
python -m benchmarks.agent_runner --single-scientist-mode 1 \
    --run-name baseline_run --sqlite-db artifacts/agent_runs/context.sqlite
```

## Knowledge Files (`agents/`)

| File | Format | Purpose |
|------|--------|---------|
| `hypotheses.json` | JSON | 11 structured hypotheses; agents append evidence after each run |
| `failures.json` | JSON | 11 failure modes; agents log errors and resolutions |
| `SKILLS.md` | Markdown | Proven physical intuition and optimization patterns |
| `Objectives.md` | Markdown | Project targets: purity ≥ 0.60, recovery GA/MA ≥ 0.75 |
| `LLM_SOUL.md` | Markdown | Agent operating principles |
| `IPOPT_SOLVER_RESOURCES.md` | Markdown | Solver configuration guide |

After each run, update `hypotheses.json` (`simulation_results[]`) and `failures.json` (`occurrences[]`) — not the deprecated `.md` versions.

## Flow Mass Balance (Critical Invariant)

```
F1 = Ffeed + Fraf      (feed zone)
F1 = Fdes  + Fex       (desorbent zone)
```

`Fraf` is derived and never optimized independently. Violating this by >1% causes solver errors or unphysical results.

## License

MIT — see [LICENSE](LICENSE).

## Citation

```bibtex
@software{autoresearch_smb_2025,
  title  = {AutoResearch-SMB: AI-Driven Simulated Moving Bed Optimization},
  author = {Tran, Q. and collaborators},
  year   = {2025},
  url    = {https://github.com/your-org/AutoResearch-SMB}
}
```
