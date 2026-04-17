# Review Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply the six remaining code-review fixes to `fix/404-setup-overhaul` before PR #2 merges.

**Architecture:** All changes are surgical edits to existing files. No new files. One commit at the end covers all six fixes. Two items from the original review are already done: `set -euo pipefail` is present in `setup_venv.sh:6`, and `install.ps1:11-13` already has the overwrite warning.

**Tech Stack:** Python 3.11, bash, pytest, PowerShell (ps1 already fixed — no changes needed)

---

## Files Touched

| File | Change |
|------|--------|
| `skills/edison-setup/scripts/check_environment.py` | Fix 2 (ImportError msg), Fix 3 (parents off-by-one), Fix 5 (docstring), Fix 7 (ping comment) |
| `README.md` | Fix 5 (exit code table) |
| `tests/test_env_walkup.py` | Fix 6 (remove dead import hook) |
| All 8 `skills/*/scripts/*.py` + `setup_venv.sh` | Pre-req (version pin, if MCP confirms a version) |

---

## Task 0: Confirm `edison-client` minimum version (pre-requisite)

**Files:**
- Modify: `skills/edison-literature/scripts/literature_search.py` (PEP 723 block)
- Modify: `skills/edison-precedent/scripts/precedent_search.py` (PEP 723 block)
- Modify: `skills/edison-molecules/scripts/chemistry_task.py` (PEP 723 block)
- Modify: `skills/edison-analysis/scripts/data_analysis.py` (PEP 723 block)
- Modify: `skills/edison-async/scripts/async_batch.py` (PEP 723 block)
- Modify: `skills/edison-evaluation/scripts/evaluate_skills.py` (PEP 723 block)
- Modify: `skills/edison-setup/scripts/check_environment.py` (PEP 723 block)
- Modify: `skills/edison-setup/scripts/test_connection.py` (PEP 723 block)
- Modify: `skills/edison-setup/scripts/setup_venv.sh` (uv pip install line)

- [ ] **Step 1: Register the Edison docs MCP (user must run this once)**

  In your terminal, run:
  ```bash
  ! claude mcp add edison-scientific-documentation --scope user --transport http https://docs.edisonscientific.com/~gitbook/mcp
  ```
  Then restart Claude Code or start a new session to pick up the server.

- [ ] **Step 2: Query the MCP for minimum compatible version**

  Ask Claude: "Using the Edison docs MCP, what is the minimum `edison-client` version that
  resolves the 404 error on the DUMMY task endpoint?"

  Record the version (e.g. `1.2.0`). If the MCP returns no version, keep `>=0.9.0` and
  mark this task as skipped.

- [ ] **Step 3: Update all 8 PEP 723 blocks**

  In each of the 8 script files listed above, find the line:
  ```
  # dependencies = ["edison-client>=0.9.0", "python-dotenv"]
  ```
  Replace `0.9.0` with the confirmed version. For example, if the version is `1.2.0`:
  ```
  # dependencies = ["edison-client>=1.2.0", "python-dotenv"]
  ```

- [ ] **Step 4: Update `setup_venv.sh`**

  In `skills/edison-setup/scripts/setup_venv.sh`, find both install lines:
  ```bash
  uv pip install --python "$VENV_PY" "edison-client>=0.9.0" python-dotenv
  ```
  and:
  ```bash
  "$VENV_PIP" install "edison-client>=0.9.0" python-dotenv
  ```
  Replace `0.9.0` with the confirmed version in both.

  Also update the error message at line 19-20:
  ```bash
  echo "ERROR: Python 3.11+ required (edison-client>=0.9.0 needs 3.11+)." >&2
  ```
  → replace `0.9.0` with the confirmed version.

  Do NOT commit yet.

---

## Task 1: Fix ImportError message in `check_environment.py`

**Files:**
- Modify: `skills/edison-setup/scripts/check_environment.py:109`

