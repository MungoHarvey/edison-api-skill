# Edison Skills: max_steps Control and Auto-Retry on Truncation

**Date:** 2026-04-20
**Status:** Approved for implementation planning

## Problem

Edison tasks are silently truncated when the agent hits its internal step budget,
producing the warning "Task Truncated (Max Steps Reached): This task hit its step
limit and may be incomplete." None of the skill scripts currently set
`RuntimeConfig.max_steps`, so every task runs at the (low) platform default.
Partial/truncated answers are returned without the script surfacing the truncation
to the caller, and there is no mechanism to retry with a larger budget.

## Goals

1. Raise the default step budget to a value that completes most queries (100).
2. Allow per-invocation tuning via a CLI flag.
3. Detect truncation in the response and auto-retry with a 50% larger budget
   until the task completes, retries are exhausted, or a hard step ceiling is hit.
4. Surface truncation clearly in stderr, Markdown output, and exit codes.
5. Keep scripts self-contained (PEP 723 inline metadata, no new shared imports).

## Non-Goals

- Fixing the pre-existing `data_analysis.py` answer-extraction bug
  (wrong path — should read `environment_frame["state"]["state"]["answer"]`).
  That is tracked separately.
- SDK-level changes to `edison-client`.
- Changing any skill's default behavior other than `max_steps`.

## Design

### Configuration

| Name | Value | Purpose |
|------|-------|---------|
| `DEFAULT_MAX_STEPS` | `100` | Per-task step budget when `--max-steps` is not passed |
| `DEFAULT_MAX_RETRIES` | `3` | Retries after initial attempt if truncated |
| `STEP_CEILING` | `300` | Hard cap — no retry will request more than this |
| Retry multiplier | `1.5×` | Applied to previous budget on each retry |

Escalation with defaults: `100 → 150 → 225 → 300 (capped from 337)`.

### CLI surface (per-skill scripts)

Added to `literature_search.py`, `precedent_search.py`, `chemistry_task.py`,
and `data_analysis.py`:

```
--max-steps N       Step budget for the first attempt (default: 100)
--max-retries N     Retries after truncation (default: 3)
--no-retry          Shortcut for --max-retries 0
```

### JSONL batch surface (`async_batch.py`)

Per-row optional field:

```json
{"name": "LITERATURE", "query": "...", "max_steps": 150}
```

Global CLI fallback applies when a row omits `max_steps`. Retry logic runs
per-task within the concurrent batch; it does not serialise the batch.

### Truncation detector

Since the SDK exposes truncation inconsistently across agents, check multiple
signals and treat any positive as truncated:

```python
def is_truncated(response) -> bool:
    status = (getattr(response, "status", "") or "").lower()
    if "truncat" in status:
        return True
    if getattr(response, "truncated", False):
        return True
    body = str(getattr(response, "formatted_answer", "")
                 or getattr(response, "answer", "") or "")
    return "max steps reached" in body.lower() or "task truncated" in body.lower()
```

### Retry wrapper

Replaces the single `client.run_tasks_until_done(task)` call site in each script:

```python
def submit_with_retry(client, build_task, max_steps, max_retries, verbose=False):
    budget = max_steps
    last_response = None
    for attempt in range(max_retries + 1):
        task = build_task(budget)                       # closure embeds query/config
        resp = client.run_tasks_until_done(task, verbose=verbose)
        if isinstance(resp, list):
            resp = resp[0]
        last_response = resp
        if not is_truncated(resp):
            return resp, False                          # (response, was_truncated)
        next_budget = min(int(budget * 1.5), STEP_CEILING)
        if attempt == max_retries or next_budget <= budget:
            print(f"⚠ Truncated at {budget} steps; retries exhausted.",
                  file=sys.stderr)
            return last_response, True
        print(f"⚠ Truncated at {budget} steps; retrying with {next_budget} ...",
              file=sys.stderr)
        budget = next_budget
    return last_response, True
```

Each script uses `build_task(budget)` to construct a fresh `TaskRequest` whose
`runtime_config` includes `max_steps=budget` alongside any existing
`continued_job_id`.

### Async variant (for `async_batch.py`)

Mirrors the sync wrapper but uses `acreate_task` + `aget_task` polling (the
existing pattern in that file). On truncation, the task is re-submitted with
the escalated budget — it does not attempt to "resume" the prior task, since
the Edison API does not support extending a truncated run.

### Output & exit codes

- Truncation warnings print to stderr during retries.
- If the final response is still truncated, the Markdown output is prefixed
  with a `> ⚠ Task truncated after N attempts (final budget: M steps).`
  block before the answer section.
- Exit code `2` on final truncation (consistent with existing
  `has_successful_answer == False` convention).

### Shared module

Helpers (`is_truncated`, `submit_with_retry`, `submit_with_retry_async`,
constants) live in `skills/_common/edison_retry.py`. Each script adds a small
`sys.path` injection block before importing, so PEP 723 `uv run` compatibility
is preserved (the common module is pure Python, no extra deps). Pattern:

