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
