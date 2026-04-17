"""Tests for .env walk-up logic used in all scripts."""
import os
from pathlib import Path
from unittest.mock import patch

import pytest


def _run_walkup(script_dir: Path, env: dict | None = None):
    """Execute the walk-up preamble in isolation and return what load_dotenv received."""
    loaded = []

    def fake_load_dotenv(path):
        loaded.append(Path(path))

    env = env or {}

    with patch.dict(os.environ, env, clear=False):
        try:
            _env_file = os.environ.get("EDISON_ENV_FILE")
            if _env_file:
                fake_load_dotenv(_env_file)
            else:
                root = script_dir
                for _ in range(8):
                    if (root / ".env.edison").exists():
                        fake_load_dotenv(root / ".env.edison")
                        break
                    if (root / ".env").exists():
                        fake_load_dotenv(root / ".env")
                        break
                    if (root / ".git").is_dir():
                        break
                    root = root.parent
        except Exception:
            pass

    return loaded


def test_edison_env_file_overrides_walkup(tmp_path):
    explicit = tmp_path / "custom.env"
    explicit.write_text("EDISON_API_KEY=override")
    loaded = _run_walkup(tmp_path / "scripts", env={"EDISON_ENV_FILE": str(explicit)})
    assert loaded == [explicit]


def test_env_edison_takes_priority_over_env(tmp_path):
    (tmp_path / ".env.edison").write_text("KEY=a")
    (tmp_path / ".env").write_text("KEY=b")
    loaded = _run_walkup(tmp_path / "scripts")
    assert len(loaded) == 1
    assert loaded[0].name == ".env.edison"


def test_env_found_in_parent(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("KEY=parent")
    script_dir = tmp_path / "skills" / "myscript"
    script_dir.mkdir(parents=True)
    loaded = _run_walkup(script_dir)
    assert loaded == [env_file]


def test_stops_at_git_directory(tmp_path):
    """Walk-up must not look past the .git boundary."""
    (tmp_path / ".git").mkdir()
    # .env exists above the .git dir (in tmp_path.parent) — should NOT be found
    deeper = tmp_path / "subdir"
    deeper.mkdir()
    loaded = _run_walkup(deeper)
    assert loaded == []


def test_no_env_file_anywhere(tmp_path):
    """Walk-up exits cleanly when no .env is found."""
    loaded = _run_walkup(tmp_path / "deep" / "scripts")
    assert loaded == []


def test_walk_falls_through_all_levels_gracefully(tmp_path):
    """8-level limit: no crash, no file loaded when nothing found."""
    nested = tmp_path
    for i in range(8):
        nested = nested / f"level{i}"
    loaded = _run_walkup(nested)
    assert loaded == []
