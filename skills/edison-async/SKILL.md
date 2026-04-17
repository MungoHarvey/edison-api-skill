---
name: edison-async
description: >
  This skill should be used when the user wants to run multiple Edison queries
  concurrently, asks to "submit a batch", "run these in parallel", "submit all
  and check back later", "fire and forget", or has 3+ queries to run without
  waiting for each sequentially. This skill should also be used when polling
  for previously submitted task IDs. Covers async task submission, polling, and batch result aggregation.
  For single queries, use the specific skill directly (edison-literature,
  edison-precedent, etc.).
version: 0.1.0
---

# Edison Async & Batch Operations

## Purpose

Orchestrate **concurrent, non-blocking** Edison task submissions using the platform's
async API.

**Use when:**
- Running literature or precedent searches across a panel of targets or compounds
- Submitting 3+ queries simultaneously and not wanting to wait sequentially
- Building a pipeline where Edison queries run in parallel with other work
- Polling for results from previously submitted task IDs

This skill handles the *how* (async/batch). The other skills define the *what*
(literature, precedent, molecules, analysis).

---

## Prerequisites

- Edison environment configured (run `edison-setup` skill first if uncertain)
- `.env` file with `EDISON_PLATFORM_API_KEY` set at project root
- Input queries in JSONL format (one JSON object per line)

---

## Usage

### Async batch from a JSONL file

```bash
uv run skills/edison-async/scripts/async_batch.py \
    --input queries.jsonl \
    --output results/batch_results.md
```

### Submit only (fire and forget)

```bash
uv run skills/edison-async/scripts/async_batch.py \
    --input queries.jsonl \
    --submit-only \
    --task-ids-out task_ids.txt
```

### Poll previously submitted tasks

```bash
uv run skills/edison-async/scripts/async_batch.py \
    --poll task_ids.txt \
    --output results/batch_results.md
```

---

## Input JSONL Format

Each line is a JSON object with `name` and `query` fields:

```jsonl
{"name": "LITERATURE", "query": "What is known about TDP-43 phase separation?"}
{"name": "PRECEDENT", "query": "Has anyone used HDAC inhibitors in ALS iPSC motor neurons?"}
{"name": "MOLECULES", "query": "Design a CNS-penetrant TDP-43 aggregation inhibitor"}
```

Valid `name` values: `LITERATURE`, `LITERATURE_HIGH`, `PRECEDENT`, `MOLECULES`, `ANALYSIS`, `DUMMY`

Note: `LITERATURE_HIGH` jobs take significantly longer than `LITERATURE` (allow 3–10 minutes).
Avoid short timeouts on batches that include them, and prefer `--submit-only` + `--poll`
for batches mixing fast and slow job types. `LITERATURE_HIGH` requires a compatible
version of `edison-client` — verify with:
`python -c "from edison_client import JobNames; print([j.name for j in JobNames])"`

Note: `ANALYSIS` batch jobs do not support a dataset payload — there is no `data` field in the JSONL format. Use `ANALYSIS` in batch mode only for follow-up questions using `--continued-from` on a prior analysis task, not for new dataset submissions. For data analysis with a dataset, use the `edison-analysis` skill directly.

Comments and blank lines are ignored. Invalid JSON or missing `name`/`query` fields
cause the script to exit with status 1.

---

## Output Format

Results saved as multi-section Markdown:

```markdown
# Edison Batch Results
*Submitted: YYYY-MM-DD HH:MM | Completed: YYYY-MM-DD HH:MM*
*Tasks: N submitted, N completed, N failed*

## Task 1: LITERATURE
**Query:** ...
**Result:** ...
*Task ID: `<uuid>`*
```

---

## Polling Strategy

The script polls task status every 15 seconds by default.

| Job Type | Typical Duration |
|---|---|
| DUMMY | < 5 seconds |
| PRECEDENT | 30–90 seconds |
| LITERATURE | 60–120 seconds |
| LITERATURE_HIGH | 3–10 minutes |
| MOLECULES | 60–180 seconds |
| ANALYSIS | 60–120 seconds |

Use `--submit-only` + `--poll` for true fire-and-forget workflows where results
are retrieved in a separate step.

---

## Additional Resources

- **[`references/tasks.md`](references/tasks.md)** — full client method table, list-batching
  shorthand for small batches, `continued_job_id` parameter, and response schema navigation.
