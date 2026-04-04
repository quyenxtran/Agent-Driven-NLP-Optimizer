#!/bin/bash
# Two-scientist SMB optimization job with Qwen3.5-35B via llama.cpp
#
# Model: Qwen3.5-35B-A3B-Claude-4.6-Opus-Reasoning-Distilled (Q3_K_M, 15.6 GB)
# Backend: llama.cpp with OpenAI-compatible API
#
# Suggested submissions:
# sbatch pace_smb_two_scientists_qwen35b_llamacpp.slurm

#SBATCH --job-name=smb-qwen35b-llamacpp
#SBATCH -A gts-sn73
#SBATCH --qos=inferno
#SBATCH -p gpu-rtx6000
#SBATCH --gres=gpu:rtx_6000:1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=6
#SBATCH --mem=48G
#SBATCH --time=12:00:00
#SBATCH --mail-user=qtran47@gatech.edu
#SBATCH --mail-type=END,FAIL
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${SLURM_SUBMIT_DIR:-$SCRIPT_DIR}"
cd "$REPO_ROOT"

# ═══════════════════════════════════════════════════════════════════════════
# 1. ENVIRONMENT & PATHS
# ═══════════════════════════════════════════════════════════════════════════

# Load CUDA modules (required for GPU library access)
module load cuda/12.9.1 2>/dev/null || module load cuda/12.6.1 2>/dev/null || module load cuda/12.1.1 2>/dev/null || true

# Python environment
source .venv/bin/activate

# IPOPT/MA97 Setup (proven configuration from earlier tests)
export IPOPT_STACK_ROOT="${IPOPT_STACK_ROOT:-/storage/scratch1/4/qtran47/opt/ipopt-hsl-stack}"
export IPOPT_BIN_DIR="${IPOPT_BIN_DIR:-$IPOPT_STACK_ROOT/bin}"
export IPOPT_LIB_DIR="${IPOPT_LIB_DIR:-$IPOPT_STACK_ROOT/lib}"
export OPENBLAS_LIBDIR="${OPENBLAS_LIBDIR:-/usr/local/pace-apps/manual/packages/fenics/2018/linux-rhel9-cascadelake/gcc-9.4.0/openblas-0.3.28-cg7h4gbbmohnlrdesf4ykgipgza67why/lib}"
export METIS_LIBDIR="${METIS_LIBDIR:-/usr/local/pace-apps/manual/packages/fenics/2018/linux-rhel9-cascadelake/gcc-9.4.0/metis-5.1.0-hkeiflow76hhkltiep2ghivt3jagcryz/lib}"
export PATH="$IPOPT_BIN_DIR:${REPO_ROOT}/.venv/bin:${PATH}"
export LD_LIBRARY_PATH="$IPOPT_LIB_DIR:$OPENBLAS_LIBDIR:$METIS_LIBDIR:${LD_LIBRARY_PATH:-}"
export SMB_HSL_LIB="$IPOPT_LIB_DIR/libcoinhsl.so"

# OpenMP settings
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-${SLURM_CPUS_PER_TASK:-8}}"
export OMP_DYNAMIC=FALSE
export OMP_PROC_BIND=spread
export OMP_PLACES=cores
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export PYTHONUNBUFFERED=1

# Directories
LOG_DIR="${LOG_DIR:-$REPO_ROOT/logs}"
ARTIFACT_DIR="${ARTIFACT_DIR:-$REPO_ROOT/artifacts/qwen35b_llamacpp_agent}"
mkdir -p "$LOG_DIR" "$ARTIFACT_DIR"

# ═══════════════════════════════════════════════════════════════════════════
# 2. LLAMA.CPP CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

# Model path (Q3_K_M quantization, 15.6 GB)
LLAMACPP_MODEL_PATH="${LLAMACPP_MODEL_PATH:-/storage/scratch1/4/qtran47/models/gguf/qwen35-35b/Qwen3.5-35B-A3B-Claude-4.6-Opus-Reasoning-Distilled.Q3_K_M.gguf}"

