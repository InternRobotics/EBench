---
name: ebench-debug
description: Diagnose EBench evaluation failures, stalled workers, transport errors, invalid actions, and unexpectedly low scores using logs and episode artifacts.
---

# Diagnose an EBench run

Work from the EBench root. Obtain the failing command with credentials redacted, run ID, worker ID, first relevant traceback, checkpoint/config, and whether the failure occurs during loading, readiness, reset, inference, step, or result saving. Read existing logs before rerunning anything.

## Isolate the failing layer

| Evidence | Next useful check |
| --- | --- |
| Import/config/weight failure | Active interpreter, installed package path, pinned submodules, baseline overlays, checkpoint files/statistics; server restart will not fix a local import. |
| Online task pending | Query the existing task with `gmp online ready`; distinguish scheduling from failure and retain its task ID. |
| Authentication or route failure | Distinguish platform URL from evaluation endpoint; check run ID and credential presence without printing credentials. |
| Reset timeout | Compare readiness, status and server logs if available. Asset loading and worker failure are hypotheses until supported. `EvalClient.reset()` kills/recreates its workers, so it is not a read-only probe. |
| Step timeout/disconnect | Correlate worker/server timestamps. Server execution may have completed; inspect progress before recovery and discard stale observations/chunks. |
| GPU OOM | Inspect model size, dtype and workers per GPU; reduce concurrency within scope before changing the model or evaluation protocol. |
| Implausible motion/near-zero SR | Inspect camera order, normalization, joint/gripper order, relative/absolute base semantics, replan horizon, and history reset before attributing failure to model capability. |
| Empty/missing report | Locate the actual result root, check completed episode files and writer errors; distinguish client traces from server result artifacts. |

Read `baselines/X-VLA/run.py` for bounded recovery and `third_party/genmanip-client/src/genmanip_client/eval_client.py` for current reset/step/storage behavior. Do not turn every exception into an endless reconnect loop. Stop retries when the same failure persists without new evidence, and report the unresolved cause and retained artifacts.

## Inspect one episode

For client traces, `gmp plot "$EPISODE_DIR"` reads `steps.jsonl` and `merged*.mp4`, producing action/state plots and optional merged video. Inspect these against the adapter's transformations.

For server-side results, `gmp visualize --project_root "$GENMANIP_ROOT"` uses the project's result tree. Its optional `visualize` dependencies and Rerun viewer cache are separate from model inference; the pinned README calls for Python 3.11+ for that viewer path. A viewer dependency failure does not establish that inference failed.

Preserve logs, partial results, and task/seed identifiers. `gmp clean` deletes server evaluation results and logs; do not use it as a generic repair. Avoid resetting all workers to investigate one worker. Make the smallest justified fix and rerun only the needed verification within the requested evaluation scope.

Deliver the observed symptom, evidence-backed cause (or remaining hypotheses), changed files/settings, validation outcome, and whether interrupted/partial episodes affect reported scores. Keep policy failures separate from infrastructure failures.
