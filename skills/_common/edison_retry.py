"""
skills/_common/edison_retry.py

Shared retry helpers for Edison skill scripts.

Import pattern (from any skills/<skill>/scripts/*.py):
    import sys, pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "_common"))
    from edison_retry import (
        is_truncated, submit_with_retry, submit_with_retry_async,
        add_retry_args, load_api_key,
        DEFAULT_MAX_STEPS, DEFAULT_MAX_RETRIES, STEP_CEILING,
    )
"""

import asyncio
import os
import sys
from typing import Any, Callable

DEFAULT_MAX_STEPS = 100
DEFAULT_MAX_RETRIES = 3
STEP_CEILING = 300
MAX_CONCURRENT_CHAINS = 8   # semaphore cap for async retry storms
BUDGET_ESCALATION_FACTOR = 1.5

# Lazily initialised; created inside the running event loop on first use.
_RETRY_SEM: asyncio.Semaphore | None = None


def _get_sem() -> asyncio.Semaphore:
    global _RETRY_SEM
    if _RETRY_SEM is None:
        _RETRY_SEM = asyncio.Semaphore(MAX_CONCURRENT_CHAINS)
    return _RETRY_SEM


def _next_budget(budget: int) -> int:
    """Return the next escalated budget, capped at STEP_CEILING."""
    return min(int(budget * BUDGET_ESCALATION_FACTOR), STEP_CEILING)


# ── Truncation detection ──────────────────────────────────────────────────────

def _detect_signal(response: Any) -> str:
    """Return a short string naming the first truncation signal that matched."""
    status = (getattr(response, "status", "") or "").lower()
    if "truncat" in status:
        return f"status={status!r}"
    if getattr(response, "truncated", False):
        return "truncated=True"
    body = str(
        getattr(response, "formatted_answer", "")
        or getattr(response, "answer", "")
        or ""
    )
    body_lower = body.lower()
    if "max steps reached" in body_lower:
        return "body='max steps reached'"
    if "task truncated" in body_lower:
        return "body='task truncated'"
    return "unknown"


def is_truncated(response: Any) -> bool:
    status = (getattr(response, "status", "") or "").lower()
    if "truncat" in status:
        return True
    if getattr(response, "truncated", False):
        return True
    body = str(
        getattr(response, "formatted_answer", "")
        or getattr(response, "answer", "")
        or ""
    )
    body_lower = body.lower()
    return "max steps reached" in body_lower or "task truncated" in body_lower


def _task_name(task: Any) -> str:
    raw = task.get("name", "?") if isinstance(task, dict) else getattr(task, "name", "?")
    return str(raw).split(".")[-1]


def _warn(task_name: str, query_prefix: str, attempt: int, budget: int, signal: str) -> None:
    print(
        f"⚠ TRUNCATED [{task_name}] query='{query_prefix}' "
        f"attempt={attempt} budget={budget} signal={signal}",
        file=sys.stderr,
    )


# ── Sync retry wrapper ────────────────────────────────────────────────────────

def submit_with_retry(
    client: Any,
    build_task: Callable[[int], Any],
    max_steps: int,
    max_retries: int,
    verbose: bool = False,
) -> tuple[Any, bool]:
    """
    Submit a task, retrying with an escalating step budget on truncation.

    build_task(budget) must return a fresh TaskRequest each call.
    Returns (response, was_truncated).  response is always list-unwrapped.
    """
    budget = max_steps
    last_response = None

    for attempt in range(max_retries + 1):
        task = build_task(budget)
        resp = client.run_tasks_until_done(task, verbose=verbose)
        if isinstance(resp, list):
            resp = resp[0]
        last_response = resp

        if not is_truncated(resp):
            return resp, False

        signal = _detect_signal(resp)
        task_name = str(getattr(task, "name", "?")).split(".")[-1]
        query_prefix = str(getattr(task, "query", ""))[:80]
        _warn(task_name, query_prefix, attempt + 1, budget, signal)

        next_budget = _next_budget(budget)
        if attempt == max_retries or next_budget <= budget:
            print(f"⚠ Retries exhausted at {budget} steps.", file=sys.stderr)
            return last_response, True

        print(f"⚠ Retrying with {next_budget} steps ...", file=sys.stderr)
        budget = next_budget

    return last_response, True  # unreachable but satisfies type checker


