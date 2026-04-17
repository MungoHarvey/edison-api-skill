"""Tests for ping_platform 3-value return contract."""
import sys
import os
import importlib.util

import pytest


def _load_check_environment():
    spec = importlib.util.spec_from_file_location(
        "check_environment",
        os.path.join(os.path.dirname(__file__), "..", "skills", "edison-setup", "scripts", "check_environment.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    # Prevent the module-level code from running the main() guard
    mod.__name__ = "check_environment"
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def ping_fn(monkeypatch):
    monkeypatch.setenv("EDISON_PLATFORM_API_KEY", "test-key")
    mod = _load_check_environment()
    return mod.ping_platform


def _mock_client(exc=None, response=None):
    class FakeResponse:
        answer = "pong"

    class FakeClient:
        def __init__(self, api_key):
            pass

        def run_tasks_until_done(self, task):
            if exc:
                raise exc
            return response or FakeResponse()

    return FakeClient


def test_returns_true_on_success(ping_fn):
    result = ping_fn(_mock_client())
    assert result is True


def test_returns_none_on_404(ping_fn):
    result = ping_fn(_mock_client(exc=Exception("404 not found")))
    assert result is None


def test_returns_none_on_not_found(ping_fn):
    result = ping_fn(_mock_client(exc=Exception("resource not found")))
    assert result is None


def test_returns_false_on_401(ping_fn):
    result = ping_fn(_mock_client(exc=Exception("401 unauthorized")))
    assert result is False


def test_returns_false_on_generic_exception(ping_fn):
    result = ping_fn(_mock_client(exc=Exception("network timeout")))
    assert result is False


def test_returns_false_when_no_api_key(monkeypatch):
    monkeypatch.delenv("EDISON_PLATFORM_API_KEY", raising=False)
    monkeypatch.delenv("EDISON_API_KEY", raising=False)
    mod = _load_check_environment()
    result = mod.ping_platform(object)
    assert result is False
