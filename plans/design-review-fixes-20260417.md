# Design: Address Code Review Issues — fix/404-setup-overhaul
**Date:** 2026-04-17
**Branch:** fix/404-setup-overhaul
**Status:** APPROVED

## Background

PR #2 (`fix/404-setup-overhaul`) was reviewed by `/code-review-ai:ai-review`. Eight issues were
identified across the changed files. This spec describes the fixes to apply before the PR merges,
all shipped as a single "address review" commit.

## Pre-requisite: Confirm `edison-client` version

Before making any code changes, register the Edison docs MCP and query the minimum
`edison-client` version that resolves the 404 DUMMY endpoint:

```bash
claude mcp add edison-scientific-documentation --scope user --transport http https://docs.edisonscientific.com/~gitbook/mcp
```

Then query the MCP for the minimum version. Replace `>=0.9.0` with the confirmed version in:
- All 8 PEP 723 `# dependencies` blocks (one per script in `skills/*/scripts/`)
- `skills/edison-setup/scripts/setup_venv.sh` — the `uv pip install` and `"$VENV_PIP" install` lines

If the MCP is unavailable or returns no version, leave `>=0.9.0` and note it as still unconfirmed.

## Fix 1 — `setup_venv.sh`: Add `set -euo pipefail`

**File:** `skills/edison-setup/scripts/setup_venv.sh`
**Severity:** High

Add `set -euo pipefail` on the second line (after the shebang). Without it, a failed
`uv venv` or `uv pip install` returns non-zero but the script continues, resulting in a
silently broken venv with no error visible to the user.

## Fix 2 — `check_environment.py`: Print ImportError before auto-repair

**File:** `skills/edison-setup/scripts/check_environment.py`, `check_edison_client()`
**Severity:** High

In the `except ImportError as import_err` block, before the auto-repair branch, add:

```python
print(f"  Import failed: {import_err}", file=sys.stderr)
```

This surfaces the actual failure reason to the user. Currently the error is silently
swallowed when the message doesn't match the Python-version guard.

## Fix 3 — `check_environment.py`: Fix `parents[4]` off-by-one

**File:** `skills/edison-setup/scripts/check_environment.py`, `find_project_root()`
**Severity:** Low

Change the fallback from `parents[4]` to `parents[3]`.

Counting from `__file__` = `skills/edison-setup/scripts/check_environment.py`:
- `parents[0]` = `skills/edison-setup/scripts/`
- `parents[1]` = `skills/edison-setup/`
- `parents[2]` = `skills/`
- `parents[3]` = project root  ← correct
- `parents[4]` = one above project root  ← current (wrong)

## Fix 4 — `install.ps1`: Add re-install warning

**File:** `install.ps1`
**Severity:** Medium

Add a check before copying each skill directory: if the destination already exists,
print a warning (matching the `install.sh` message) before overwriting. Example:

```powershell
if (Test-Path $dest) {
    Write-Warning "$name already exists at $dest — overwriting."
}
```

## Fix 5 — Exit code docs: Document ping 404 behaviour

**Files:** `README.md`, `skills/edison-setup/scripts/check_environment.py` (module docstring)
**Severity:** Medium

Clarify that `--ping` exits 0 when it receives a 404 from the platform. The exit code
table in both places should read:

| Exit code | Meaning |
|-----------|---------|
| 0 | Ready (including 404 on ping — platform-side, key is fine) |
| 1 | Hard failure (auth error, import error, missing env) |
| 2 | API key missing or not set |

## Fix 6 — `test_env_walkup.py`: Remove dead import hook

**File:** `tests/test_env_walkup.py`
**Severity:** Low

Remove the `_make_import_hook` function and the `patch("builtins.__import__", ...)` line
from `_run_walkup`. The walk-up simulation calls `fake_load_dotenv` directly and never
triggers the import hook. Keeping it implies the import path is being tested when it isn't.

## Fix 7 — `ping_platform()`: Add intent comment for "not found" heuristic

**File:** `skills/edison-setup/scripts/check_environment.py`, `ping_platform()`
**Severity:** Low

Add a short comment above the `"not found" in msg` check explaining that the string
match is intentional — it catches both `"404 not found"` (HTTP status text) and
`"resource not found"` (library error text), both of which are treated as indeterminate
rather than hard failures.

## Success Criteria

- [ ] `setup_venv.sh` aborts immediately on any failed command
- [ ] A broken import surfaces the error message before attempting auto-repair
- [ ] `find_project_root()` fallback resolves to the actual project root, not one above it
- [ ] `install.ps1` warns when overwriting an existing skill directory
- [ ] README and module docstring both document exit 0 for ping 404
- [ ] `test_env_walkup.py` has no dead code (import hook removed)
- [ ] `ping_platform()` has an explanatory comment on the "not found" branch
- [ ] `edison-client` version pin is either confirmed or noted as still pending

## Out of Scope

- Extracting the shared `.env` preamble to `skills/common/env_loader.py` (tracked in TODOS.md)
- Changing the 3-value ping return contract
- Any new test coverage beyond what the fixes require
