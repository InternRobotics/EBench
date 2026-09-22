---
name: ebench-setup
description: Prepare or check an EBench evaluation environment for OpenPI, X-VLA, InternVLA-A1, or a custom policy. Use for first-run setup and baseline reproduction prerequisites.
---

# Prepare EBench evaluation

Resolve paths from the EBench repository root. Read `README.md`, the selected `baselines/<name>/README.md`, and `third_party/genmanip-client/pyproject.toml`. Prefer the checked-out implementation when examples disagree with it.

## Establish the execution path

- Identify the model/checkpoint, online endpoint versus locally hosted GenManip, intended track/split, and available GPUs. Reuse information already supplied; ask only for missing inputs needed for the next action.
- EBench contains adapters, not the Isaac Sim server. An online client does not need a local Isaac Sim installation. A local server requires a separate GenManip checkout and its environment/assets; inspect that checkout's instructions before proposing server commands.
- Inspect `git submodule status --recursive`, the active Python interpreter, installed package locations, GPU availability, and checkpoint existence. Initialize missing pinned submodules with `git submodule update --init --recursive` when setup is requested; do not advance them to arbitrary upstream heads.
- Install the pinned client in the selected model/client environment with `python -m pip install -e third_party/genmanip-client`. Choose `full_numpy1` or `full_numpy2` extras to match the baseline environment; do not install both. Keep incompatible baseline dependencies in separate environments.

## Baseline-specific checks

| Baseline | Source of truth | Checks that change the launch plan |
| --- | --- | --- |
| X-VLA | `baselines/X-VLA/run.py`, `scripts/run_xvla_eval.sh` | Check matching processor/checkpoint and requirements; worker IDs and GPU IDs are separate settings. |
| OpenPI | `baselines/openpi/README.md`, `baselines/openpi/src/openpi/training/config.py`, `baselines/openpi/src/openpi/policies/ebench_policy.py`, `baselines/openpi/scripts/pi_eval_client_online.py` | Apply EBench overlays together; verify the selected config actually exists and uses checkpoint-compatible normalization. Model WebSocket server and eval client have separate endpoints/environments. |
| InternVLA-A1 | `baselines/InternVLA-A1/inference.py`, `baselines/InternVLA-A1/eval_pjsim.sh` | Check upstream dependencies, checkpoint config/weights/`stats.json`, and the statistics key. Verify a documented wrapper actually exists before using it. |

`scripts/launch_pi_onlineeval.sh` contains placeholder paths, activation commands, and settings; it is a template, not a ready-to-run launcher. Inspect shell wrappers before execution. Create a concrete local launch command using the user's paths rather than running placeholders or copying another machine's paths.

## Verify and hand off

Check imports and `gmp --help` in the selected environment before allocating a full run. Inspect CLI source if imports are unavailable. A connectivity test with `gmp eval` uses fake actions and is not a model evaluation; label it accordingly and keep its run separate from reported model results.

Report the interpreter/environment, pinned revisions, model path/config, dependency gaps, and launch command with credential placeholders. Distinguish checks actually run from inferred compatibility. Do not claim readiness while weights, server access, or imports remain unverified. If asked to proceed with evaluation, continue within the existing request once prerequisites are satisfied.
