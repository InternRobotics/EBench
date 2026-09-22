---
name: ebench-integrate-policy
description: Implement or review a custom VLA policy adapter for EBench EvalClient, including observation preprocessing, action semantics, chunking, and episode resets.
---

# Integrate a policy with EBench

Resolve paths from the EBench root. Read `third_party/genmanip-client/src/genmanip_client/eval_client.py` and the closest adapter: `baselines/X-VLA/run.py`, `baselines/openpi/scripts/pi_eval_client_online.py`, or `baselines/InternVLA-A1/inference.py`. Inspect the user's policy inference API and training transforms before choosing a mapping.

## Establish the contract

Observations are keyed by string worker IDs; a worker's model observation is `obs[wid]["obs"]`. Existing adapters use:

- `video.overlook_camera_view`, `video.left_camera_view`, `video.right_camera_view`;
- `state.joints`, `state.gripper`, `state.base`, and optionally `state.ee_pose`;
- `instruction`, and `reset` for episode-boundary handling.

Verify image type, RGB ordering, shape, resize/padding, proprioception ordering, units, and normalization against training. Do not invent missing cameras or silently replace missing input with zeros. Keep checkpoint normalization and model transforms paired.

For the current r5a/lift2 joint-position adapters, the dispatched `action` orders left arm (6), left gripper (2), right arm (6), right gripper (2); `base_motion` has 3 components. The payload explicitly declares `control_type`, `is_rel`, and `base_is_rel`. Verify a different robot/control mode against its server contract rather than generalizing these dimensions.

Model outputs are **not** interchangeable:

- X-VLA rescales base/gripper channels, reorders joints/grippers, and sends absolute base motion.
- OpenPI reorders joints/grippers and differences chunk-relative base predictions into per-step deltas with `base_is_rel=True`.
- InternVLA-A1 has checkpoint statistics and an `action_mode` setting; inspect its conversion before selecting delta or absolute behavior.

Document the chosen model-to-server channel mapping, normalization, frame/units, gripper interpretation, and relative/absolute semantics. Match the checkpoint, not whichever baseline is easiest to copy.

## Implement lifecycle and chunking

Use `EvalClient.reset()` for initial observations and `step()` for execution; inspect supported single-action/chunk forms in the pinned client. Keep string worker IDs consistent. Limit deployed horizon to available predictions and reset model history, cached actions, and temporal state at each episode boundary. `done` indicates evaluation completion, not task success; use saved result metrics for success.

Never execute the remainder of an old chunk after an episode reset. For multiple workers, keep history/chunks independent and handle worker-specific resets. If a step times out, execution may already have occurred: do not blindly resend actions. Use bounded client recovery and fresh observations, discard stale actions, and record the interruption. Close the client in `finally` so recordings/results are flushed.

## Validate the adapter

Use a representative local observation or fixture to check preprocessing, finite action values, dimensions, channel order, inverse normalization, chunk-length boundaries, and reset behavior without a simulator. Include a known-value action conversion example that would expose swapped channels or incorrect delta semantics; shape-only assertions are insufficient.

Then run a small validation rollout when a server/checkpoint is available and evaluation is in scope. Inspect actual state/action traces before scaling. Deliver the adapter, concrete launch command, mapping description, and evidence distinguishing offline contract checks from live rollout validation. Keep model-specific code in its baseline/adapter directory rather than changing unrelated upstream submodules.