- [ ] **Step 1: Locate the auto-repair branch**

  Open `skills/edison-setup/scripts/check_environment.py`. Find `check_edison_client()` at line 97.
  The `except ImportError as import_err` block starts at line 102. The auto-repair message
  is at line 110:
  ```python
  # Try auto-repair: run setup_venv.sh
  print("  Attempting to auto-repair: running setup_venv.sh ...", file=sys.stderr)
  ```

- [ ] **Step 2: Add the import error print**

  Insert one line immediately after `except ImportError as import_err:` (after the
  Python-version guard block, before the auto-repair print), so it reads:

  ```python
    except ImportError as import_err:
        err_msg = str(import_err).lower()
        if "python" in err_msg and ("version" in err_msg or "3.1" in err_msg):
            print("✗ edison-client requires Python 3.11+", file=sys.stderr)
            print("  Hint: re-create venv with: uv venv --python 3.11", file=sys.stderr)
            return False, None, None

        print(f"  Import failed: {import_err}", file=sys.stderr)
        # Try auto-repair: run setup_venv.sh
        print("  Attempting to auto-repair: running setup_venv.sh ...", file=sys.stderr)
  ```

  The new line goes between the `return False, None, None` and the `# Try auto-repair` comment.

- [ ] **Step 3: Verify no tests broke**

  ```bash
  uv run --group dev pytest tests/test_ping_platform.py -v
  ```
  Expected: all 6 tests PASS.

  Do NOT commit yet.

---

## Task 2: Fix `parents[4]` off-by-one in `find_project_root()`

**Files:**
- Modify: `skills/edison-setup/scripts/check_environment.py:34`

- [ ] **Step 1: Change `parents[4]` to `parents[3]`**

  In `find_project_root()` at line 33-34:
  ```python
  # Fallback: 5 levels up from script directory
  return Path(__file__).resolve().parents[4]
  ```
  Change to:
  ```python
  # Fallback: 4 levels up from script directory (skills/edison-setup/scripts/ → project root)
  return Path(__file__).resolve().parents[3]
  ```

  Verification: `__file__` = `.../edison-api-skill/skills/edison-setup/scripts/check_environment.py`
  - `parents[0]` = `skills/edison-setup/scripts/`
  - `parents[1]` = `skills/edison-setup/`
  - `parents[2]` = `skills/`
  - `parents[3]` = `edison-api-skill/`  ← project root ✓

- [ ] **Step 2: Update the comment to match**

  The comment above the fallback currently says "5 levels up". Change to "4 levels up" as shown above.

- [ ] **Step 3: Run full test suite**

  ```bash
  uv run --group dev pytest tests/ -v
  ```
  Expected: all 21 tests PASS.

  Do NOT commit yet.

---

## Task 3: Update exit code documentation

**Files:**
- Modify: `skills/edison-setup/scripts/check_environment.py:9-12` (module docstring)
- Modify: `README.md` (Step 4 — Verify section)

- [ ] **Step 1: Update module docstring in `check_environment.py`**

  Find the module docstring at lines 3-13:
  ```python
  Exit codes:
    0 = environment ready
    1 = hard failure (broken venv, cannot recover)
    2 = soft failure (missing API key — needs user action)
  ```
  Replace with:
  ```python
  Exit codes:
    0 = environment ready (includes ping 404 — platform-side issue, key is fine)
    1 = hard failure (broken venv, auth error, cannot recover)
    2 = soft failure (missing API key — needs user action)
  ```

- [ ] **Step 2: Update README exit code table**

  In `README.md`, find the "Step 4 — Verify" section:
  ```
  - Exit code `0` = ready. Report success.
  - Exit code `1` = hard failure — show the error output and help the user fix it.
  - Exit code `2` = API key missing or invalid — re-prompt the user to check `.env`.
  ```
  Replace with:
  ```
  - Exit code `0` = ready (includes a `⚠` warning if ping returned 404 — platform-side, key is fine).
  - Exit code `1` = hard failure — show the error output and help the user fix it.
  - Exit code `2` = API key missing or invalid — re-prompt the user to check `.env`.
  ```

  Do NOT commit yet.