# ── Async retry wrapper ───────────────────────────────────────────────────────

async def submit_with_retry_async(
    client: Any,
    build_task: Callable[[int], Any],
    max_steps: int,
    max_retries: int,
    poll_interval: int = 15,
    max_poll_attempts: int = 120,
) -> tuple[Any, bool]:
    """
    Async equivalent of submit_with_retry for use with acreate_task / aget_task.

    A module-level Semaphore(8) prevents concurrent retry storms across a batch.
    build_task(budget) must return a task dict (or TaskRequest) accepted by acreate_task.
    Returns (response, was_truncated).
    """
    budget = max_steps
    last_response = None

    for attempt in range(max_retries + 1):
        task = build_task(budget)
        # Semaphore caps concurrent submissions only — not the poll loop.
        # This prevents retry storms (8 simultaneous submissions max) while
        # allowing polling to proceed freely once a task is submitted.
        async with _get_sem():
            task_id = await client.acreate_task(task)

        resp = None
        for _ in range(max_poll_attempts):
            await asyncio.sleep(poll_interval)
            resp = await client.aget_task(task_id)
            task_status = getattr(resp, "status", None)
            if task_status in ("success", "failed", "error"):
                break

        last_response = resp

        if resp is None:
            # Timeout — not truncation, return as-is
            return resp, False

        if not is_truncated(resp):
            return resp, False

        signal = _detect_signal(resp)
        query_prefix = (task.get("query", "") if isinstance(task, dict) else str(getattr(task, "query", "")))[:80]
        _warn(_task_name(task), query_prefix, attempt + 1, budget, signal)

        next_budget = _next_budget(budget)
        if attempt == max_retries or next_budget <= budget:
            print(f"⚠ Retries exhausted at {budget} steps.", file=sys.stderr)
            return last_response, True

        print(f"⚠ Retrying with {next_budget} steps ...", file=sys.stderr)
        budget = next_budget

    return last_response, True


# ── CLI helpers ───────────────────────────────────────────────────────────────

def add_retry_args(parser: Any) -> None:
    """Add --max-steps, --max-retries, --no-retry to an ArgumentParser.

    Callers must apply args.no_retry themselves:
        max_retries = 0 if args.no_retry else args.max_retries
    """
    parser.add_argument(
        "--max-steps",
        type=int,
        default=DEFAULT_MAX_STEPS,
        metavar="N",
        help=f"Step budget for the first attempt (default: {DEFAULT_MAX_STEPS})",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=DEFAULT_MAX_RETRIES,
        metavar="N",
        help=f"Retries after truncation (default: {DEFAULT_MAX_RETRIES})",
    )
    parser.add_argument(
        "--no-retry",
        action="store_true",
        help="Disable auto-retry on truncation (equivalent to --max-retries 0)",
    )


def load_api_key() -> str:
    """Return EDISON_PLATFORM_API_KEY (or legacy EDISON_API_KEY), or exit(1)."""
    key = os.getenv("EDISON_PLATFORM_API_KEY") or os.getenv("EDISON_API_KEY")
    if not key:
        print(
            "✗ EDISON_PLATFORM_API_KEY not set in environment or .env",
            file=sys.stderr,
        )
        sys.exit(1)
    return key


# ── Truncation output helpers ─────────────────────────────────────────────────

def truncation_prefix(attempts: int, final_budget: int) -> str:
    """Markdown blockquote prefix for the output when a run is still truncated."""
    return f"> ⚠ Task truncated after {attempts} attempt(s) (final budget: {final_budget} steps).\n\n"
