#!/usr/bin/env python

from collections import deque
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
import tyro
import cv2
from genmanip_client import EvalClient

from lerobot.configs.policies import PreTrainedConfig
from lerobot.datasets.utils import load_json
from lerobot.policies.InternVLA_A1_3B.modeling_internvla_a1 import QwenA1Config, QwenA1Policy
from lerobot.policies.InternVLA_A1_3B.transform_internvla_a1 import Qwen3_VLProcessorTransformFn
from lerobot.transforms.core import (
    NormalizeTransformFn,
    ResizeImagesWithPadFn,
    UnNormalizeTransformFn,
    compose,
)
from lerobot.utils.constants import OBS_IMAGES

def build_policy_and_transforms(ckpt_path: Path, stats_key: str, resize_size: int, dtype: torch.dtype):
    config = PreTrainedConfig.from_pretrained(ckpt_path)
    assert isinstance(config, QwenA1Config)
    policy = QwenA1Policy.from_pretrained(config=config, pretrained_name_or_path=ckpt_path)
    policy.cuda().to(dtype).eval()

    stats = load_json(ckpt_path / "stats.json")[stats_key]
    stat_keys = ["min", "max", "mean", "std"]
    state_keys = ["state.joints", "state.base" ,"state.gripper", ]
    action_keys = ["action.joints", "action.base" ,"action.gripper"]

    state_concat = {
        k: np.concatenate([np.asarray(stats[state_key][k]) for state_key in state_keys], axis=-1)
        for k in stat_keys
    }
    state_stat = {"observation.state": state_concat}

    action_concat = {
        k: np.concatenate([np.asarray(stats[action_key][k]) for action_key in action_keys], axis=-1)
        for k in stat_keys
    }
    action_stat = {"action": action_concat}

    unnormalize_fn = UnNormalizeTransformFn(
        selected_keys=["action"],
        mode="mean_std",
        norm_stats=action_stat,
    )

    input_transforms = compose(
        [
            ResizeImagesWithPadFn(height=resize_size, width=resize_size),
            Qwen3_VLProcessorTransformFn(),
            NormalizeTransformFn(selected_keys=["observation.state"], norm_stats=state_stat),
        ]
    )

    return policy, input_transforms, unnormalize_fn

@dataclass
class InferenceArgs:
    """CLI arguments for policy inference."""

    ckpt_path: Path
    stats_key: str = "lift2"
    resize_size: int = 224
    image_history_interval: int = 15
    action_mode: str = "delta"  # delta | abs
    dtype: str = "float32"  # float32 | bfloat16
    decode_image: bool = False
    infer_horizon: int = 50
    action_horizon_size: int = 30

    worker_ids: str = "0"  # Comma-separated worker IDs, e.g. "0,1,2"
    host: str = "0.0.0.0"
    port: int = 8087
    url: str = ""  # Optional custom URL for EvalClient connection, overrides host and port if provided.
    token: str = ""
    run_id: str = ""


