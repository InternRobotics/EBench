"""Policy transforms for the mobile-base Lift2 EBench datasets."""

import dataclasses

import einops
import numpy as np

from openpi import transforms
from openpi.models import model as _model

def make_ebench_example() -> dict:
    """Creates a random input example for the EBench policy."""
    return {
        "states/joint": np.random.rand(12),
        "states/gripper":np.random.rand(4),
        "images/head": np.random.randint(256, size=(224, 224, 3), dtype=np.uint8),
        "images/hand_left": np.random.randint(256, size=(224, 224, 3), dtype=np.uint8),
        "images/hand_right": np.random.randint(256, size=(224, 224, 3), dtype=np.uint8),
        "prompt": "do something",
    }

JOINT_DIM = 12
GRIPPER_DIM = 4
BASE_DIM = 3
STATE_DIM = JOINT_DIM + GRIPPER_DIM
ACTION_DIM = JOINT_DIM + GRIPPER_DIM + BASE_DIM

def _parse_image(image: np.ndarray) -> np.ndarray:
    image = np.asarray(image)
    if np.issubdtype(image.dtype, np.floating):
        image = (255 * image).astype(np.uint8)
    if image.shape[0] == 3:
        image = einops.rearrange(image, "c h w -> h w c")
    return image


def _check_last_dim(name: str, value: np.ndarray, expected: int) -> None:
    if value.ndim == 0 or value.shape[-1] != expected:
        raise ValueError(f"{name} must have last dimension {expected}, got shape {value.shape}")


@dataclasses.dataclass(frozen=True)
class EBenchInputs(transforms.DataTransformFn):
    """
    This class is used to convert inputs to the model to the expected format. It is used for both training and inference.

    Map EBench observations and absolute action chunks into pi model space.
    """

    # Determines which model will be used.
    # Do not change this for your own dataset.
    model_type: _model.ModelType

    def __call__(self, data: dict) -> dict:
        if self.model_type not in (_model.ModelType.PI0, _model.ModelType.PI05):
            raise ValueError(f"Unsupported model type: {self.model_type}")

        joint_state = np.asarray(data["states/joint"], dtype=np.float32)
        gripper_state = np.asarray(data["states/gripper"], dtype=np.float32)
        _check_last_dim("states/joint", joint_state, JOINT_DIM)
        _check_last_dim("states/gripper", gripper_state, GRIPPER_DIM)

        inputs = {
            # Base state is intentionally used only to form targets, never model state.
            "state": np.concatenate([joint_state, gripper_state]),
            "image": {
                "base_0_rgb": _parse_image(data["images/head"]),
                "left_wrist_0_rgb": _parse_image(data["images/hand_left"]),
                "right_wrist_0_rgb": _parse_image(data["images/hand_right"]),
            },
            "image_mask": {
                "base_0_rgb": np.True_,
                "left_wrist_0_rgb": np.True_,
                "right_wrist_0_rgb": np.True_,
            },
        }

        if "actions/joint" in data:
            joint_actions = np.asarray(data["actions/joint"], dtype=np.float32)
            gripper_actions = np.asarray(data["actions/gripper"], dtype=np.float32)
            base_actions = np.asarray(data["actions/base"], dtype=np.float32)
            base_state = np.asarray(data["states/base"], dtype=np.float32)
            _check_last_dim("actions/joint", joint_actions, JOINT_DIM)
            _check_last_dim("actions/gripper", gripper_actions, GRIPPER_DIM)
            _check_last_dim("actions/base", base_actions, BASE_DIM)
            _check_last_dim("states/base", base_state, BASE_DIM)

            # Every target uses the base state at the beginning of its base action chunk as the origin.
            inputs["actions"] = np.concatenate(
                [
                    joint_actions,
                    gripper_actions,
                    base_actions - base_state[np.newaxis, ...],
                ],
                axis=-1,
            )

        if "prompt" in data:
            prompt = data["prompt"]
            inputs["prompt"] = prompt.decode("utf-8") if isinstance(prompt, bytes) else prompt

        return inputs


@dataclasses.dataclass(frozen=True)
class EBenchOutputs(transforms.DataTransformFn):
    """Drop model padding after joints have been restored to absolute targets."""

    def __call__(self, data: dict) -> dict:
        # Only return the first N actions -- since we padded actions above to fit the model action
        # dimension, we need to now parse out the correct number of actions in the return dict.
        return {"actions": np.asarray(data["actions"])[..., :ACTION_DIM]}