# Server configuration
LLAMACPP_PORT="${LLAMACPP_PORT:-8000}"
LLAMACPP_HOST="127.0.0.1"
LLAMACPP_BASE_URL="http://${LLAMACPP_HOST}:${LLAMACPP_PORT}/v1"
LLAMACPP_API_LOG="${LOG_DIR}/llamacpp-qwen35b-${SLURM_JOB_ID:-local}.log"

# GPU configuration
LLAMACPP_GPU_ID="${LLAMACPP_GPU_ID:-0}"
LLAMACPP_N_GPU_LAYERS="${LLAMACPP_N_GPU_LAYERS:-100}"  # 35B model, more layers
LLAMACPP_CTX_SIZE="${LLAMACPP_CTX_SIZE:-8192}"
LLAMACPP_BATCH_SIZE="${LLAMACPP_BATCH_SIZE:-512}"
LLAMACPP_N_THREADS="${LLAMACPP_N_THREADS:-6}"

# ═══════════════════════════════════════════════════════════════════════════
# 3. LLAMA.CPP SERVER MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════

LOCAL_LLM_PID=""

cleanup_llamacpp() {
  if [[ -n "${LOCAL_LLM_PID:-}" ]] && kill -0 "${LOCAL_LLM_PID}" >/dev/null 2>&1; then
    echo "[$(date '+%F %T')] STOP: llama.cpp server pid=${LOCAL_LLM_PID}"
    kill "${LOCAL_LLM_PID}" >/dev/null 2>&1 || true
    wait "${LOCAL_LLM_PID}" >/dev/null 2>&1 || true
  fi
  LOCAL_LLM_PID=""
}

trap cleanup_llamacpp EXIT

resolve_llamacpp_bin() {
  if command -v llama-server >/dev/null 2>&1; then
    command -v llama-server
    return 0
  fi
  # Check in common build locations
  if [[ -x "/usr/local/bin/llama-server" ]]; then
    echo "/usr/local/bin/llama-server"
    return 0
  fi
  # Check user's AC_Adsorption_ML build (known location)
  if [[ -x "${HOME:-}/AC_Adsorption_ML/external/llama.cpp/build/bin/llama-server" ]]; then
    echo "${HOME:-}/AC_Adsorption_ML/external/llama.cpp/build/bin/llama-server"
    return 0
  fi
  if [[ -x "${HOME:-}/llama.cpp/llama-server" ]]; then
    echo "${HOME:-}/llama.cpp/llama-server"
    return 0
  fi
  if [[ -x "${REPO_ROOT}/llama.cpp/llama-server" ]]; then
    echo "${REPO_ROOT}/llama.cpp/llama-server"
    return 0
  fi
  return 1
}