class QwenA1PolicyWrapper:
    """QwenA1 policy wrapper with stateful action chunking."""

    def __init__(self, args: InferenceArgs):
        self.args = args
        dtype = torch.float32 if args.dtype == "float32" else torch.bfloat16
        self.dtype = dtype

        self.policy, self.input_transforms, self.unnormalize_fn = build_policy_and_transforms(
            args.ckpt_path, args.stats_key, args.resize_size, dtype
        )
        self.image_history_maxlen = args.image_history_interval + 1
        self.reset()

    def reset(self) -> None:
        self.policy.reset()
        self.action_plan = deque(maxlen=self.args.action_horizon_size)
        self.head_color_history = deque(maxlen=self.image_history_maxlen)
        self.left_wrist_color_history = deque(maxlen=self.image_history_maxlen)
        self.right_wrist_color_history = deque(maxlen=self.image_history_maxlen)
        self.chunk_start_base = None

    @staticmethod
    def _to_image_tensor(image: np.ndarray, dtype: torch.dtype) -> torch.Tensor:
        return torch.as_tensor(image.copy()).contiguous().cuda().to(dtype) / 255.0

    @staticmethod
    def _pack_action_fields(action: np.ndarray) -> np.ndarray:
        # Reorder robot joint/gripper fields to match the deployed controller format.
        return np.concatenate([action[:6], action[12:14], action[6:12], action[14:16]], axis=-1)

    def get_action(self, obs: dict) -> dict:
        if not self.action_plan:
            self._plan_action(obs)
        if self.action_plan:
            output = {}
            action = np.asarray(self.action_plan.popleft(), dtype=np.float32)
            joints_gripper = self._pack_action_fields(action)
            curr_base = np.asarray(obs["obs"]["state.base"], dtype=np.float32)
            if self.chunk_start_base is None:
                self.chunk_start_base = curr_base.copy()
            predicted_rel_base = action[16:]
            target_base_abs = self.chunk_start_base + predicted_rel_base
            base_motion = target_base_abs - curr_base
            output["action"] = joints_gripper.tolist()
            output['is_rel'] = False
            output["base_motion"] = base_motion.tolist()
            output['base_is_rel'] = True
            output["control_type"] = "joint_position"
            return output

        return {}

    def get_action_chunk(self, obs: dict) -> list[dict]:
        curr_base = np.asarray(obs["obs"]["state.base"], dtype=np.float32)
        self._plan_action(obs)
        action_chunk = []
        for action_raw in list(self.action_plan):
            action_step = {}
            action = np.asarray(action_raw, dtype=np.float32)
            joints_gripper = self._pack_action_fields(action)
            predicted_rel_base = action[16:]
            target_base_abs = curr_base + predicted_rel_base
            action_step["action"] = joints_gripper.tolist()
            action_step['is_rel'] = False
            action_step["base_motion"] = target_base_abs.tolist()
            action_step['base_is_rel'] = False
            action_step["control_type"] = "joint_position"
            action_chunk.append(action_step)
        self.action_plan.clear()
        return action_chunk

    def _plan_action(self, obs: dict) -> None:
        """Plan a new action chunk and populate the queue."""
        observation = obs['obs']
        img = observation["video.overlook_camera_view"]
        img = cv2.resize(img, (640, 480))
        left_wrist_img = observation["video.left_camera_view"]
        right_wrist_img = observation["video.right_camera_view"]
        instruction = observation["instruction"]
        joints = observation["state.joints"]
        gripper_state = observation["state.gripper"]
        base_state = observation["state.base"]
        self.chunk_start_base = np.asarray(base_state, dtype=np.float32).copy()

        # Keep base dimensions but zero values, consistent with training preprocessing.
        zero_base = np.zeros_like(base_state)
        new_state = np.concatenate([joints, zero_base, gripper_state])

        self.head_color_history.append(self._to_image_tensor(img, self.dtype))
        self.left_wrist_color_history.append(self._to_image_tensor(left_wrist_img, self.dtype))
        self.right_wrist_color_history.append(self._to_image_tensor(right_wrist_img, self.dtype))

        if not self.action_plan:
            # Build [past, current] image pairs.
            past_idx = max(len(self.head_color_history) - self.args.image_history_interval - 1, 0)
            image_head_with_history = torch.stack(
                [self.head_color_history[past_idx], self.head_color_history[-1]], dim=0
            )
            image_hand_left_with_history = torch.stack(
                [self.left_wrist_color_history[past_idx], self.left_wrist_color_history[-1]], dim=0
            )
            image_hand_right_with_history = torch.stack(
                [self.right_wrist_color_history[past_idx], self.right_wrist_color_history[-1]], dim=0
            )

            sample = {
                f"{OBS_IMAGES}.image0": image_head_with_history,
                f"{OBS_IMAGES}.image1": image_hand_left_with_history,
                f"{OBS_IMAGES}.image2": image_hand_right_with_history,
                "observation.state": torch.from_numpy(new_state).float().cuda(),
                "task": instruction,
            }

            # Convert image layout from (T, H, W, C) to (T, C, H, W).
            for key in sample.keys():
                if OBS_IMAGES in key and "mask" not in key:
                    image = sample[key].permute(0, 3, 1, 2)
                    sample[key] = image

            for transform in self.input_transforms.transforms:
                if isinstance(transform, Qwen3_VLProcessorTransformFn):
                    sample.update({
                        f"{OBS_IMAGES}.image0_mask": torch.tensor([True]).cuda(),
                        f"{OBS_IMAGES}.image1_mask": torch.tensor([True]).cuda(),
                        f"{OBS_IMAGES}.image2_mask": torch.tensor([True]).cuda(),
                    })
                sample = transform(sample)

            inputs = {}
            for key in sample.keys():
                if key == "task":
                    inputs[key] = [sample[key]]
                elif sample[key].dtype == torch.int64:
                    inputs[key] = sample[key][None].cuda()
                else:
                    inputs[key] = sample[key][None].cuda().to(dtype=self.dtype)

            inputs.update({
                f"{OBS_IMAGES}.image0_mask": torch.tensor([True]).cuda(),
                f"{OBS_IMAGES}.image1_mask": torch.tensor([True]).cuda(),
                f"{OBS_IMAGES}.image2_mask": torch.tensor([True]).cuda(),
            })

            with torch.no_grad():
                action_pred, _ = self.policy.predict_action_chunk(
                    inputs, decode_image=self.args.decode_image
                )

            action_pred = action_pred[0, : self.args.infer_horizon, :19]
            action_pred = self.unnormalize_fn({"action": action_pred})["action"]

            if self.args.action_mode == "delta":
                init_action = torch.from_numpy(new_state)[None].float().cuda()
                action_pred[:, :12] += init_action[:, :12]

            action_pred_joints = action_pred[:, :12]
            action_pred_gripper = action_pred[:, 15:]
            action_pred_base = action_pred[:, 12:15]

            action_pred_gripper[action_pred_gripper < 0.005] = 0.0
            action_pred_gripper[action_pred_gripper > 0.005] = 0.044

            action_pred = torch.cat([action_pred_joints, action_pred_gripper, action_pred_base], dim=-1)
            self.action_plan.extend(action_pred[:self.args.action_horizon_size].cpu().numpy())


