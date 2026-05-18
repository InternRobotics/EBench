# X-VLA Baseline for EBench

This directory contains the X-VLA evaluation baseline for the
[EBench](https://github.com/InternRobotics/EBench)
benchmark. `run.py` is a thin glue layer that:

1. Loads an X-VLA checkpoint via Hugging Face `AutoModel` / `AutoProcessor`
   (`trust_remote_code=True`), so any X-VLA repo on the Hub is downloaded
   and instantiated automatically — no manual cloning required.
2. Connects an `EvalClient` (from `genmanip_client`) to the EBench
   evaluation server.
3. Runs an observation → action-chunk → step loop until the server signals
   the rollout is done, with automatic client recovery on transport errors.

---

## 1. Prerequisites

- Python ≥ 3.10
- A CUDA-capable GPU is strongly recommended (`run.py` falls back to CPU
  but it is impractically slow for X-VLA).
- Network access to `huggingface.co` (or a pre-downloaded local snapshot).
- A reachable EBench evaluation server: you need its `BASE_URL`,
  per-run `RUN_ID`, and access `TOKEN`. See the top-level EBench docs
  for how to obtain these.

## 2. Installation

```bash
# (recommended) create a clean environment
conda create -n ebench-xvla python=3.10 -y
conda activate ebench-xvla

# install PyTorch matching your CUDA version, e.g.
pip install torch --index-url https://download.pytorch.org/whl/cu121

# install X-VLA baseline dependencies
pip install -r EBench/baselines/X-VLA/requirements.txt

# install the EBench evaluation client
git clone https://github.com/InternRobotics/genmanip-client.git
cd genmanip-client && pip install -e .[full_numpy1] && cd -
```

> `transformers<=4.51.3` is pinned because X-VLA's custom modeling code
> on the Hub targets that API surface — do not upgrade blindly.

## 3. Available X-VLA checkpoints

All X-VLA baseline checkpoints are published on the Hugging Face Hub
under the `InternRobotics` org and load with `AutoModel.from_pretrained`,
so you only need the repo id — `run.py` will download and cache it on
first use.

| Variant     | HF repo id                                      |
| ----------- | ----------------------------------------------- |
| Generalist  | `InternRobotics/EBench-XVLA-Generalist`         |

To pick a different variant just change `--model_path` (or `MODEL_PATH`)
to the corresponding repo id; you can also point it at a local snapshot
directory if you have already downloaded one (e.g. with
`huggingface-cli download`).

If the Hub is rate-limiting or unreachable, set a mirror once per shell:

```bash
export HF_ENDPOINT=https://hf-mirror.com   # optional
export HF_HOME=/path/to/large/cache        # optional, recommended
```

## 4. Quick start: single worker

```bash
python EBench/baselines/X-VLA/run.py \
    --model_path InternRobotics/EBench-XVLA-Generalist \
    --base_url   "$BASE_URL" \
    --run_id     "$RUN_ID" \
    --token      "$TOKEN" \
    --worker_id  0 \
    --step_mode  step
```

On first launch this will download the checkpoint into your HF cache,
build the policy on GPU, open one EvalClient worker, and start stepping.

## 5. Multi-worker / multi-host: `run_xvla_eval.sh`

`scripts/run_xvla_eval.sh` launches one `run.py` process per worker id,
streams each worker's stdout/stderr to its own log file, and forwards
SIGINT/SIGTERM to all children for clean shutdown.

```bash
MODEL_PATH=InternRobotics/EBench-XVLA-Generalist \
BASE_URL=https://your-ebench-server.example.com \
RUN_ID=my_run_2026_04_29 \
TOKEN=$EBENCH_TOKEN \
WORKER_IDS=0,1,2,3 \
STEP_MODE=step \
LOG_DIR=log_dir/xvla-generalist \
bash EBench/scripts/run_xvla_eval.sh
```

Multi-host parallelism: share the **same** `RUN_ID` across hosts and
give each host a **disjoint** slice of `WORKER_IDS` (e.g. host A uses
`0,1,2,3`, host B uses `4,5,6,7`, …). The EBench server fans episodes
out across the union of workers automatically.

Each worker writes to `${LOG_DIR}/worker_<id>.log`; if any worker exits
non-zero, the script tails the last 30 lines of every log to stdout.

## 6. CLI reference (`run.py`)

| Flag                       | Default | Description                                                                                       |
| -------------------------- | ------- | ------------------------------------------------------------------------------------------------- |
| `--model_path`             | _req._  | HF repo id (e.g. `InternRobotics/EBench-XVLA-Generalist`) or local checkpoint directory.          |
| `--base_url`               | _req._  | EBench evaluation server URL.                                                                     |
| `--run_id`                 | _req._  | Identifier of the evaluation run; shared across all workers (and hosts) for the same run.         |
| `--token`                  | _req._  | Auth token issued by the EBench server.                                                           |
| `--worker_id`              | `0`     | Worker index handled by this process. Each worker drives one parallel rollout.                    |
| `--step_mode`              | `step` | `chunk`: send the whole inferred chunk in one `EvalClient.step`. `step`: dispatch one action at a time and re-check `done` between actions. |
| `--used_chunk_size`        | `30`    | Truncate the model's predicted action chunk to this many leading actions before deployment.       |
| `--client_reinit_retries`  | `3`     | Max attempts to rebuild the `EvalClient` on a transport error.                                    |
| `--client_reinit_backoff`  | `5.0`   | Linear backoff (seconds) between reinit attempts: `attempt * backoff`.                            |

> if your task can terminate or reset mid-chunk and you want the worker
> to react immediately; pick `chunk` for lower per-action overhead.

## 7. What `run.py` actually does

The control loop (see `main` in `run.py`) is intentionally short:

1. **Build policy.** `AutoModel.from_pretrained(model_path,
   trust_remote_code=True, torch_dtype=torch.float32)` plus the matching
   `AutoProcessor`. Custom code is loaded directly from the HF repo, so
   bumping the checkpoint usually requires no local code changes.
2. **Build proprio vector.** Joint state, base pose (with the X-VLA
   training-time scaling: XY × 10, Z ÷ 10) and gripper state (× 20) are
   concatenated into a single proprio tensor.
3. **Inference.** `model.inference_api(payload, processor)` is called
   with the three camera streams (`overlook`, `left`, `right`), the
   language instruction, the proprio vector, `domain_id=0` and
   `steps=10` to produce an action chunk.
4. **Rescale & repack.** The inverse of the proprio scaling is applied
   to base actions and gripper outputs; per-action gripper widths are
   gated by a small threshold; each action is wrapped as
   `{action, base_motion, control_type=joint_position, is_rel=False,
   base_is_rel=False}`.
5. **Step.** Either the full chunk (`--step_mode chunk`) or one action
   at a time (`--step_mode step`) is sent to `EvalClient.step`. On any
   exception the client is rebuilt with backoff and the rollout is
   resumed from a fresh `reset()`.

If you need to plug in a different X-VLA variant that exposes the same
`inference_api` signature, simply point `--model_path` at it; otherwise
fork `run.py` and adapt the proprio/action mapping.

## 8. Troubleshooting

- **`ModuleNotFoundError: genmanip_client`** — you forgot step 2 of the
  install (`pip install -e .` of the genmanip-client repo).
- **HF download stalls / 401** — set `HF_ENDPOINT` to a mirror, or
  pre-download with `huggingface-cli download
  InternRobotics/EBench-XVLA-Generalist` and pass the local path to
  `--model_path`.
- **`EvalClient step failed: …` repeated forever** — the server is
  unreachable or your `TOKEN` / `RUN_ID` is wrong; the script will retry
  `--client_reinit_retries` times then exit with `RuntimeError`.
- **CUDA OOM** — X-VLA is loaded in fp32 by default for numerical
  parity with training. If you need to fit it on a smaller GPU, edit
  the `torch_dtype` in `run.py` (`torch.bfloat16` is usually safe on
  Ampere+).
