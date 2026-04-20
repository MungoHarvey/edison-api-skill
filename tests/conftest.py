"""Shared test fixtures for Edison skill tests."""
import pytest


class FakeResponse:
    """Minimal Edison response object for unit tests."""

    def __init__(
        self,
        *,
        answer: str = "Test answer",
        status: str = "success",
        truncated: bool = False,
        body: str | None = None,
        task_id: str = "fake-task-123",
        has_successful_answer: bool = True,
    ):
        self.answer = body if body is not None else answer
        self.formatted_answer = body if body is not None else None
        self.status = status
        self.truncated = truncated
        self.task_id = task_id
        self.id = task_id
        self.has_successful_answer = has_successful_answer if not truncated else False


def _truncated_via_status() -> FakeResponse:
    return FakeResponse(status="truncated", answer="partial")


def _truncated_via_attr() -> FakeResponse:
    return FakeResponse(truncated=True, answer="partial")


def _truncated_via_body_steps() -> FakeResponse:
    return FakeResponse(body="Task Truncated (Max Steps Reached): incomplete")


def _truncated_via_body_task() -> FakeResponse:
    return FakeResponse(body="Task Truncated: answer cut short")


def _success() -> FakeResponse:
    return FakeResponse(answer="Complete answer", has_successful_answer=True)


class FakeEdisonClient:
    """Scripted response queue for sync tests.

    Pops one response per run_tasks_until_done call in order.
    Also records every TaskRequest that was passed.
    """

    def __init__(self, responses: list):
        self._queue = list(responses)
        self.calls: list = []

    def run_tasks_until_done(self, task, verbose: bool = False):
        self.calls.append(task)
        if not self._queue:
            raise RuntimeError("FakeEdisonClient: no more responses in queue")
        return self._queue.pop(0)


class FakeAsyncEdisonClient:
    """Async-compatible fake client for submit_with_retry_async tests."""

    def __init__(self, responses: list):
        self._queue = list(responses)
        self.calls: list = []
        self._task_counter = 0
        self._pending: dict = {}

    async def acreate_task(self, task) -> str:
        self.calls.append(task)
        self._task_counter += 1
        task_id = f"async-task-{self._task_counter}"
        if not self._queue:
            raise RuntimeError("FakeAsyncEdisonClient: no more responses in queue")
        self._pending[task_id] = self._queue.pop(0)
        return task_id

    async def aget_task(self, task_id: str):
        return self._pending.get(task_id)


@pytest.fixture
def fake_response():
    return _success


@pytest.fixture
def truncated_status():
    return _truncated_via_status


@pytest.fixture
def truncated_attr():
    return _truncated_via_attr


@pytest.fixture
def truncated_body_steps():
    return _truncated_via_body_steps


@pytest.fixture
def truncated_body_task():
    return _truncated_via_body_task
