# InternVLA-A1 Baseline Test Guide

This document describes a minimal evaluation workflow for this baseline.

## 1) Install InternVLA-A1 dependencies first

Please read and follow the official setup guide in:

`third_party/InternVLA-A1/README.md`

The submodule contains the full environment and dependency requirements. Make sure the installation is completed before running evaluation.

## 2) Download checkpoint from Hugging Face

Download the model checkpoint to your local path.



```bash
mkdir -p checkpoints
huggingface-cli download hxma/EBench-Generalist-InternVLA-A1 \
  --repo-type model \
  --local-dir ./checkpoints/EBench-Generalist-InternVLA-A1
```

Then update the checkpoint path used by `eval_pjsim.sh` (or pass it via script arguments after you customize the script).

## 3) Run evaluation

Please install genmanip-client sdk into the InternVLA-A1 environment.
```
# install the EBench evaluation client
git clone https://github.com/InternRobotics/genmanip-client.git
cd genmanip-client && pip install -e .[full_numpy2] && cd -
```

From this directory, run:

```bash
bash eval_pjsim.sh
```

The script will launch `inference.py` and start evaluation.

## 4) Quick start: single worker

```bash
python inference.py \
  --ckpt_path /mnt/data/wangyukai/github/EBench/checkpoints/EBench-Generalist-InternVLA-A1 \
  --url "$BASE_URL" \
  --run_id "$RUN_ID" \
  --token "$TOKEN" \
  --worker_ids 0
```

`--url` should point to the remote EBench evaluation server. If `--url`
is empty, `inference.py` falls back to `http://{host}:{port}`.

## 5) Multi-worker / multi-host: `run_internvla_eval.sh`

`scripts/run_internvla_eval.sh` launches one `inference.py` process per
worker id, writes each worker's stdout/stderr to a separate log file, and
forwards SIGINT/SIGTERM to all children for clean shutdown.

```bash
CKPT_PATH=/you/checkpoints/EBench-Generalist-InternVLA-A1 \
BASE_URL=https://your-ebench-server.example.com \
RUN_ID=my_run_2026_04_29 \
TOKEN=$EBENCH_TOKEN \
WORKER_IDS=0,1,2,3 \
GPU_IDS=0,1,2,3 \
LOG_DIR=log_dir/internvla-a1-generalist \
bash /mnt/data/wangyukai/github/EBench/scripts/run_internvla_eval.sh
```

## 6) CLI reference (`inference.py`)

| Flag | Default | Description |
| ---- | ------- | ----------- |
| `--ckpt_path` | _req._ | Local InternVLA-A1 checkpoint directory. Must contain the policy config, weights, and `stats.json`. |
| `--stats_key` | `lift2` | Key inside `stats.json` used for state/action normalization statistics. |
| `--resize_size` | `224` | Image resize target used by `ResizeImagesWithPadFn`. |
| `--image_history_interval` | `15` | Interval used to pick the historical frame paired with the current frame. |
| `--action_mode` | `delta` | `delta`: add predicted joint deltas to the current joint state. `abs`: use predicted actions directly. |
| `--dtype` | `float32` | Policy inference dtype. Supported by the script: `float32` or `bfloat16`. |
| `--decode_image` | `False` | Pass through to `policy.predict_action_chunk(..., decode_image=...)`. Usually leave disabled for evaluation. |
| `--infer_horizon` | `50` | Number of predicted action steps kept from the model output before final truncation. |
| `--action_horizon_size` | `30` | Number of action steps deployed from each planned chunk. |
| `--worker_ids` | `0` | Comma-separated worker ids handled by this process, e.g. `0,1,2`. For multi-process launch, use one id per process. |
| `--url` | `""` | Full EBench evaluation server URL. Overrides `--host` and `--port` when set. |
| `--host` | `0.0.0.0` | Host used to build `http://{host}:{port}` when `--url` is not set. |
| `--port` | `8087` | Port used to build `http://{host}:{port}` when `--url` is not set. |
| `--run_id` | `""` | Identifier of the evaluation run; shared across all workers and hosts for the same run. |
| `--token` | `""` | Auth token issued by the EBench server. |


## Notes

- Ensure your environment variables in `eval_pjsim.sh` are set correctly (for example `HF_HOME`).
- First run may require downloading checkpoints and tokenizer files from Hugging Face.
- If you are using offline mode, keep `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1` only after required files are fully downloaded.
