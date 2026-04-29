import time
import argparse
from tqdm import tqdm
import numpy as np

from openpi_client import image_tools
from openpi_client import websocket_client_policy

from genmanip_client import EvalClient


class Pi0Client:
    """
    Run under conda env client
    """

    def __init__(self, model_host="0.0.0.0", model_port="8000", ids="0", horizon=30):
        self.client = websocket_client_policy.WebsocketClientPolicy(host=model_host, port=model_port)
        self.ids = ids
        self.horizon = horizon


    def get_action(self, obs):
        obs = self.prep_input(obs)
        action_chunk = self.client.infer(obs)["actions"]
        actions = self.prep_output(action_chunk)
        return actions

    def prep_input(self, obs):    
        observation = {
            "images/head": obs[self.ids]["obs"]["video.overlook_camera_view"],
            "images/hand_left": obs[self.ids]["obs"]["video.left_camera_view"],
            "images/hand_right": obs[self.ids]["obs"]["video.right_camera_view"],
            "states/joint": obs[self.ids]["obs"]["state.joints"],
            "states/gripper": obs[self.ids]["obs"]["state.gripper"],
            "states/base": obs[self.ids]["obs"]["state.base"],
            "prompt": obs[self.ids]["obs"]["instruction"],
        }
        return observation

    def prep_output(self, action_chunk):
        actions = []
        last_base_motion = np.zeros(3)
        for i in range(self.horizon):
            action = action_chunk[i]
            gripper_joint = action[12:16]
            base_motion = action[16:19] - last_base_motion #chunk relative to delta
            last_base_motion = action[16:19]
            
            joint = np.concatenate([
                action[:6],               # joints 0-5
                gripper_joint[0:2],       # left gripper
                action[6:12],             # joints 6-11        
                gripper_joint[2:4],       # right gripper
            ])
            action_dict = {
                "action": joint,
                "base_motion": base_motion,
                "control_type": "joint_position",
                "is_rel": False,
                "base_is_rel": True,
            }
            actions.append({self.ids:action_dict})
        return actions


def parse_list(s):
    return s.split(",")

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--worker_ids",
        type=parse_list,
        default=["0"],
        help="List of worker IDs, i.e. --worker_ids 0,1,2",
    )
    parser.add_argument("--eval_host", type=str)
    parser.add_argument("--run_id", type=str)
    parser.add_argument("--token", type=str)
    parser.add_argument("--model_host", type=str, default="0.0.0.0")
    parser.add_argument("--model_port", type=int, default=8000)
    parser.add_argument("--horizon", type=int, default=10)
    parser.add_argument("--config", type=str, default="")
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("-a", "--arm_type", type=str, default="r5a")
    parser.add_argument("-g", "--gripper_type", type=str, default="lift2")
    parser.add_argument("-c", "--control_type", type=str, default="joint_position")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    base_url = args.eval_host
    run_id = args.run_id
    worker_ids = args.worker_ids
    token = args.token
   
    config = args.config

    ids = worker_ids[0]
    # Create workers on server here, make sure they are created before stepping
    eval_client = EvalClient(base_url=base_url, worker_ids=worker_ids, run_id=run_id, token=token)
    print(f"Created workers {worker_ids} on server {base_url}.")

    pi0_client = Pi0Client(args.model_host, args.model_port, ids, args.horizon)
    print(f"Connect to model server")

    try:
        obs = eval_client.reset()
        eval_finished = False
        while not eval_finished:
            
            if obs[ids]["obs"]["reset"]:
                pass
            action_chunk = pi0_client.get_action(obs)
            for action in action_chunk:
                obs, eval_finished = eval_client.step(action)
                if eval_finished:
                    break
                if obs[ids]["obs"]["reset"]: 
                    break
    finally:
        eval_client.close()

    