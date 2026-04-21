import argparse
import numpy as np
import torch
from genmanip_client import EvalClient
from transformers import AutoModel, AutoProcessor


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_path", type=str, required=True)
    parser.add_argument("--base_url", type=str, required=True)
    parser.add_argument("--run_id", type=str, required=True)
    parser.add_argument("--token", type=str, required=True)
    parser.add_argument("--worker_id", default=0)
    parser.add_argument("--used_chunk_size", type=int, default=30)
    return parser.parse_args()


def main():
    args = get_args()
    wid = str(args.worker_id)

    eval_client = EvalClient(
        base_url=args.base_url,
        token=args.token,
        run_id=args.run_id,
        worker_ids=[wid],
        
    )
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = AutoModel.from_pretrained(
        args.model_path, trust_remote_code=True, torch_dtype=torch.float32
    ).to(device).eval()
    processor = AutoProcessor.from_pretrained(args.model_path, trust_remote_code=True)

    try:
        obs = eval_client.reset()
        while True:
            o = obs[wid]["obs"]
            c_joints = np.array(o["state.joints"], dtype=np.float32)
            c_base = np.array(o["state.base"], dtype=np.float32)
            p_base = c_base.copy()
            p_base[:2] *= 10.0
            p_base[2] /= 10.0
            proprio = np.concatenate(
                [c_joints, p_base, np.array(o["state.gripper"], dtype=np.float32) * 20.0]
            )
            with torch.inference_mode():
                action_chunk = model.inference_api(
                    payload={
                        "proprio": proprio,
                        "language_instruction": o["instruction"],
                        "image0": o["video.overlook_camera_view"],
                        "image1": o["video.left_camera_view"],
                        "image2": o["video.right_camera_view"],
                        "domain_id": 0,
                        "steps": 10,
                    },
                    processor=processor,
                )
            action_chunk = np.asarray(action_chunk, dtype=np.float32)
            if action_chunk.ndim == 1:
                action_chunk = action_chunk[None, :]

            action_chunk[:, 12:14] /= 10.0
            action_chunk[:, 14] *= 10.0
            action_chunk[:, 15:19] /= 20.0

            deploy_action_chunk = []
            for act in action_chunk[: args.used_chunk_size]:
                grip = (
                    ([act[15], act[16]] if act[15] >= 0.001 else [-0.01, -0.01])
                    + ([act[17], act[18]] if act[17] >= 0.001 else [-0.01, -0.01])
                )
                deploy_action_chunk.append(
                    {
                        "action": act[:6].tolist()
                        + grip[:2]
                        + act[6:12].tolist()
                        + grip[2:],
                        "base_motion": act[12:15].tolist(),
                        "control_type": "joint_position",
                        "is_rel": False,
                        "base_is_rel": False,
                    }
                )

            obs, done = eval_client.step(deploy_action_chunk)
            if done:
                break
    finally:
        eval_client.close()


if __name__ == "__main__":
    main()