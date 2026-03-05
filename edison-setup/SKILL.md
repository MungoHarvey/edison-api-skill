---
name: edison-setup
description: >
  Bootstrap and validate the Edison Scientific platform client environment.
  Use this skill first — before any other Edison skill — whenever the environment
  may not yet be configured, or when troubleshooting authentication and connectivity
  issues. Covers installation, API key configuration, and connection testing.
---

# Edison Setup & Authentication

## Purpose

This skill establishes the foundational environment required by all other Edison skills.
It ensures `edison-client` is installed in an isolated virtual environment, the API key
is available, and the platform connection is live.

**Run this skill when:**
- Setting up Edison for the first time on a machine
- Diagnosing authentication or import errors in other Edison skills
- Onboarding a new project directory that needs Edison access

---

## Prerequisites

- Python 3.10+ on PATH
- `uv` package manager (preferred) or `pip`
- An Edison Scientific API key from: https://platform.edisonscientific.com/profile

---

## Step 1 — Create and Populate the Virtual Environment

Use the adjacent setup script:

```bash
bash edison-skills/edison-setup/scripts/setup_venv.sh
```

This script:
1. Creates `.venv/` in the project root (if absent)
2. Installs `edison-client` and `python-dotenv` via `uv pip`
3. Verifies the import succeeds

---

## Step 2 — Configure the API Key

Create a `.env` file in the project root (never commit this):

```
EDISON_API_KEY=your_api_key_here
```

All Edison scripts load this via `python-dotenv`. The key is **never** hard-coded in scripts.

---

## Step 3 — Pre-flight Environment Check

Before running any other Edison skill, validate the environment with:

```bash
.venv/bin/python edison-skills/edison-setup/scripts/check_environment.py
```

This lightweight check validates (in order):
1. `python-dotenv` is installed
2. `.env` file exists at project root
3. `EDISON_API_KEY` is set and non-empty
4. `edison-client` is importable (auto-repairs if needed)

**Exit codes:**
- `0` — environment ready, proceed to other skills
- `1` — hard failure (broken venv) — re-run `setup_venv.sh` and check for errors
- `2` — soft failure (missing API key) — follow printed instructions to edit `.env`

**Optional:** Add `--ping` flag to also verify live platform connectivity (uses 1 API call):
```bash
.venv/bin/python edison-skills/edison-setup/scripts/check_environment.py --ping
```

---

## Step 4 — Test Connectivity (Advanced)

For detailed connectivity diagnostics beyond the pre-flight check:

```bash
.venv/bin/python edison-skills/edison-setup/scripts/test_connection.py
```

A successful run prints:
```
✓ Edison client imported successfully
✓ API key loaded from .env
✓ Dummy task completed — connection confirmed
```

---

## Environment Layout

```
project-root/
├── .env                          ← API key (git-ignored)
├── .venv/                        ← Virtual environment
└── edison-skills/
    ├── edison-setup/
    │   ├── SKILL.md
    │   └── scripts/
    │       ├── setup_venv.sh
    │       └── test_connection.py
    ├── edison-literature/...
    ├── edison-precedent/...
    ├── edison-molecules/...
    ├── edison-analysis/...
    └── edison-async/...
```

---

## Error Handling

| Error | Likely Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: edison_client` | venv not activated or install failed | Re-run `setup_venv.sh` |
| `AuthenticationError` | Missing or invalid API key | Check `.env` file, regenerate key at platform |
| `ConnectionError` / timeout | Network issue or platform outage | Check https://platform.edisonscientific.com |

