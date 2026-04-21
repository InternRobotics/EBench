#!/usr/bin/env bash
# Usage: MODEL_PATH=... BASE_URL=... RUN_ID=... TOKEN=... \
#        WORKER_IDS=0,1,2,3 ./EBench/scripts/run_xvla_eval.sh
# Multi-host: share RUN_ID across hosts, give each host a disjoint WORKER_IDS slice.

set -uo pipefail

RUN_PY="$(cd "$(dirname "$0")/.." && pwd)/baselines/X-VLA/run.py"
LOG_DIR="${LOG_DIR:-log_dir/$(date +%Y%m%d_%H%M%S)-${RUN_ID}}"
mkdir -p "$LOG_DIR"
echo "[run_xvla_eval] logs -> $LOG_DIR"

pids=()
trap 'kill "${pids[@]}" 2>/dev/null; exit 130' INT TERM

for wid in ${WORKER_IDS//,/ }; do
    log="$LOG_DIR/worker_${wid}.log"
    python -u "$RUN_PY" \
        --model_path "$MODEL_PATH" \
        --base_url  "$BASE_URL" \
        --run_id    "$RUN_ID" \
        --token     "$TOKEN" \
        --worker_id "$wid" \
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
