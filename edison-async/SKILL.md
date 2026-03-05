---
name: edison-async
description: >
  Run multiple Edison tasks concurrently using async/batch submission patterns.
  Use this skill when you need to submit many queries simultaneously (e.g. screening
  a list of compounds against the literature, or running precedent searches for a
  panel of targets) and want to retrieve results without blocking. Covers async task
  creation, polling for completion, and batch result aggregation.
---

# Edison Async & Batch Operations

## Purpose

This skill orchestrates **concurrent, non-blocking** Edison task submissions using the
platform's async API. It is appropriate when:

- You have 3+ queries to run and do not want to wait sequentially
- You want to submit a batch and check back later
- You are building a pipeline where Edison queries run in parallel with other work

**Use this skill when:**
- Running literature or precedent searches across a panel of targets/compounds
- Submitting multiple analysis tasks simultaneously
- Polling for results from previously submitted task IDs

**Combine with other Edison skills** — this skill handles the *how* (async/batch);
the other skills define the *what* (literature, precedent, molecules, analysis).

---

## Prerequisites

- Edison environment configured (run `edison-setup` skill first)
- `.env` file with `EDISON_API_KEY` set
- **Run pre-flight check:** `.venv/bin/python edison-skills/edison-setup/scripts/check_environment.py`

---

## Usage

### Async batch from a JSONL file

Each line of the input file is a JSON object with `name` and `query` fields:

```jsonl
{"name": "LITERATURE", "query": "What is known about TDP-43 phase separation?"}
{"name": "PRECEDENT", "query": "Has anyone used HDAC inhibitors in ALS iPSC motor neurons?"}
{"name": "MOLECULES", "query": "Design a CNS-penetrant TDP-43 aggregation inhibitor"}
```

```bash
.venv/bin/python edison-skills/edison-async/scripts/async_batch.py \
    --input queries.jsonl \
    --output results/batch_results.md
```

### Submit only (fire and forget)

```bash
.venv/bin/python edison-skills/edison-async/scripts/async_batch.py \
    --input queries.jsonl \
    --submit-only \
    --task-ids-out task_ids.txt
```

### Poll previously submitted tasks

```bash
.venv/bin/python edison-skills/edison-async/scripts/async_batch.py \
    --poll task_ids.txt \
    --output results/batch_results.md
```

---

## Input JSONL Format

```jsonl
{"name": "LITERATURE", "query": "..."}
{"name": "PRECEDENT", "query": "..."}
{"name": "MOLECULES", "query": "..."}
{"name": "ANALYSIS",  "query": "..."}
```

Valid `name` values: `LITERATURE`, `PRECEDENT`, `MOLECULES`, `ANALYSIS`, `DUMMY`

---

## Output Format

Results are saved as a multi-section Markdown document:

```markdown
# Edison Batch Results
*Submitted: YYYY-MM-DD HH:MM | Completed: YYYY-MM-DD HH:MM*
*Tasks: N submitted, N completed, N failed*

## Task 1: LITERATURE
**Query:** ...
**Result:** ...
*Task ID: `<uuid>`*

---
## Task 2: PRECEDENT
...
```

---

## Polling Strategy

The async script polls task status every 15 seconds by default.
Tasks typically complete in:

| Job Type | Typical Duration |
|---|---|
| DUMMY | < 5 seconds |
| PRECEDENT | 30–90 seconds |
| LITERATURE | 60–120 seconds |
| MOLECULES | 60–180 seconds |
| ANALYSIS | 60–120 seconds |

Use `--submit-only` + `--poll` for true fire-and-forget workflows.

---

## Claude Code Integration

```
Use the Edison async batch skill to run the following queries concurrently.
Input file: edison-queries/screening_batch.jsonl
Save all results to results/screening_batch_results.md
```

## Claude Cowork Integration

Cowork is particularly well-suited for async workflows:
1. Cowork generates the JSONL query file from a template
2. Submits via `async_batch.py --submit-only`
3. Saves task IDs to file
4. At a later time, polls for results and aggregates into the research log
