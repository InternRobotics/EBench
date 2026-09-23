---
name: ebench-analyze
description: Generate and interpret EBench evaluation reports, compare runs and baselines, and diagnose capability or generalization gaps with explicit data coverage and aggregation semantics.
---

# Analyze EBench evaluation results

Work from the EBench root. Read `third_party/genmanip-client/src/genmanip_client/extensions/analyse_cli.py` and `analyse.py` for the pinned behavior; inspect `default_cluster_map.json` only when interpreting taxonomy or checking task coverage.

## Verify inputs before rendering

Identify each run's model/checkpoint, benchmark revision, track, split, task set, seed/episode coverage, and completion state from its manifest and result files. Keep incomplete runs labeled. Missing episodes are not automatic successes or failures; state the coverage and denominator instead of inventing outcomes.

Default discovery scans `<project_root>/saved/eval_results/<benchmark>/<run_id>`. Client results commonly live under `client_results/<benchmark>/<run_id>` instead: pass the concrete run directory explicitly. Do not point to a single seed directory or assume EBench's root contains server outputs.

The loader prefers per-episode `result_info.json`, then run-level `result.json`, then task-level `episode_result.json`. These formats retain different detail. Raw `result_info.json` can carry `metric_score` needed for atomic-skill aggregation; absent metrics cannot be recovered from a total success rate. Check loaded records and parse failures before drawing conclusions.

## Generate the report

With actual run paths already verified:

```bash
gmp analyse "$RUN_A_DIR" "$RUN_B_DIR" --no-reference -o "$REPORT_PATH"
```

Omit `--no-reference` when bundled baseline comparison is desired. The default includes bundled reference models; `--reference` renders only those reference data and skips local runs. Label their bundled version rather than claiming they are freshly measured or current leaderboard standings.

**An HTML file is not proof that local results loaded.** The pinned CLI falls back to bundled reference data when no runs/records load, even when `--no-reference` was supplied. Check the CLI's loaded-record messages and report payload/run IDs against the requested inputs. If empty, report missing data; never describe the fallback as the user's model performance.

Use `--group 'Label=pattern'` only to combine intended compatible runs. Grouping different checkpoints, splits or overlapping retries can conceal variation or double-count evidence. Explicitly identify grouping members. Choose a fresh output path so prior reports remain available.

## Interpret with the right denominator

- Report SR and score separately, per split, with coverage. In the current aggregator, top-line means are over loaded records; cluster summaries first average within each task and then across tasks. Run-level aggregated input is not equivalent to raw per-episode input for weighting or uncertainty.
- Explain capability dimensions (Scene, Atomic Skill, Horizon, Precision, Mobility) and generalization dimensions (Object, Background, Instruction, Mixed) only where task labels and metrics support them. Mark absent axes as unavailable, not zero.
- Compare models on aligned benchmark revisions, split/task coverage, and evaluation settings. If coverage differs, present that difference and, when raw data permits, a clearly labeled matched subset; do not silently compare partial scores as a full benchmark.
- Do not present standard deviation across task/episode records as a confidence interval across independent runs. Separate repeated-seed variation from variation between tasks.
- Ground failure hypotheses in task-level metrics and representative episode traces. Aggregate scores alone cannot establish a camera bug, planning failure, or causal explanation. Use validation splits for suggested tuning; keep held-out results for final assessment.

Deliver a linked HTML report, input run paths/IDs, actual loaded coverage, aggregation/reference settings, key supported findings, and limitations. If only reference data or partial results exist, make that the main conclusion. Do not publish results to a leaderboard as a side effect of analysis.