start_llamacpp_server() {
  local llamacpp_exec ready_url max_attempts prompt_payload response_file http_code

  echo "[$(date '+%F %T')] START: llama.cpp server for Qwen3.5-35B on GPU ${LLAMACPP_GPU_ID}"
  echo "  Model: ${LLAMACPP_MODEL_PATH}"
  echo "  Server: ${LLAMACPP_BASE_URL}"
  echo "  GPU layers: ${LLAMACPP_N_GPU_LAYERS}"

  if ! llamacpp_exec="$(resolve_llamacpp_bin)"; then
    echo "ERROR: llama-server not found in PATH or common locations."
    echo "  Install from: https://github.com/ggerganov/llama.cpp"
    return 1
  fi

  # Verify model file exists
  if [[ ! -f "${LLAMACPP_MODEL_PATH}" ]]; then
    echo "ERROR: Model file not found: ${LLAMACPP_MODEL_PATH}"
    return 1
  fi

  # Start llama-server
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
  echo "[$(date '+%F %T')] llama.cpp server started with PID ${LOCAL_LLM_PID}"

  # Wait for server to be ready
  ready=0
  ready_url="${LLAMACPP_BASE_URL%/}/models"
  max_attempts=60

  echo "[$(date '+%F %T')] Waiting for llama.cpp server to be ready..."
  for ((attempt=1; attempt<=max_attempts; attempt++)); do
    if curl -fsS --max-time 5 "${ready_url}" >/dev/null 2>&1; then
      ready=1
      echo "[$(date '+%F %T')] Server ready after $((attempt * 2)) seconds"
      break
    fi
    if ! kill -0 "${LOCAL_LLM_PID}" >/dev/null 2>&1; then
      echo "ERROR: llama.cpp server process died"
      break
    fi
    sleep 2
  done

  if [[ "${ready}" != "1" ]]; then
    echo "ERROR: llama.cpp server did not become ready after ${max_attempts} attempts"
    if [[ -f "${LLAMACPP_API_LOG}" ]]; then
      echo "Server log (last 50 lines):"
      tail -n 50 "${LLAMACPP_API_LOG}" || true
    fi
    cleanup_llamacpp
    return 1
  fi

  # Test inference
  echo "[$(date '+%F %T')] Testing inference with simple prompt..."
  prompt_payload='{"model":"gpt-3.5-turbo","messages":[{"role":"user","content":"ping"}],"max_tokens":10}'
  response_file="$(mktemp)"
  http_code="$(curl -sS \
    --max-time 120 \
    -o "${response_file}" \
    -w '%{http_code}' \
    -H "Content-Type: application/json" \
    -d "${prompt_payload}" \
    "${LLAMACPP_BASE_URL%/}/chat/completions" || true)"

  if [[ ! "${http_code}" =~ ^2 ]]; then
    echo "WARNING: inference test returned status ${http_code}"
    cat "${response_file}" || true
  else
    echo "[$(date '+%F %T')] Inference test successful (HTTP ${http_code})"
  fi
  rm -f "${response_file}"

  export LLAMACPP_BASE_URL="${LLAMACPP_BASE_URL}"
  export LLAMACPP_MODEL="gpt-3.5-turbo"  # API-compatible naming
  echo "[$(date '+%F %T')] READY: Qwen3.5-35B available at ${LLAMACPP_BASE_URL}"
  return 0
}

# ═══════════════════════════════════════════════════════════════════════════
# 4. START SERVER AND RUN BENCHMARK
# ═══════════════════════════════════════════════════════════════════════════

echo "═══════════════════════════════════════════════════════════════════════════"
echo "Parse SMB Two-Scientist Benchmark with Qwen3.5-35B via llama.cpp"
echo "═══════════════════════════════════════════════════════════════════════════"
echo ""
echo "Job: ${SLURM_JOB_ID:-local}"
echo "GPU: RTX 6000 (${LLAMACPP_GPU_ID})"
echo "CPUs: ${SLURM_CPUS_PER_TASK:-8}"
echo "Memory: ${SLURM_MEM:-48G}"
echo "Time: ${SLURM_TIME:-12:00:00}"
echo ""

# Start llama.cpp server
if ! start_llamacpp_server; then
  echo "FATAL: Could not start llama.cpp server"
  exit 1
fi

echo ""
echo "Starting agent benchmark..."
echo "═══════════════════════════════════════════════════════════════════════════"
echo ""

# Run the two-scientist agent benchmark
"${REPO_ROOT}/.venv/bin/python" -m benchmarks.agent_runner \
  --run-name "qwen35b_llamacpp_agent" \
  --artifact-dir "$ARTIFACT_DIR" \
  --benchmark-hours 11.0 \
  --search-hours 10.0 \
  --validation-hours 1.0 \
  --max-search-evals 100 \
  --max-validations 5 \
  --solver-name auto \
  --linear-solver ma57 \
  --llm-base-url "${LLAMACPP_BASE_URL}" \
  --llm-model "${LLAMACPP_MODEL}" \
  --llm-api-key "llamacpp"

EXIT_CODE=$?

echo ""
echo "═══════════════════════════════════════════════════════════════════════════"
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ BENCHMARK COMPLETED SUCCESSFULLY"
else
    echo "❌ BENCHMARK FAILED (exit code: $EXIT_CODE)"
fi
echo "═══════════════════════════════════════════════════════════════════════════"
echo ""
echo "Results:"
echo "  Artifacts: $ARTIFACT_DIR"
echo "  Logs: ${LLAMACPP_API_LOG}"
echo ""

exit $EXIT_CODE
