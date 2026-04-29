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

From this directory, run:

```bash
bash eval_pjsim.sh
```

The script will launch `inference.py` and start evaluation.

## Notes

- Ensure your environment variables in `eval_pjsim.sh` are set correctly (for example `HF_HOME`).
- If you are using offline mode, keep `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1` only after required files are fully downloaded.
