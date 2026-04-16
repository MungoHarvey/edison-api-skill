# Edison Client API Reference

## Core Client Methods

| Method | Type | Description |
|---|---|---|
| `run_tasks_until_done(task_or_list)` | Sync | Submit one task or a list; block until all complete |
| `arun_tasks_until_done(task_or_list)` | Async | Awaitable equivalent |
| `create_task(dict)` | Sync | Submit a task, return task ID immediately |
| `acreate_task(dict)` | Async | Async task submission |
| `get_task(task_id)` | Sync | Poll task status by ID |
| `aget_task(task_id)` | Async | Async task status poll |

## List Batching — Simpler Than async_batch.py for Small Batches

For 2–5 tasks where fire-and-forget is not needed, pass a list directly to
`run_tasks_until_done`. The client handles concurrent submission internally and returns
results in order:

```python
results = client.run_tasks_until_done([
    {"name": JobNames.LITERATURE, "query": "What are TDP-43 aggregation mechanisms?"},
    {"name": JobNames.PRECEDENT,  "query": "Has anyone used HDAC inhibitors in ALS iPSC motor neurons?"},
])
# results[0] → LITERATURE result
# results[1] → PRECEDENT result
```

This is simpler than `async_batch.py` when you don't need `--submit-only`, `--poll`, or
JSONL-file input. Use `async_batch.py` for larger batches, file-driven workflows, or
true fire-and-forget patterns.

## Continuing from a Prior Job

The underlying API parameter is `runtime_config.continued_job_id`. This is what the
`--continued-from` CLI flag maps to in all Edison scripts:

```python
task = {
    "name": JobNames.LITERATURE,
    "query": "Expand the third finding with trial-stage evidence.",
    "runtime_config": {"continued_job_id": "<prior_task_id>"},
}
```

## Task Payload Structure

```python
{
    "name": JobNames.<TYPE>,       # required — one of: LITERATURE, LITERATURE_HIGH,
                                   #   PRECEDENT, MOLECULES, ANALYSIS, DUMMY
    "query": "<string>",           # required
    "runtime_config": {            # optional
        "continued_job_id": "<prior_task_id>"
    }
}
```

## Response Schema

The response schema is not formally documented. The main convenience attributes are:

| Attribute | Available for |
|---|---|
| `answer` | All job types |
| `formatted_answer` | LITERATURE, LITERATURE_HIGH |
| `has_successful_answer` | All job types |

For raw retrieval data, context windows, and agent traces:

```python
job_result.environment_frame["state"]["info"]["output_data"]
```

Always use `getattr(result, "field_name", None)` before asserting field presence —
available fields vary by job type and platform version. See
`skills/edison-setup/references/gotchas.md` for more.

## Verifying Supported JobNames

Before using a job type not confirmed in your environment:

```bash
python -c "from edison_client import JobNames; print([j.name for j in JobNames])"
```

`LITERATURE_HIGH` was added in a later release — this check is important before
including it in batch submissions.
