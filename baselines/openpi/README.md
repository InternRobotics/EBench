# OpenPI Baseline Evaluation Guide

This guide describes the minimal workflow for evaluating the post-trained OpenPI baseline, including $\pi_{0.5}$ and $\pi_{0}$, on EBench.

## Setup

### 1. Install OpenPI

Install the official OpenPI repository located at: `baselines/openpi/third_party/openpi`. 
Please refer to the official OpenPI README for detailed setup instructions.

i.e.
```
cd baselines/openpi/third_party/openpi
GIT_LFS_SKIP_SMUDGE=1 uv sync
GIT_LFS_SKIP_SMUDGE=1 uv pip install -e .

# install genmanip client for ebench evaluation
cd path/to/genmanip-client
uv pip install -e .[full_numpy1]
```

### 2. Add EBench-Specific Files

The EBench-specific files are provided under:

```bash
baselines/openpi/src/
baselines/openpi/scripts/
```

Layer these files on top of the official OpenPI codebase. This can be done by either updating `PYTHONPATH` or copying the files to the corresponding locations in the OpenPI repository.


### 3. Download EBench Post-Trained Models

The post-trained OpenPI models on EBench are available at:

- [π0.5 EBench Generalist](https://huggingface.co/william-g/pi05-ebench-generalist/tree/main)
- [π0 EBench Generalist](https://huggingface.co/william-g/pi0-ebench-generalist/tree/main)

Download the desired checkpoint and update the model path in:

```bash
scripts/launch_pi_onlineeval.sh
```

## Run Evaluation

Launch the evaluation with:

```bash
bash scripts/launch_pi_onlineeval.sh
```

Please make sure that the model path, dataset path, environment settings, and output directory are correctly specified.

## Fine-tuning

Follow the [upstream OpenPI fine-tuning guide](third_party/openpi/README.md#fine-tuning-base-models-on-your-own-data) after applying the EBench-specific files above. Use `pi05_ebench_all` or `pi0_ebench_all` for the generalist track, or the corresponding `_mobile` and `_tabletop` configs for specialist training. Set the dataset `repo_id` and model paths in `src/openpi/training/config.py` before running the upstream training commands.

Recompute normalization statistics with `scripts/compute_norm_stats.py --config-name <config_name>` before fine-tuning with the updated data transforms, and use the statistics saved with the resulting checkpoint for evaluation.

## Update Notes

**September 8, 2026:** We updated the OpenPI baseline configurations and EBench data-processing pipeline, including action-chunk sampling, relative joint and base targets, and right-wrist image masking. Use the updated EBench configs, policy transforms, and evaluation client together when evaluating the baseline or reproducing results.
