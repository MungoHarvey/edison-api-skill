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

### Self-contained pattern

The helpers (`is_truncated`, `submit_with_retry`, constants, CLI flags) are
copy-pasted into each of the five scripts rather than extracted to a shared
module. This preserves the existing PEP 723 self-contained convention
(each script runnable via `uv run <script>.py` with inline dependencies)
documented in `CLAUDE.md`.

## Implementation phases

1. **Sync scripts** — `literature_search.py`, `precedent_search.py`,
   `chemistry_task.py`, `data_analysis.py`: add flags, detector, retry wrapper.
2. **Async script** — `async_batch.py`: add flags, per-row `max_steps` parsing,
   async retry wrapper, per-task truncation surfacing.
3. **Evaluation** — `evaluate_skills.py`: `evaluate_skill` and
   `evaluate_analysis_skill` construct tasks inline rather than shelling out
   to the per-skill scripts. Apply the same detector + retry wrapper here so
   full-mode runs inherit the retry behaviour. Surface truncation in the
   report's per-skill "Status" column as a third state (`⚠ Truncated`).
4. **Documentation & skill instructions** — update:
   - `CLAUDE.md` Quick Reference and Running Skills sections with the new flags
     and a note on retry behaviour.
   - Each `skills/<skill>/SKILL.md` to mention `--max-steps` / `--max-retries`
     in the skill's usage examples.
   - `.env.example` comment if retry-tuning env vars are ever added
     (none planned in this change).
5. **Manual verification** — once Edison platform access is restored, run a
   known-long literature query (the TDP-43 prompt) with defaults and confirm
   either successful completion or a clean retry-exhaustion message.

## Testing strategy

- **Unit-level** (per script, no platform): build a fake response object that
  flips between truncated and complete, and assert the retry loop behaves:
  completes on first success, escalates on truncation, caps at `STEP_CEILING`,
  and respects `--max-retries 0`.
- **Integration** (requires platform access): covered by phase 5.

## Risks

- **Cost escalation.** A pathologically truncated task now burns up to
  ~4× credits before giving up. Mitigated by the `STEP_CEILING` of 300 and
  the `--no-retry` flag for batch jobs where this matters.
- **Truncation detection false negatives.** If the platform introduces a new
  truncation signal not covered by the three checks, we silently return the
  partial answer. Mitigated by logging `response.status` at debug level.
