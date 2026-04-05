#!/bin/bash
# 27B LHS Low-Fidelity Benchmark (15 min)
# Fast validation of LHS + agent approach
# Quick smoke test before medium/high fidelity runs

#SBATCH --job-name=smb-qwen27b-lhs-lo
#SBATCH -A gts-sn73
#SBATCH --qos=inferno
#SBATCH -p gpu-rtx6000
#SBATCH --gres=gpu:rtx_6000:1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=6
#SBATCH --mem=48G
#SBATCH --time=00:30:00
#SBATCH --mail-user=qtran47@gatech.edu
#SBATCH --mail-type=END,FAIL
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${SLURM_SUBMIT_DIR:-$SCRIPT_DIR}"
cd "$REPO_ROOT"

module load cuda/12.9.1 2>/dev/null || module load cuda/12.6.1 2>/dev/null || module load cuda/12.1.1 2>/dev/null || true
source .venv/bin/activate

export IPOPT_STACK_ROOT="${IPOPT_STACK_ROOT:-/storage/scratch1/4/qtran47/opt/ipopt-hsl-stack}"
export IPOPT_BIN_DIR="${IPOPT_BIN_DIR:-$IPOPT_STACK_ROOT/bin}"
export IPOPT_LIB_DIR="${IPOPT_LIB_DIR:-$IPOPT_STACK_ROOT/lib}"
export OPENBLAS_LIBDIR="${OPENBLAS_LIBDIR:-/usr/local/pace-apps/manual/packages/fenics/2018/linux-rhel9-cascadelake/gcc-9.4.0/openblas-0.3.28-cg7h4gbbmohnlrdesf4ykgipgza67why/lib}"
export METIS_LIBDIR="${METIS_LIBDIR:-/usr/local/pace-apps/manual/packages/fenics/2018/linux-rhel9-cascadelake/gcc-9.4.0/metis-5.1.0-hkeiflow76hhkltiep2ghivt3jagcryz/lib}"
export PATH="$IPOPT_BIN_DIR:${REPO_ROOT}/.venv/bin:${PATH}"
export LD_LIBRARY_PATH="$IPOPT_LIB_DIR:$OPENBLAS_LIBDIR:$METIS_LIBDIR:${LD_LIBRARY_PATH:-}"
export SMB_HSL_LIB="$IPOPT_LIB_DIR/libcoinhsl.so"

export OMP_NUM_THREADS="${OMP_NUM_THREADS:-${SLURM_CPUS_PER_TASK:-8}}"
export OMP_DYNAMIC=FALSE
export OMP_PROC_BIND=spread
export OMP_PLACES=cores
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export PYTHONUNBUFFERED=1

LOG_DIR="${LOG_DIR:-$REPO_ROOT/logs}"
ARTIFACT_DIR="${ARTIFACT_DIR:-$REPO_ROOT/artifacts/lhs_bench_27b_low}"
mkdir -p "$LOG_DIR" "$ARTIFACT_DIR"

LLAMACPP_MODEL_PATH="${LLAMACPP_MODEL_PATH:-/storage/scratch1/4/qtran47/models/gguf/qwen35-27b/Qwen3.5-27B-Q4_K_M.gguf}"
LLAMACPP_PORT="${LLAMACPP_PORT:-8002}"
LLAMACPP_HOST="127.0.0.1"
LLAMACPP_BASE_URL="http://${LLAMACPP_HOST}:${LLAMACPP_PORT}/v1"
LLAMACPP_API_LOG="${LOG_DIR}/llamacpp-lhs-lo-${SLURM_JOB_ID:-local}.log"

LLAMACPP_GPU_ID="${LLAMACPP_GPU_ID:-0}"
LLAMACPP_N_GPU_LAYERS="${LLAMACPP_N_GPU_LAYERS:-80}"
LLAMACPP_CTX_SIZE="${LLAMACPP_CTX_SIZE:-8192}"
LLAMACPP_BATCH_SIZE="${LLAMACPP_BATCH_SIZE:-512}"
LLAMACPP_N_THREADS="${LLAMACPP_N_THREADS:-6}"

