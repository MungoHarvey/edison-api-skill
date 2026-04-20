"""Unit tests for skills/_common/edison_retry.py.

All tests run without any Edison platform access.
"""
import asyncio
import sys
import pathlib
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "skills" / "_common"))
from edison_retry import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_MAX_STEPS,
    STEP_CEILING,
    _detect_signal,
    is_truncated,
    submit_with_retry,
    submit_with_retry_async,
    add_retry_args,
    load_api_key,
    truncation_prefix,
)
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from conftest import (
    FakeAsyncEdisonClient,
    FakeEdisonClient,
    FakeResponse,
)


# ── is_truncated: detector matrix ────────────────────────────────────────────

@pytest.mark.parametrize("resp,expected,label", [
    (FakeResponse(status="truncated"),                        True,  "status contains 'truncat'"),
    (FakeResponse(status="TASK_TRUNCATED"),                   True,  "status uppercase variant"),
    (FakeResponse(truncated=True),                            True,  "truncated attribute True"),
    (FakeResponse(body="Task Truncated (Max Steps Reached)"), True,  "body 'max steps reached'"),
    (FakeResponse(body="task truncated: incomplete"),         True,  "body 'task truncated'"),
    (FakeResponse(answer="All done"),                         False, "clean response"),
])
def test_is_truncated_signal_matrix(resp, expected, label):
    assert is_truncated(resp) == expected, label


def test_is_truncated_none_status():
    """Handles None status gracefully."""
    resp = FakeResponse()
    resp.status = None
    assert is_truncated(resp) is False


# ── submit_with_retry: sync behaviour ────────────────────────────────────────

def _make_task(budget):
    """Minimal task builder that records the budget."""
    from collections import namedtuple
    Task = namedtuple("Task", ["name", "query", "runtime_config"])
    return Task(name="LITERATURE", query="test query", runtime_config={"max_steps": budget})


def test_first_attempt_succeeds():
    """T1: no retries when first call succeeds."""
    client = FakeEdisonClient([FakeResponse(answer="done")])
    resp, was_truncated = submit_with_retry(client, _make_task, 100, 3)
    assert was_truncated is False
    assert resp.answer == "done"
    assert len(client.calls) == 1


def test_truncated_then_succeeds():
    """T2: escalates budget and succeeds on attempt 2."""
    truncated = FakeResponse(body="Task Truncated (Max Steps Reached): partial")
    success = FakeResponse(answer="complete")
    client = FakeEdisonClient([truncated, success])

    resp, was_truncated = submit_with_retry(client, _make_task, 100, 3)

    assert was_truncated is False
    assert resp.answer == "complete"
    assert len(client.calls) == 2
    # Second call must request a larger budget
    assert client.calls[1].runtime_config["max_steps"] == 150  # 100 * 1.5


def test_always_truncated_exhausts_retries():
    """T3: all attempts truncated → returns last response, was_truncated=True."""
    responses = [FakeResponse(body="Task Truncated (Max Steps Reached)") for _ in range(4)]
    client = FakeEdisonClient(responses)

    resp, was_truncated = submit_with_retry(client, _make_task, 100, 3)

    assert was_truncated is True
    assert len(client.calls) == 4  # initial + 3 retries


def test_step_ceiling_caps_budget():
    """T4: budget escalation is capped at STEP_CEILING."""
    # With budget=250, next = min(375, 300) = 300; then min(450, 300)=300 == prev → stop
    responses = [FakeResponse(body="Task Truncated (Max Steps Reached)") for _ in range(10)]
    client = FakeEdisonClient(responses)

    _, was_truncated = submit_with_retry(client, _make_task, 250, 10)

    assert was_truncated is True
    budgets = [c.runtime_config["max_steps"] for c in client.calls]
    assert max(budgets) == STEP_CEILING
    # Once ceiling is reached the loop terminates (no further escalation possible)
    assert budgets.count(STEP_CEILING) >= 1
    assert all(b <= STEP_CEILING for b in budgets)


def test_no_retry_flag():
    """T5: max_retries=0 → single attempt only."""
    responses = [FakeResponse(body="Task Truncated (Max Steps Reached)"), FakeResponse(answer="x")]
    client = FakeEdisonClient(responses)

    resp, was_truncated = submit_with_retry(client, _make_task, 100, 0)

    assert was_truncated is True
    assert len(client.calls) == 1


def test_list_response_unwrapped():
    """T6: client returns a list → wrapper unwraps it."""
    inner = FakeResponse(answer="unwrapped")
    client = FakeEdisonClient([[inner]])  # queue has a list

    resp, was_truncated = submit_with_retry(client, _make_task, 100, 3)

    assert resp is inner
    assert was_truncated is False


def test_warn_log_on_truncation(capsys):
    """T7: truncation warning is printed to stderr with task name and signal."""
    truncated = FakeResponse(body="Task Truncated (Max Steps Reached): partial")
    success = FakeResponse(answer="done")
    client = FakeEdisonClient([truncated, success])

    submit_with_retry(client, _make_task, 100, 3)

    err = capsys.readouterr().err
    assert "TRUNCATED" in err
    assert "LITERATURE" in err
    assert "budget=100" in err
    assert "signal=" in err


def test_default_constants():
    assert DEFAULT_MAX_STEPS == 100
    assert DEFAULT_MAX_RETRIES == 3
    assert STEP_CEILING == 300


