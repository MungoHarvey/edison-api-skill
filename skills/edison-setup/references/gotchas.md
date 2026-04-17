# Edison Gotchas and Common Pitfalls

## API Key Management

Never hard-code the API key in scripts or notebooks. Always load it from a `.env` file
via `python-dotenv`. The `.env` file must never be committed to version control. All
Edison scripts in this repo call `load_dotenv()` at startup — any new scripts must
follow the same pattern.

## Non-Interactive Shell Environments

Cron jobs, CI pipelines, and subprocess calls do not inherit shell exports. An
`EDISON_PLATFORM_API_KEY` set in `.bashrc` or `.zshrc` will not be available to scripts invoked
this way. Scripts must explicitly call `load_dotenv()` to source the `.env` file — and
the `.env` file must be present at the expected project root path.

## Task Duration — Do Not Set Aggressive Timeouts

`run_tasks_until_done` blocks with internal polling until the platform returns a result.
`LITERATURE_HIGH` and `ANALYSIS` jobs can take many minutes. Do not wrap these calls in
short timeouts or assume they complete quickly. For workflows that cannot block, use the
`edison-async` skill.

## Kosmos Is Not API-Accessible

The Edison platform documentation mentions Kosmos (autonomous research mode), but it is
not accessible via the `edison-client` API despite documentation that may suggest
otherwise. Kosmos is only available through the web platform at
https://platform.edisonscientific.com. Do not attempt to call it programmatically.

## Response Schema Is Not Formally Documented

The response object's field names are not guaranteed by published documentation. Always
use `getattr(response, "field_name", default)` rather than direct attribute access before
inspecting whether a field exists. Analysis and notebook artifacts from completed jobs
live at:

```python
job_result.environment_frame["state"]["info"]["output_data"]
```

Navigate this dict carefully and inspect it with `vars(response)` or direct dict access
before building assertions around field presence.

## Async Is the Only Path for Storage Operations

The synchronous `run_tasks_until_done` method does not support file storage operations
(`astore_file_content`, `afetch_data_from_storage`). For workflows requiring file upload
or output retrieval beyond the inline `--data` mechanism, use the async client methods
documented in `skills/edison-analysis/references/files.md`.

## Verify Supported JobNames at Runtime

The installed version of `edison-client` may not support all job types documented here.
Before scripting against a job type, verify it exists in the installed package:

```bash
python -c "from edison_client import JobNames; print([j.name for j in JobNames])"
```

This is especially important for `LITERATURE_HIGH`, which was added in a later release.

## PaperQA2, Aviary, and LDP Are Separate Packages

`PaperQA2`, `Aviary`, and `LDP` are independent open-source packages documented
alongside Edison on the same docs site. They are not bundled with `edison-client` and
are not required to use the Edison API. Do not attempt to import them unless a workflow
explicitly requires them outside of the Edison platform.