LOCAL_LLM_PID=""

cleanup_llamacpp() {
  if [[ -n "${LOCAL_LLM_PID:-}" ]] && kill -0 "${LOCAL_LLM_PID}" >/dev/null 2>&1; then
    kill "${LOCAL_LLM_PID}" >/dev/null 2>&1 || true
    wait "${LOCAL_LLM_PID}" >/dev/null 2>&1 || true
  fi
}

trap cleanup_llamacpp EXIT

resolve_llamacpp_bin() {
  command -v llama-server 2>/dev/null || \
  [[ -x "/usr/local/bin/llama-server" ]] && echo "/usr/local/bin/llama-server" || \
  [[ -x "${REPO_ROOT}/llama.cpp/llama-server" ]] && echo "${REPO_ROOT}/llama.cpp/llama-server" || \
  return 1
}

start_llamacpp_server() {
  local llamacpp_exec ready_url max_attempts

  echo "[$(date '+%F %T')] Starting llama.cpp (LHS Low-Fidelity: 15 min)"
  if ! llamacpp_exec="$(resolve_llamacpp_bin)"; then
    echo "ERROR: llama-server not found"
    return 1
  fi

  CUDA_VISIBLE_DEVICES="${LLAMACPP_GPU_ID}" \
  "${llamacpp_exec}" \
    --model "${LLAMACPP_MODEL_PATH}" \
    --port "${LLAMACPP_PORT}" \
    --n-gpu-layers "${LLAMACPP_N_GPU_LAYERS}" \
    --ctx-size "${LLAMACPP_CTX_SIZE}" \
    --batch-size "${LLAMACPP_BATCH_SIZE}" \
    --threads "${LLAMACPP_N_THREADS}" \
    --flash-attn auto \
    >"${LLAMACPP_API_LOG}" 2>&1 &

  LOCAL_LLM_PID=$!
  echo "[$(date '+%F %T')] llama.cpp PID ${LOCAL_LLM_PID}"

  ready_url="${LLAMACPP_BASE_URL%/}/models"
  max_attempts=60
  for ((attempt=1; attempt<=max_attempts; attempt++)); do
    if curl -fsS --max-time 5 "${ready_url}" >/dev/null 2>&1; then
      echo "[$(date '+%F %T')] Server ready"
      return 0
    fi
    sleep 2
  done

  echo "ERROR: Server timeout"
  return 1
}

echo "═══════════════════════════════════════════════════════════════════════════"
echo "LHS LOW-FIDELITY: 27B Agent + LHS Ranking (15 min benchmark)"
echo "═══════════════════════════════════════════════════════════════════════════"
echo "Job: ${SLURM_JOB_ID:-local}"
echo "Budget: 0.25 hours (15 min)"
echo "Config space: 31 valid (sum=8)"
echo "LHS ranking: ENABLED"
echo ""

if ! start_llamacpp_server; then
  echo "FATAL: Could not start server"
  exit 1
fi

echo "Running LHS Low-Fidelity benchmark..."
"${REPO_ROOT}/.venv/bin/python" -m benchmarks.agent_runner \
  --run-name "lhs_bench_27b_low" \
  --artifact-dir "$ARTIFACT_DIR" \
  --benchmark-hours 0.25 \
  --search-hours 0.2 \
  --validation-hours 0.05 \
  --max-search-evals 50 \
  --max-validations 2 \
  --use-lhs-ranking \
  --solver-name auto \
  --linear-solver ma97 \
  --llm-base-url "${LLAMACPP_BASE_URL}" \
  --llm-model "gpt-3.5-turbo" \
  --llm-api-key "llamacpp"

EXIT_CODE=$?

echo "═══════════════════════════════════════════════════════════════════════════"
echo "Results: $ARTIFACT_DIR"
echo "Exit: $EXIT_CODE"
echo "═══════════════════════════════════════════════════════════════════════════"

exit $EXIT_CODE
