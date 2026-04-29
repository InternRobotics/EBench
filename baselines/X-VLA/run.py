import argparse
import numpy as np
import time
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
    parser.add_argument(
        "--step_mode",
        type=str,
        default="step",
        choices=("chunk", "step"),
        help="chunk: send one inferred chunk per EvalClient.step(); step: execute one action at a time",
    )
    
    parser.add_argument("--client_reinit_retries", type=int, default=3)
    parser.add_argument("--client_reinit_backoff", type=float, default=5.0)
    return parser.parse_args()


def build_eval_client(args, wid):
    return EvalClient(
        base_url=args.base_url,
        token=args.token,
        run_id=args.run_id,
        worker_ids=[wid],
    )


def cleanup_eval_client(eval_client):
    if eval_client is None:
        return

    try:
        eval_client.close()
    except Exception as exc:
        action = "close eval client"
        print(f"[warn] Failed to {action}: {exc}", flush=True)


def recreate_eval_client(args, wid, eval_client, reason):
    cleanup_eval_client(eval_client)
    last_exc = None
    max_attempts = max(1, args.client_reinit_retries)

    for attempt in range(1, max_attempts + 1):
        new_client = None
        try:
            print(
                f"[warn] Recreating EvalClient after {reason} "
                f"(attempt {attempt}/{max_attempts})",
                flush=True,
            )
            new_client = build_eval_client(args, wid)
            # After a transport failure we do a fresh reset because the previous
            # step may have partially executed on the server and local obs is stale.
            obs = new_client.reset()
            return new_client, obs
        except Exception as exc:
            last_exc = exc
            cleanup_eval_client(new_client)
            if attempt < max_attempts:
                sleep_s = args.client_reinit_backoff * attempt
                print(
                    f"[warn] EvalClient recovery attempt failed: {exc}. "
                    f"Retrying in {sleep_s:.1f}s",
                    flush=True,
                )
                time.sleep(sleep_s)

    raise RuntimeError(
        f"Failed to recover EvalClient after {max_attempts} attempts: {last_exc}"
    ) from last_exc


def main():
    args = get_args()
    wid = str(args.worker_id)
    eval_client = None
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = AutoModel.from_pretrained(
        args.model_path, trust_remote_code=True, torch_dtype=torch.float32
    ).to(device).eval()
    processor = AutoProcessor.from_pretrained(args.model_path, trust_remote_code=True)

    try:
        eval_client, obs = recreate_eval_client(
            args=args,
            wid=wid,
            eval_client=eval_client,
            reason="startup",
        )
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
            for act in action_chunk[:args.used_chunk_size]:
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

            done = False
            if args.step_mode == "chunk":
                try:
                    obs, done = eval_client.step({wid: deploy_action_chunk})
                except Exception as exc:
                    print(f"[warn] EvalClient step failed: {exc}", flush=True)
                    eval_client, obs = recreate_eval_client(
                        args=args,
                        wid=wid,
                        eval_client=eval_client,
                        reason="step failure",
                    )
            else:
                for action in deploy_action_chunk:
                    try:
                        obs, done = eval_client.step({wid: action})
                    except Exception as exc:
                        print(f"[warn] EvalClient step failed: {exc}", flush=True)
                        eval_client, obs = recreate_eval_client(
                            args=args,
                            wid=wid,
                            eval_client=eval_client,
                            reason="step failure",
                        )
                        break
                    if done or obs[wid]['obs'].get('reset', False):
                        break
            if done:
                break
    finally:
        cleanup_eval_client(eval_client)


if __name__ == "__main__":
    main()