if __name__ == "__main__":
    args = tyro.cli(InferenceArgs)

    worker_ids = [worker_id.strip() for worker_id in args.worker_ids.split(",") if worker_id.strip()]
    if not worker_ids:
        raise ValueError("`worker_ids` must contain at least one valid worker id.")

    if args.url:
        base_url = args.url
    else:
        base_url = f"http://{args.host}:{args.port}"

    client = EvalClient(
        base_url=base_url,
        token=args.token,
        run_id=args.run_id,
        worker_ids=worker_ids
    )
    policy_list = [QwenA1PolicyWrapper(args) for _ in worker_ids]
    print("Initialize policy successfully.")

    # Ensure workers are always terminated cleanly.
    try:
        obs = client.reset()
        while True:
            action = {
                worker_id: policy.get_action(obs[worker_id])
                for worker_id, policy in zip(worker_ids, policy_list)
            }
            try:
                obs, done = client.step(action)
            except Exception as exc:
                print(f"[warn] EvalClient step failed: {exc}", flush=True)
                client.close()
                client = EvalClient(
                    base_url=base_url,
                    token=args.token,
                    run_id=args.run_id,
                    worker_ids=worker_ids
                )
                obs = client.reset()
                policy.reset()
                break
            if done:
                break

            for worker_id, policy in zip(worker_ids, policy_list):
                worker_obs = obs.get(worker_id, {}).get("obs", {})
                if worker_obs.get("reset"):
                    policy.reset()
    finally:
        client.kill_workers()
        client.close()
