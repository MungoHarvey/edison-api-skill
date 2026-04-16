---
name: edison-setup
description: >
  This skill should be used when the user asks to "set up Edison", "install Edison",
  "configure the Edison API key", "fix Edison authentication", "Edison setup", or
  encounters errors like "edison_client not found", "EDISON_API_KEY not set", or
  "ModuleNotFoundError". This skill should be run before any other Edison skill when
  the environment may not yet be configured or when troubleshooting authentication
  and connectivity issues.
version: 0.1.0
---

# Edison Setup & Authentication

## Purpose

This skill bootstraps the foundational environment required by all other Edison skills.
It ensures `edison-client` is available, the API key is configured, and the platform
connection is live.

**This skill should be used when:**
- Setting up Edison for the first time on a machine
- Diagnosing authentication or import errors in other Edison skills
- Onboarding a new project directory that needs Edison access

---

## Prerequisites

- Python 3.10+ on PATH
- `uv` package manager (recommended): `curl -LsSf https://astral.sh/uv/install.sh | sh`
- An Edison Scientific API key from: https://platform.edisonscientific.com/profile

---

## Automatic Environment Detection

A SessionStart hook runs automatically when Claude Code opens a project with this
plugin enabled. It checks for `uv`, `.env`, and `EDISON_API_KEY`, reporting status
and any issues that need attention.

---

## Step 1 — Install uv (if not already installed)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

On Windows: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`

---

## Step 2 — Create the Virtual Environment

Run the setup script from the project root to create `.venv/` and install all
dependencies. This only needs to be done once:

```bash
bash edison-setup/scripts/setup_venv.sh
```

This creates `.venv/` using `uv` (or `pip` as fallback), installs `edison-client`
and `python-dotenv`, and verifies the imports succeed. All other Edison skills
reuse this venv — no per-run dependency resolution.

---

## Step 3 — Configure the API Key

The setup script does **not** create `.env` — only `.env.example` ships with the repo.
Copy it and add the real key:

```bash
cp .env.example .env
```

Then edit `.env` and replace `your_api_key_here` with the actual API key:

```
EDISON_API_KEY=ek_live_...
```

Get an API key at: https://platform.edisonscientific.com/profile

**Important:** `.env` is gitignored — never commit it. All Edison scripts load the
key via `python-dotenv` at runtime. The key is never hard-coded in scripts.

---

## Step 4 — Verify Setup

Run the pre-flight check to validate the full environment:

```bash
uv run edison-setup/scripts/check_environment.py
```

This validates (in order):
1. `python-dotenv` is installed
2. `.env` file exists at project root
3. `EDISON_API_KEY` is set and non-empty
4. `edison-client` is importable

**Exit codes:**
- `0` — environment ready
- `1` — hard failure (missing dependencies) — re-run `setup_venv.sh`
- `2` — soft failure (missing API key) — copy `.env.example` to `.env` and add key

Add `--ping` to also verify live platform connectivity (uses 1 API call):

```bash
uv run edison-setup/scripts/check_environment.py --ping
```

---

## Step 5 — Test Connectivity

For detailed connectivity diagnostics:

```bash
uv run edison-setup/scripts/test_connection.py
```

A successful run prints:
```
✓ Edison client imported successfully
✓ API key loaded from .env
✓ Dummy task completed — connection confirmed
```

---

## Error Handling

| Error | Likely Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: edison_client` | `uv` not installed or network issue | Install `uv`, check network |
| `AuthenticationError` | Missing or invalid API key | Check `.env`, regenerate key at platform |
| `ConnectionError` / timeout | Network issue or platform outage | Check https://platform.edisonscientific.com |
| Exit code 2 | `EDISON_API_KEY` not in `.env` | Add key to `.env` file at project root |

---

## Additional Resources

- **[`references/gotchas.md`](references/gotchas.md)** — common pitfalls: API key handling,
  non-interactive shells, timeout behaviour, Kosmos limitations, response schema gotchas,
  and how to verify supported job types at runtime.
