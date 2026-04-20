"""Unit tests for async_batch.py pure helper functions.

These functions don't call the Edison API, so we mock the module-level
imports (edison_client, dotenv) before importing the script.
"""
import json
import sys
import types
import pathlib
import pytest

# ── Stub out heavy top-level imports so we can import the script ──────────────
_stub_client = types.ModuleType("edison_client")


class _JobNames:
    LITERATURE = "LITERATURE"
    PRECEDENT = "PRECEDENT"
    MOLECULES = "MOLECULES"
    ANALYSIS = "ANALYSIS"
    DUMMY = "DUMMY"


_stub_client.EdisonClient = object
_stub_client.JobNames = _JobNames

_stub_models = types.ModuleType("edison_client.models")
_stub_models_app = types.ModuleType("edison_client.models.app")
_stub_models_app.TaskRequest = dict
_stub_client.models = _stub_models
sys.modules.setdefault("edison_client", _stub_client)
sys.modules.setdefault("edison_client.models", _stub_models)
sys.modules.setdefault("edison_client.models.app", _stub_models_app)
sys.modules.setdefault("dotenv", types.ModuleType("dotenv"))

_script_dir = pathlib.Path(__file__).resolve().parents[1] / "skills" / "edison-async" / "scripts"
sys.path.insert(0, str(_script_dir))

from async_batch import load_queries, render_results, JOB_NAME_MAP  # noqa: E402


# ── load_queries ──────────────────────────────────────────────────────────────

def test_load_queries_valid(tmp_path):
    f = tmp_path / "queries.jsonl"
    f.write_text(
        '{"name": "LITERATURE", "query": "What is X?"}\n'
        '# comment line\n'
        '\n'
        '{"name": "PRECEDENT", "query": "Has anyone done Y?"}\n',
        encoding="utf-8",
    )
    queries = load_queries(f)
    assert len(queries) == 2
    assert queries[0]["query"] == "What is X?"
    assert queries[1]["query"] == "Has anyone done Y?"


def test_load_queries_invalid_json(tmp_path):
    f = tmp_path / "bad.jsonl"
    f.write_text("not-json\n", encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        load_queries(f)
    assert exc.value.code == 1


def test_load_queries_missing_name(tmp_path):
    f = tmp_path / "missing.jsonl"
    f.write_text('{"query": "no name"}\n', encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        load_queries(f)
    assert exc.value.code == 1


def test_load_queries_unknown_job(tmp_path):
    f = tmp_path / "unknown.jsonl"
    f.write_text('{"name": "BOGUS", "query": "test"}\n', encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        load_queries(f)
    assert exc.value.code == 1


# ── render_results ────────────────────────────────────────────────────────────

class _FakeResp:
    def __init__(self, answer="ok", formatted_answer=None, task_id="tid-1"):
        self.answer = answer
        self.formatted_answer = formatted_answer
        self.task_id = task_id
        self.status = "success"


def test_render_results_success():
    results = [
        {
            "task_id": "abc",
            "query": {"name": "LITERATURE", "query": "What is X?"},
            "response": _FakeResp(answer="Answer here"),
            "status": "success",
        }
    ]
    output = render_results(results, "2026-04-20 12:00")
    assert "# Edison Batch Results" in output
    assert "Task 1" in output
    assert "LITERATURE" in output
    assert "Answer here" in output
    assert "abc" in output


def test_render_results_truncated():
    results = [
        {
            "task_id": "xyz",
            "query": {"name": "MOLECULES", "query": "Design compound"},
            "response": _FakeResp(answer="partial"),
            "status": "truncated",
        }
    ]
    output = render_results(results, "2026-04-20 12:00")
    assert "truncated" in output.lower()
    assert "partial" in output


def test_render_results_failed():
    results = [
        {
            "task_id": "fail-1",
            "query": {"name": "ANALYSIS", "query": "Analyse data"},
            "response": None,
            "status": "failed",
        }
    ]
    output = render_results(results, "2026-04-20 12:00")
    assert "failed" in output.lower()
    assert "fail-1" in output


def test_render_results_counts_summary():
    results = [
        {"task_id": "t1", "query": {"name": "LITERATURE", "query": "Q1"}, "response": _FakeResp(), "status": "success"},
        {"task_id": "t2", "query": {"name": "PRECEDENT", "query": "Q2"}, "response": _FakeResp(), "status": "truncated"},
        {"task_id": "t3", "query": {"name": "MOLECULES", "query": "Q3"}, "response": None, "status": "failed"},
    ]
    output = render_results(results, "2026-04-20 12:00")
    assert "3 submitted" in output
    assert "1 succeeded" in output
    assert "1 truncated" in output