```python
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "_common"))
from edison_retry import is_truncated, submit_with_retry, STEP_CEILING, DEFAULT_MAX_STEPS, DEFAULT_MAX_RETRIES
```

Rationale: eng-review decision 1A. ~200 LOC duplication avoided; bug fixes and
detector-signal additions land in one place. CLAUDE.md's "self-contained
convention" is updated to document the `_common` sibling import pattern.

The module additionally exposes:

- `add_retry_args(parser)` — adds `--max-steps`, `--max-retries`, `--no-retry`
  to any `argparse.ArgumentParser`. Kills ~15 LOC × 5 scripts.
- `load_api_key()` — returns `EDISON_PLATFORM_API_KEY` (falling back to
  `EDISON_API_KEY`) or prints the standard error and `sys.exit(1)`.

`submit_with_retry` returns `(response, was_truncated)` where `response` has
already been list-unwrapped, so callers drop their `isinstance(resp, list)`
branch. On final truncation the caller exits with code **2** — the same code
used for `has_successful_answer == False` — so truncation is treated as a
soft failure under the existing CLAUDE.md convention, not a new exit code.

### Truncation logging

On every detected truncation (both during retries and on final exhaustion),
`submit_with_retry` emits a single-line WARN record to stderr including:
task type (`JobNames` value), query prefix (first 80 chars), attempt number,
budget used, and the matched detector signal (`status` / `truncated` attr /
body substring). Rationale: review issue 1C — the body-substring detector is
the weakest signal; logging the matched signal lets us catch regressions if
the platform changes its truncation surface.

### Async concurrency guard

`submit_with_retry_async` in `async_batch.py` is gated by a module-level
`asyncio.Semaphore(8)` so retries cannot storm the platform. Without it, a
batch of 20 truncating tasks × 3 retries would burst to 80 concurrent
submissions. Rationale: eng-review decision 1B.

## Implementation phases

1. **Shared module** — create `skills/_common/edison_retry.py` with
   `is_truncated`, `submit_with_retry`, `submit_with_retry_async`, constants,
   and the WARN-log helper. Add unit tests using a fake-response pytest fixture.
2. **Sync scripts** — `literature_search.py`, `precedent_search.py`,
   `chemistry_task.py`, `data_analysis.py`: add `sys.path` import, CLI flags,
   and swap the `run_tasks_until_done` call for `submit_with_retry`.
3. **Async script** — `async_batch.py`: add flags, per-row `max_steps` parsing,
   `submit_with_retry_async` with `Semaphore(8)`, per-task truncation surfacing.
4. **Evaluation** — `evaluate_skills.py`: `evaluate_skill` and
   `evaluate_analysis_skill` construct tasks inline rather than shelling out
   to the per-skill scripts. Apply the same detector + retry wrapper here so
   full-mode runs inherit the retry behaviour. Surface truncation in the
   report's per-skill "Status" column as a third state (`⚠ Truncated`).
5. **Documentation & skill instructions** — update:
   - `CLAUDE.md` Quick Reference and Running Skills sections with the new flags
     and a note on retry behaviour.
   - Each `skills/<skill>/SKILL.md` to mention `--max-steps` / `--max-retries`
     in the skill's usage examples.
   - `.env.example` comment if retry-tuning env vars are ever added
     (none planned in this change).
6. **Manual verification** — once Edison platform access is restored, run a
   known-long literature query (the TDP-43 prompt) with defaults and confirm
   either successful completion or a clean retry-exhaustion message.

## Testing strategy

Tests live at `tests/` at the repo root (single `uv run pytest` entrypoint).
`tests/conftest.py` provides a `FakeEdisonClient` with a scripted response
queue — deterministic and explicit. Full test matrix is in the eng-review
test-plan artifact under `~/.gstack/projects/<slug>/`.

- **Unit-level** (no platform):
  - Detector: parameterised over all five truth-paths.
  - `submit_with_retry`: first-success, truncate-then-success, exhaustion,
    `STEP_CEILING` cap, `--no-retry`, list-unwrap, WARN-log contents.
  - `submit_with_retry_async`: **asserts `Semaphore(8)` caps in-flight
    concurrency** (20 truncating tasks instrumented on the fake client).
  - `add_retry_args` defaults + `--no-retry`.
  - `load_api_key`: both env vars, backward-compat fallback, exit on neither.
- **Regression** (no platform):
  - `continued_from` still plumbed through `runtime_config` alongside
    `max_steps`.
  - Output Markdown on successful runs matches golden file.
  - Truncated-run Markdown has the `> ⚠ Task truncated ...` prefix.
- **Integration** (requires platform access): covered by phase 6.

## Risks

- **Cost escalation.** A pathologically truncated task now burns up to
  ~4× credits before giving up. Mitigated by the `STEP_CEILING` of 300 and
  the `--no-retry` flag for batch jobs where this matters.
- **Truncation detection false negatives.** If the platform introduces a new
  truncation signal not covered by the three checks, we silently return the
  partial answer. Mitigated by logging `response.status` at debug level.
