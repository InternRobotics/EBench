---
name: ebench-evaluate
description: Run and monitor an EBench policy evaluation against a local GenManip server or the online service, including baseline launch commands, worker allocation, and reproducible run records.
---

# Run an EBench policy evaluation

Work from the EBench root. Read the selected baseline entry point and the relevant CLI implementation under `third_party/genmanip-client/src/genmanip_client/`. Verify installed `gmp ... --help` before relying on flags from a different revision.

## Define the run

Resolve model/checkpoint, track, split, server mode, GPU/worker budget, and output directory from the request. Use `val_train` / `val_unseen` for tuning. Run held-out `test` when requested for final evaluation; do not silently substitute a split or tune on held-out results.

Record a small manifest beside the run logs: EBench and submodule commits, local code changes, checkpoint revision/path, config and normalization source, track/split/task selection, run/task ID, worker-to-GPU mapping, action/replan horizon, start time, sanitized command, and result locations. Mark unavailable fields as unknown. Exclude tokens and signed credentials.

## Select one submission path

- **Local GenManip:** verify the actual server config path or benchmark alias, then use `gmp submit "$CONFIG_PATH" --run_id "$RUN_ID" --host "$SERVER_HOST" --port "$SERVER_PORT"`. The pinned submit CLI takes host/port, not the online platform's `--base_url`. Submission schedules jobs; it does not load the user's policy.
- **New online task:** inspect `extensions/online_cli.py`; `gmp online submit --base_url "$PLATFORM_URL" --token "$TOKEN" --model_name "$MODEL_NAME" --benchmark_set EBench --timeout 600 --print_endpoint` creates a task and waits for readiness. Choose metadata, visibility and wait budget appropriate to the user's request; 600 seconds is an example budget, not a service guarantee. Capture returned `task_id` and `endpoint`; use that task ID as the client run ID.
- **Existing online task:** reuse it. Query `gmp online ready --base_url "$PLATFORM_URL" --token "$TOKEN" --task_id "$RUN_ID"`; use its returned evaluation endpoint. A wait timeout does not prove creation failed. Inspect existing task state before retrying creation; do not create duplicate tasks while resources are pending.

The platform URL, returned evaluation endpoint, and an OpenPI model server address serve different purposes. Do not interchange them. Preserve credentials through local environment/configuration, omit them from reports, and avoid shell tracing of authenticated commands.

## Online evaluation: queue, obtain endpoint, then evaluate

For a new online evaluation, the agent should complete this sequence rather than require the user to obtain an endpoint manually. First verify the local model environment/checkpoint and obtain the platform URL and locally configured token. A new task does not need a pre-existing evaluation URL or task ID.

1. **Submit and wait in the queue.** `gmp online submit` creates the task and polls until evaluation resources are ready. Run it as a monitored process; while pending, report that the task is waiting, not evaluating. This Bash example requires `jq` and uses a configurable wait budget:

   ```bash
   set -euo pipefail
   : "${PLATFORM_URL:?Set the online platform URL}"
   : "${TOKEN:?Set the API token locally}"
   : "${MODEL_NAME:?Set the model name}"
   READY_JSON=$(gmp online submit \
     --base_url "$PLATFORM_URL" \
     --token "$TOKEN" \
     --model_name "$MODEL_NAME" \
     --model_type VLA \
     --benchmark_set EBench \
     --timeout "${QUEUE_TIMEOUT_SECONDS:-600}" \
     --print_endpoint)

   # Parse only a successful ready response; never launch with empty values.
   EVAL_URL=$(printf '%s' "$READY_JSON" | jq -er '.endpoint | strings | select(length > 0)')
   RUN_ID=$(printf '%s' "$READY_JSON" | jq -er '.task_id | strings | select(length > 0)')
   export EVAL_URL RUN_ID
   ```

   `--print_endpoint` returns a JSON object containing both `endpoint` and `task_id`, not a plain URL. If submission fails, times out, or either field is missing, stop before launching the client. A timeout may leave a task queued: recover its ID from available logs/platform state and query `gmp online ready` instead of submitting again. If its ID cannot be determined, report that uncertainty rather than create a duplicate.

2. **Save the assignment.** Record the returned task ID and endpoint in the local run metadata, excluding credentials. Use the returned task ID unchanged as `RUN_ID`; do not substitute a friendly experiment name. Keep any credential-bearing endpoint out of shared reports.
3. **Start actual model inference against the assigned endpoint.** Use the baseline commands below or the custom adapter. Pass `EVAL_URL` as the evaluation server address and `RUN_ID` as the run ID. Do not run a second `gmp submit` against the online endpoint: the online task already schedules the evaluation. For OpenPI, ensure its separate local model server is ready before launching the eval client.
4. **Monitor until evaluation completes.** Use the assigned endpoint/task ID for status and preserve the resulting logs and episode artifacts. Queue readiness only means resources are available; it does not mean the model has been evaluated.

An existing ready task starts at step 2; an existing queued task uses `gmp online ready` until ready within the chosen wait budget. Once both fields are valid, continue to evaluation within the user's request without asking them to copy the values back manually.

## Launch the real policy

`gmp eval` supplies fake actions. Use it only for an explicitly scoped connectivity smoke test, never as evidence of a checkpoint's performance.

For X-VLA, the existing wrapper accepts environment variables (here `EVAL_URL` is the evaluation endpoint):

```bash
MODEL_PATH="$CHECKPOINT" BASE_URL="$EVAL_URL" RUN_ID="$RUN_ID" \
TOKEN="$TOKEN" WORKER_IDS=0 GPU_IDS=0 LOG_DIR="$RUN_LOG_DIR" \
  bash scripts/run_xvla_eval.sh
```

For OpenPI, use the baseline README plus the actual `serve_policy.py` and `pi_eval_client_online.py` arguments; resolve the launch template's placeholders first. The current client constructs its policy adapter for `worker_ids[0]`, so launch one client process per worker rather than assuming one process drives all listed workers.

For InternVLA-A1, run `inference.py` from its baseline directory with its supported `--ckpt_path`, `--url`, `--run_id`, `--token`, and `--worker_ids` arguments. Check the implementation before relying on a wrapper mentioned only in documentation.

Across hosts, share the run ID and assign disjoint worker IDs. A GPU index is not a worker ID. Start with a small validation smoke run for a newly integrated policy before expanding to the requested budget; do not submit an extra held-out smoke run by default.

## Monitor and finish

Use `gmp status --url "$EVAL_URL" --run_id "$RUN_ID" --token "$TOKEN"` with worker logs. Distinguish waiting for resources, model loading, active steps, completed episodes, and transport failures. Bound polling/recovery to the user's time budget. Do not overwrite runs, clean results, or restart unrelated workers as routine recovery.

At completion, verify server status and expected versus saved episode coverage, not just process exit code. Capture failed/missing episodes and interruptions. Locate actual client outputs (default `client_results`, overridable by `GENMANIP_RESULT_DIR`) and server outputs separately. Report completion or partial completion, run ID, manifest/log/result paths, and any blocker. A request to run evaluation does not by itself request separate leaderboard publication.
