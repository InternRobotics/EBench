# Openpi (pi0.5/pi0) Baseline Test Guide

This document describes a minimal evaluation workflow for this baseline.


> 1) Install the official openpi from `baselines/openpi/third_party/openpi` (see its README for setup).  


> 2) Layer the EBench-specific files under `baselines/openpi/src/` and `baselines/openpi/scripts/` over the official openpi (e.g. via `PYTHONPATH` or by copying).  

> 3) Modify the settings in `scripts/launch_pi_onlineeval.sh`.

> 4) Run evaluation.

```bash
bash scripts/launch_pi_onlineeval.sh
```