def test_escalation_sequence():
    """Full escalation sequence: 100 → 150 → 225 → 300 (capped from 337)."""
    responses = [FakeResponse(body="Task Truncated (Max Steps Reached)") for _ in range(10)]
    client = FakeEdisonClient(responses)

    _, was_truncated = submit_with_retry(client, _make_task, 100, 10)

    budgets = [c.runtime_config["max_steps"] for c in client.calls]
    assert budgets[0] == 100
    assert budgets[1] == 150
    assert budgets[2] == 225
    assert budgets[3] == 300
    # At STEP_CEILING the loop terminates because next_budget <= budget
    assert len(budgets) == 4


# ── submit_with_retry_async ───────────────────────────────────────────────────

def _make_task_dict(budget: int) -> dict:
    return {"name": "LITERATURE", "query": "test", "runtime_config": {"max_steps": budget}}


def test_async_first_attempt_succeeds():
    """T10: async version succeeds on first attempt."""
    client = FakeAsyncEdisonClient([FakeResponse(answer="async done")])

    async def run():
        return await submit_with_retry_async(client, _make_task_dict, 100, 3, poll_interval=0)

    resp, was_truncated = asyncio.run(run())
    assert was_truncated is False
    assert resp.answer == "async done"


def test_async_truncated_then_succeeds():
    """T10b: async escalates budget and succeeds on attempt 2."""
    truncated = FakeResponse(body="Task Truncated (Max Steps Reached)")
    success = FakeResponse(answer="async complete")
    client = FakeAsyncEdisonClient([truncated, success])

    async def run():
        return await submit_with_retry_async(client, _make_task_dict, 100, 3, poll_interval=0)

    resp, was_truncated = asyncio.run(run())
    assert was_truncated is False
    assert resp.answer == "async complete"
    assert len(client.calls) == 2


def test_async_semaphore_limits_concurrency():
    """T9: Semaphore(8) caps in-flight retry chains to 8 concurrent.

    We instrument the fake client's acreate_task to track how many
    coroutines are inside the semaphore at once.
    """
    import skills._common.edison_retry as retry_mod

    # Reset the global semaphore so this test gets a fresh one
    retry_mod._RETRY_SEM = None

    n = 20
    max_concurrent = 0
    active = 0

    class InstrumentedAsyncClient:
        """Fake client that tracks peak concurrent in-flight tasks."""

        def __init__(self, n):
            self._responses = [FakeResponse(answer="ok") for _ in range(n)]
            self._task_counter = 0
            self._pending: dict = {}

        async def acreate_task(self, task) -> str:
            nonlocal active, max_concurrent
            self._task_counter += 1
            task_id = f"t-{self._task_counter}"
            self._pending[task_id] = self._responses.pop(0)
            active += 1
            max_concurrent = max(max_concurrent, active)
            await asyncio.sleep(0)  # yield to let other coroutines in
            return task_id

        async def aget_task(self, task_id: str):
            resp = self._pending.get(task_id)
            active_here = True
            # Decrement only once per task chain
            if active_here:
                nonlocal active
                active -= 1
                self._pending.pop(task_id, None)
            return resp

    client = InstrumentedAsyncClient(n)

    async def run_one():
        await submit_with_retry_async(client, _make_task_dict, 100, 0, poll_interval=0)

    async def run_all():
        await asyncio.gather(*[run_one() for _ in range(n)])

    asyncio.run(run_all())

    assert max_concurrent <= 8, f"Expected ≤8 concurrent, got {max_concurrent}"


# ── add_retry_args ────────────────────────────────────────────────────────────

def test_add_retry_args_defaults():
    """T14: defaults are 100 steps, 3 retries."""
    import argparse
    parser = argparse.ArgumentParser()
    add_retry_args(parser)
    args = parser.parse_args([])
    assert args.max_steps == 100
    assert args.max_retries == 3
    assert args.no_retry is False


def test_add_retry_args_no_retry():
    """T15: --no-retry sets no_retry=True."""
    import argparse
    parser = argparse.ArgumentParser()
    add_retry_args(parser)
    args = parser.parse_args(["--no-retry"])
    assert args.no_retry is True


def test_add_retry_args_custom_values():
    import argparse
    parser = argparse.ArgumentParser()
    add_retry_args(parser)
    args = parser.parse_args(["--max-steps", "200", "--max-retries", "1"])
    assert args.max_steps == 200
    assert args.max_retries == 1


# ── load_api_key ──────────────────────────────────────────────────────────────

def test_load_api_key_platform_var(monkeypatch):
    """T16: prefers EDISON_PLATFORM_API_KEY."""
    monkeypatch.setenv("EDISON_PLATFORM_API_KEY", "platform-key")
    monkeypatch.delenv("EDISON_API_KEY", raising=False)
    assert load_api_key() == "platform-key"


def test_load_api_key_fallback(monkeypatch):
    """T17: falls back to EDISON_API_KEY."""
    monkeypatch.delenv("EDISON_PLATFORM_API_KEY", raising=False)
    monkeypatch.setenv("EDISON_API_KEY", "legacy-key")
    assert load_api_key() == "legacy-key"


def test_load_api_key_missing_exits(monkeypatch):
    """T18: exits(1) when neither env var is set."""
    monkeypatch.delenv("EDISON_PLATFORM_API_KEY", raising=False)
    monkeypatch.delenv("EDISON_API_KEY", raising=False)
    with pytest.raises(SystemExit) as exc:
        load_api_key()
    assert exc.value.code == 1


# ── truncation_prefix ─────────────────────────────────────────────────────────

def test_truncation_prefix_format():
    prefix = truncation_prefix(attempts=3, final_budget=300)
    assert "3 attempt" in prefix
    assert "300 steps" in prefix
    assert prefix.startswith("> ⚠")
