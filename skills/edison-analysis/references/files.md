# Edison File Management API

This reference covers the async file storage methods for the ANALYSIS workflow.
These methods are only accessible via the async client path — the synchronous
`run_tasks_until_done` method does not support storage operations.

## Uploading Files

### Single file

```python
resp = await client.astore_file_content(
    name="brain size dataset",
    file_path="./datasets/brain_size_data.csv",
    description="RNA-seq count matrix, 500 genes x 12 samples",
)
```

### Entire directory as a collection

```python
resp = await client.astore_file_content(
    name="scRNA project files",
    file_path="./datasets",
    description="Full project directory",
    as_collection=True,
)
```

| Parameter | Meaning |
|---|---|
| `name` | Descriptive identifier for the stored file |
| `file_path` | Local path to file or directory |
| `description` | Context for the data — helps the agent interpret it |
| `as_collection` | `True` to treat a directory as a unified collection |

## Retrieving Job Outputs

After a job completes, retrieve stored output artifacts:

```python
output_data = job_result.environment_frame["state"]["info"]["output_data"]
for entry in output_data:
    await client.afetch_data_from_storage(data_storage_id=entry["entry_id"])
```

**File size handling:**
- Files **≥ 10 MB** stream to disk automatically — the method returns a local file path
- Smaller files return a `RawFetchResponse` with the content in memory

Always use `getattr()` before asserting field names on the response object — the schema
is not formally documented (see `skills/edison-setup/references/gotchas.md`).

## When to Use File Storage vs. Inline Data

| Data size | Recommended method | Script flag |
|---|---|---|
| Up to ~15,000 characters | Inline in script | `--data file.csv` or `--data-inline "..."` |
| > ~15,000 characters | `astore_file_content()` | Async client only |
| Whole directory of files | `astore_file_content(as_collection=True)` | Async client only |

The `data_analysis.py` script truncates inline data at 20,000 characters. For datasets
that exceed this limit, the async file storage path is the correct approach — it bypasses
the truncation entirely and supports larger, multi-file datasets.

## Full Async Upload → Analyse → Retrieve Pattern

```python
import asyncio
from edison_client import EdisonClient, JobNames

async def run_analysis(api_key: str, data_path: str, query: str):
    client = EdisonClient(api_key=api_key)

    # Upload dataset
    storage_ref = await client.astore_file_content(
        name="analysis dataset",
        file_path=data_path,
        description="Pre-filtered CSV with gene expression data",
    )

    # Submit analysis task
    task = await client.acreate_task({
        "name": JobNames.ANALYSIS,
        "query": query,
        # Pass storage reference in the task payload
    })

    # Poll until complete
    result = await client.aget_task(task.task_id)

    # Retrieve outputs
    output_data = result.environment_frame["state"]["info"]["output_data"]
    for entry in output_data:
        await client.afetch_data_from_storage(data_storage_id=entry["entry_id"])

    return result
```

This pattern is appropriate for datasets larger than the 20,000-character inline limit
or when submitting multiple files as a collection.
