# EBench coding agent skills

These skills help coding agents evaluate **robot policies on EBench**: prepare environments, integrate models, run experiments, diagnose failures, and interpret results. They are not a benchmark for evaluating coding agents themselves.

## Where to start

| Skill | Priority | When to use it | Deliverables |
| --- | --- | --- | --- |
| [ebench-setup](ebench-setup/SKILL.md) | P0 | First-time setup, environment checks, baseline reproduction | Environment findings, missing prerequisites, executable launch commands |
| [ebench-evaluate](ebench-evaluate/SKILL.md) | P0 | Local or online evaluation, launching multiple workers | Traceable runs, logs, and completion status |
| [ebench-analyze](ebench-analyze/SKILL.md) | P0 | Report generation, model comparison, capability analysis | HTML reports, data coverage, and evidence-backed conclusions |
| [ebench-integrate-policy](ebench-integrate-policy/SKILL.md) | P1 | Connecting a custom VLA to EBench | Observation/action adapter and contract validation |
| [ebench-debug](ebench-debug/SKILL.md) | P1 | Stalled runs, errors, unexpected actions or success rates | Diagnosis, minimal fixes, and verification evidence |

P0 skills cover the complete workflow for an existing model, from preparation to reporting. For custom models, start with policy integration; use debugging when failures occur. Training, data downloads, and leaderboard publication do not have separate skills yet because they are not required for every evaluation. Follow the baseline documentation for training and data preparation.

## Usage

Skills are versioned under `skills/`, with a standard `SKILL.md` containing `name` and `description` in each directory. **Not every agent automatically discovers this directory.** The simplest approach is to ask your agent to read a specific file from the EBench repository:

```text
Read skills/ebench-setup/SKILL.md, check whether this environment can run X-VLA online evaluation, and list any missing prerequisites.
Read skills/ebench-evaluate/SKILL.md, submit an online evaluation using the configured token, wait for the endpoint and task_id, then launch my model.
Read skills/ebench-evaluate/SKILL.md and launch my model using the existing endpoint and run_id, with worker 0 only.
Read skills/ebench-integrate-policy/SKILL.md and connect my policy to EvalClient, validating the input/output contract first.
Read skills/ebench-debug/SKILL.md and investigate this run's reset timeout while preserving existing results.
Read skills/ebench-analyze/SKILL.md, compare these two result directories, generate a report, and explain whether their evaluation coverage matches.
```

You can also import these directories through your agent's skill installation mechanism. Once installed, agents that support `$skill-name` can invoke them by names such as `$ebench-evaluate`. Copying the entire collection into a global user directory is not a prerequisite for evaluation.

Repository paths in all skills are relative to the **EBench root**, not the skill directory. Skill instructions are in English for international reuse; agents can respond in the user's language. For a first run, provide the model/checkpoint, online or local mode, split/track, and GPU/worker budget. For an existing task, also provide its run ID and endpoint. Supply tokens through the local environment or an existing credential mechanism, never through committed files or reports.

## Online evaluation workflow

[ebench-evaluate](ebench-evaluate/SKILL.md#online-evaluation-queue-obtain-endpoint-then-evaluate) includes complete command examples. The agent follows this sequence:

1. Check the local model environment, checkpoint, platform URL, and token.
2. Run `gmp online submit --print_endpoint` to join the queue and wait for resources.
3. Parse `endpoint` and `task_id` from the returned JSON, using them as the evaluation URL and `run_id`, respectively.
4. Launch the baseline or custom policy client for real model evaluation, then monitor progress and save results.

A new task does not require the user to provide an evaluation URL or task ID in advance. After a queue timeout, query the existing task before retrying to avoid duplicate submissions. Receiving a URL does not mean evaluation is complete. The setup and policy integration skills also explain how to connect to this workflow.

## Maintenance and acceptance checks

Treat the baseline code and `third_party/genmanip-client` source in the current checkout as the source of truth. After updating submodules, review CLI arguments, action conversions, and result parsing. Do not assume one baseline's normalization or action layout applies to every model.

When adding or changing a skill, check its frontmatter and file references, then review its behavior against these scenarios:

| Scenario | Expected behavior |
| --- | --- |
| A fresh clone is missing submodules | Identify missing dependencies rather than treating import errors as model failures |
| The user requests real model evaluation | Use a baseline/custom policy entry point; do not report `gmp eval` fake actions as model performance |
| An existing online task is waiting for resources | Query the existing task instead of creating another one |
| A step times out with unknown execution state | Discard the old chunk, use bounded recovery, and record the interruption rather than blindly resending actions |
| Analysis inputs are empty | Report missing local results rather than presenting bundled reference data as the user's results |
| Two runs have different splits or task coverage | Flag them as not directly comparable and explain denominators and missing data |

These scenarios are maintenance acceptance criteria, not evidence that GPU or online platform end-to-end validation has been performed.
