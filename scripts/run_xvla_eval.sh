#!/usr/bin/env bash
# Usage: MODEL_PATH=... BASE_URL=... RUN_ID=... TOKEN=... \
#        WORKER_IDS=0,1,2,3 ./EBench/scripts/run_xvla_eval.sh
# Multi-host: share RUN_ID across hosts, give each host a disjoint WORKER_IDS slice.

set -uo pipefail

RUN_PY="$(cd "$(dirname "$0")/.." && pwd)/baselines/X-VLA/run.py"
LOG_DIR="${LOG_DIR:-log_dir/$(date +%Y%m%d_%H%M%S)-${RUN_ID}}"
STEP_MODE="${STEP_MODE:-chunk}"
mkdir -p "$LOG_DIR"
echo "[run_xvla_eval] logs -> $LOG_DIR"
echo "[run_xvla_eval] step_mode=$STEP_MODE"

pids=()

cleanup() {
    local rc="${1:-0}"
    trap - INT TERM EXIT
    # Gather workers and any of their descendants.
    local alive=()
    for p in "${pids[@]:-}"; do
        kill -0 "$p" 2>/dev/null && alive+=("$p")
    done
    if (( ${#alive[@]} )); then
        echo "[run_xvla_eval] cleanup: TERM ${alive[*]}"
        # Kill descendants first (e.g. CUDA helper threads spawned by python)
        for p in "${alive[@]}"; do pkill -TERM -P "$p" 2>/dev/null || true; done
        kill -TERM "${alive[@]}" 2>/dev/null || true
        for _ in $(seq 1 20); do
            local still=0
            for p in "${alive[@]}"; do kill -0 "$p" 2>/dev/null && still=1; done
            (( still == 0 )) && break
            sleep 0.5
        done
        for p in "${alive[@]}"; do
            if kill -0 "$p" 2>/dev/null; then
                pkill -KILL -P "$p" 2>/dev/null || true
                kill -KILL "$p" 2>/dev/null || true
            fi
        done
    fi
    exit "$rc"
}
trap 'cleanup 130' INT TERM
trap 'cleanup "$?"' EXIT



for wid in ${WORKER_IDS//,/ }; do
    log="$LOG_DIR/worker_${wid}.log"
    python -u "$RUN_PY" \
        --model_path "$MODEL_PATH" \
        --base_url  "$BASE_URL" \
        --run_id    "$RUN_ID" \
        --token     "$TOKEN" \
        --worker_id "$wid" \
        --step_mode "$STEP_MODE" \
        > "$log" 2>&1 &
    pids+=($!)
    echo "[run_xvla_eval] worker=$wid pid=$! log=$log"
done

rc=0
for pid in "${pids[@]}"; do
    wait "$pid" || rc=$?
done
if (( rc != 0 )); then
    echo "[run_xvla_eval] one or more workers failed (rc=$rc); tailing logs:"
    for f in "$LOG_DIR"/worker_*.log; do echo "===== $f ====="; tail -n 30 "$f"; done
fi
exit "$rc"
