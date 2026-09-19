#!/usr/bin/env bash
# Brings up a container-local Ollama, guarantees the configured model is
# present, then runs the requested evaluation command. Keeping the server in
# the same container means the experiments still talk to 127.0.0.1:11434
# exactly as config.yaml expects.
set -euo pipefail

HOST="http://127.0.0.1:11434"
READY_TIMEOUT="${OLLAMA_READY_TIMEOUT:-90}"
SERVE_LOG=/tmp/ollama-serve.log

log() { printf '[entrypoint] %s\n' "$*" >&2; }

# The model name comes from config.yaml so the image never disagrees with the
# committed configuration. TOOLGUARD_MODEL overrides it for one run.
MODEL="${TOOLGUARD_MODEL:-$(python3 -c 'from src.config import load_config; print(load_config()["model"]["name"])')}"

ollama serve >"$SERVE_LOG" 2>&1 &
SERVE_PID=$!
trap 'kill "$SERVE_PID" 2>/dev/null || true' EXIT

log "waiting for Ollama (model store: ${OLLAMA_MODELS})"
ready=0
for _ in $(seq "$READY_TIMEOUT"); do
    if curl -sf -o /dev/null "$HOST/api/tags"; then
        ready=1
        break
    fi
    if ! kill -0 "$SERVE_PID" 2>/dev/null; then
        log "ollama serve exited early:"
        cat "$SERVE_LOG" >&2
        exit 1
    fi
    sleep 1
done
if [ "$ready" -ne 1 ]; then
    log "Ollama was not ready within ${READY_TIMEOUT}s:"
    cat "$SERVE_LOG" >&2
    exit 1
fi

if ollama list | awk 'NR > 1 { print $1 }' | grep -qx "$MODEL"; then
    log "model ${MODEL} already in the mounted store"
else
    log "model ${MODEL} not in the mounted store; pulling it (needs network, ~4.7 GB)"
    ollama pull "$MODEL"
fi

# Start from the benign baseline no matter what state the image was built from.
# The experiment suites reset per case anyway; this makes ad-hoc `src.agent`
# runs and `shell` sessions reproducible too.
log "resetting the mock workspace to the benign baseline"
python3 -m src.workspace reset >/dev/null

reps=()
if [ -n "${TOOLGUARD_REPETITIONS:-}" ]; then
    reps=(--repetitions "$TOOLGUARD_REPETITIONS")
fi

run_suite() {
    python3 -m experiments.run_benign --backend ollama "${reps[@]}"
    python3 -m experiments.run_attacks --backend ollama "${reps[@]}"
    python3 -m experiments.run_defenses --backend ollama --mode delimited "${reps[@]}"
    python3 -m experiments.run_defenses --backend ollama --mode defended "${reps[@]}"
    python3 -m src.evaluator logs
}

case "${1:-suite}" in
    suite)
        log "running the full suite at the configured repetition count"
        run_suite
        ;;
    smoke)
        log "running a one-repetition smoke suite"
        reps=(--repetitions 1)
        run_suite
        ;;
    shell)
        log "Ollama is up and the workspace is reset. The agent is a Python module,"
        log "not a chat prompt. For example:"
        log '  python3 -m src.agent --backend ollama --mode vulnerable --prompt "Summarize my latest email."'
        log "  python3 -m experiments.run_benign --backend ollama --mode vulnerable --repetitions 1"
        exec bash
        ;;
    *)
        exec "$@"
        ;;
esac