---

## Task 4: Remove dead import hook from `test_env_walkup.py`

**Files:**
- Modify: `tests/test_env_walkup.py`

- [ ] **Step 1: Remove the `_make_import_hook` function**

  Delete lines 45-53 entirely:
  ```python
  def _make_import_hook(fake_dotenv_mod):
      real_import = __builtins__.__import__ if hasattr(__builtins__, "__import__") else __import__

      def hook(name, *args, **kwargs):
          if name == "dotenv":
              return fake_dotenv_mod
          return real_import(name, *args, **kwargs)

      return hook
  ```

- [ ] **Step 2: Remove the dead patch and unused MagicMock**

  In `_run_walkup`, the `with` block currently is:
  ```python
  with patch.dict(os.environ, env, clear=False), \
       patch("builtins.__import__", side_effect=_make_import_hook(fake_dotenv_mod)):
  ```
  Simplify to:
  ```python
  with patch.dict(os.environ, env, clear=False):
  ```
  Also remove these two now-unused lines above it:
  ```python
  fake_dotenv_mod = MagicMock()
  fake_dotenv_mod.load_dotenv = fake_load_dotenv
  ```
  And remove the `MagicMock` import from line 4 if it is now unused. Check: `MagicMock`
  is only used in the removed lines. Remove `MagicMock` from the import:
  ```python
  from unittest.mock import patch, MagicMock
  ```
  → change to:
  ```python
  from unittest.mock import patch
  ```

- [ ] **Step 3: Verify tests still pass**

  ```bash
  uv run --group dev pytest tests/test_env_walkup.py -v
  ```
  Expected: all 6 tests PASS.

  Do NOT commit yet.

---

## Task 5: Add intent comment to `ping_platform()`

**Files:**
- Modify: `skills/edison-setup/scripts/check_environment.py:161`

- [ ] **Step 1: Add the comment**

  Find `ping_platform()`. The exception handler at line 161:
  ```python
        if "404" in msg or "not found" in msg:
  ```
  Add one comment line immediately above it:
  ```python
        # "not found" catches both "404 not found" (HTTP text) and "resource not found"
        # (library message) — both treated as indeterminate rather than hard failures.
        if "404" in msg or "not found" in msg:
  ```

  Do NOT commit yet.

---

## Task 6: Final verification and commit

- [ ] **Step 1: Run the full test suite one last time**

  ```bash
  uv run --group dev pytest tests/ -v
  ```
  Expected output: 21 tests collected, all PASS. Zero failures, zero errors.

- [ ] **Step 2: Verify no stray `parents[4]` or `>=0.9.0` remain (unless MCP unavailable)**

  ```bash
  grep -rn "parents\[4\]" skills/ tests/
  grep -rn ">=0.9.0" skills/ tests/
  ```
  First grep: zero results expected.
  Second grep: zero results expected (or all results confirmed as intentional if MCP was unavailable).

- [ ] **Step 3: Commit all fixes**

  ```bash
  git add \
    skills/edison-setup/scripts/check_environment.py \
    skills/edison-setup/scripts/setup_venv.sh \
    skills/edison-literature/scripts/literature_search.py \
    skills/edison-precedent/scripts/precedent_search.py \
    skills/edison-molecules/scripts/chemistry_task.py \
    skills/edison-analysis/scripts/data_analysis.py \
    skills/edison-async/scripts/async_batch.py \
    skills/edison-evaluation/scripts/evaluate_skills.py \
    skills/edison-setup/scripts/test_connection.py \
    README.md \
    tests/test_env_walkup.py
  git commit -m "fix: address code review — ImportError msg, parents off-by-one, exit code docs, dead test code, ping comment, version pin"
  ```

  If Task 0 was skipped (MCP unavailable), omit the 8 script files from the add and adjust
  the commit message to remove "version pin".
