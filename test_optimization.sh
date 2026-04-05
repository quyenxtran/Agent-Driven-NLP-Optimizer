#!/bin/bash
# Quick test of Phase 1 optimizations without full GPU/SLURM

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

# Activate venv
source .venv/bin/activate

# Quick test with minimal time budgets
python -m benchmarks.agent_runner \
  --run-name "test_optimization_quick" \
  --artifact-dir "$REPO_ROOT/artifacts/test_optimization" \
  --benchmark-hours 0.1 \
  --search-hours 0.05 \
  --validation-hours 0.05 \
  --max-search-evals 2 \
  --max-validations 1 \
  --solver-name auto \
  --linear-solver ma97 \
  --llm-base-url "http://127.0.0.1:8000/v1" \
  --llm-model "gpt-3.5-turbo" \
  --llm-api-key "test" \
  2>&1 | tee test_optimization.log

echo ""
echo "======================================"
echo "✅ Optimization test completed!"
echo "======================================"
echo ""
echo "Check test_optimization.log for details."
echo "Metrics to verify:"
echo "  - No expensive JSON repair cycles"
echo "  - Few-shot examples in Scientist_B prompt"
echo "  - Context sizes reduced"
echo ""
