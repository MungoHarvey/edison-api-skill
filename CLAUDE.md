# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Reference

| What | How |
|------|-----|
| Run a skill script | `uv run skills/<skill>/scripts/<script>.py <args>` |
| Environment file | `.env` at project root — variable: `EDISON_PLATFORM_API_KEY` |
| Install uv | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Create venv | `bash skills/edison-setup/scripts/setup_venv.sh` |
| Verify setup | `uv run skills/edison-setup/scripts/check_environment.py` |
| Verify + connectivity | `uv run skills/edison-setup/scripts/check_environment.py --ping` |
| Retry flags | `--max-steps N` (default 100), `--max-retries N` (default 3), `--no-retry` |

> `EDISON_OUTPUT_DIR` is a user shell convention only — scripts do not read it. Pass output paths via `--output`.

## Project Overview

**Edison Scientific Skills Collection** — a monorepo of Anthropic Open Standard skill definitions wrapping the Edison Scientific REST API. Integrates scientific research tasks (literature search, molecular design, dataset analysis) into Claude Code and Claude Cowork workflows.

Plugin skill definitions live in `skills/<name>/SKILL.md` (auto-discovered by Claude Code). Python entry points live in `skills/<name>/scripts/`, co-located with each skill.

## Architecture

### Skill Modules

| Skill | `JobNames` enum | Purpose | Entry Point |
|-------|-----------------|---------|-------------|
| `edison-setup` | — | Env setup, auth validation, pre-flight checks | `setup_venv.sh`, `check_environment.py`, `test_connection.py` |
| `edison-literature` | `LITERATURE` | Cited scientific literature search (PaperQA3-backed) | `literature_search.py` |
| `edison-precedent` | `PRECEDENT` | Binary "has anyone done X?" searches | `precedent_search.py` |
| `edison-molecules` | `MOLECULES` | Chemistry, synthesis, molecular design | `chemistry_task.py` |
| `edison-analysis` | `ANALYSIS` | Biological dataset analysis | `data_analysis.py` |
| `edison-async` | All | Batch submit & poll for concurrent queries | `async_batch.py` |
| `edison-evaluation` | All | Health checks and performance evaluation | `evaluate_skills.py` |

### Script Patterns

All scripts follow the same conventions:
- **PEP 723 inline metadata**: Each script declares `edison-client` and `python-dotenv` as dependencies, so `uv run` works without a pre-built venv
- **`.env` loading**: Walk up from script location (up to 8 levels) to find `.env` via `python-dotenv`
- **Output**: Results to stdout or `--output <path>`; task IDs and logs to stderr
- **Exit codes**: `0` = success, `1` = hard failure, `2` = no successful answer / missing API key / truncated after retries exhausted
- **Task chaining**: Task ID printed to stderr; pass to next call with `--continued-from <task_id>`
- **`--ping` flag**: `check_environment.py --ping` is read via `sys.argv`, not argparse (won't appear in `--help`)
- **Retry on truncation**: All scripts support `--max-steps N` (default 100), `--max-retries N` (default 3), `--no-retry`; on truncation the budget escalates 1.5× per attempt (capped at 300 steps)
- **Shared retry module**: `skills/_common/edison_retry.py` — imported via `sys.path.insert(0, ..._common_path)` in every script; no extra `uv` dependency

### API Client

All scripts use `edison_client.EdisonClient`:
- `api_key` from `EDISON_PLATFORM_API_KEY` env var (falls back to `EDISON_API_KEY` for backward compatibility)
- `run_tasks_until_done(task)` — blocking submission
- `acreate_task(task)` / `aget_task(task_id)` — async batch ops
- `JobNames` enum: `LITERATURE`, `PRECEDENT`, `MOLECULES`, `ANALYSIS`, `DUMMY` (plus `LITERATURE_HIGH` if the installed `edison-client` version supports it)

Use `JobNames.DUMMY` for connectivity tests without consuming API credits.

## Setup

```bash
# 1. Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Create venv and install dependencies (one-time)
bash skills/edison-setup/scripts/setup_venv.sh

# 3. Configure API key
cp .env.example .env   # edit .env, set EDISON_PLATFORM_API_KEY=<your_key>

# 4. Verify
uv run skills/edison-setup/scripts/check_environment.py --ping
```

## Running Skills

```bash
# Literature search
uv run skills/edison-literature/scripts/literature_search.py \
    --query "Your scientific question" --output results/answer.md

# With custom retry settings (useful for complex queries that hit step limits)
uv run skills/edison-literature/scripts/literature_search.py \
    --query "Your scientific question" --max-steps 150 --max-retries 5 --output results/answer.md

# Disable retry entirely
uv run skills/edison-literature/scripts/literature_search.py \
    --query "Your scientific question" --no-retry --output results/answer.md

# Precedent check
uv run skills/edison-precedent/scripts/precedent_search.py \
    --query "Has anyone done X?" --output results/precedent.md

# Molecular design
uv run skills/edison-molecules/scripts/chemistry_task.py \
    --query "Design a compound that..." --output results/molecules.md

# Data analysis (file or inline data)
uv run skills/edison-analysis/scripts/data_analysis.py \
    --query "Are any genes downregulated?" --data path/to/data.csv --output results/analysis.md
uv run skills/edison-analysis/scripts/data_analysis.py \
    --query "Describe this data" --data-inline "col1,col2\nval1,val2"

# Chained follow-up (reuses retrieved papers/context from prior task)
uv run skills/edison-literature/scripts/literature_search.py \
    --query "Which mechanisms are druggable?" --continued-from <task_id>

# Async batch: submit + wait (per-task retry applies to each row)
uv run skills/edison-async/scripts/async_batch.py \
    --input queries.jsonl --output results/batch.md

# Async batch: with retry settings
uv run skills/edison-async/scripts/async_batch.py \
    --input queries.jsonl --max-steps 150 --max-retries 2 --output results/batch.md

# Async batch: fire-and-forget, then poll later (no retry in poll mode)
uv run skills/edison-async/scripts/async_batch.py \
    --input queries.jsonl --submit-only --task-ids-out task_ids.txt
uv run skills/edison-async/scripts/async_batch.py \
    --poll task_ids.txt --output results/batch.md

# Evaluation: quick (free, DUMMY only)
uv run skills/edison-evaluation/scripts/evaluate_skills.py --quick

# Evaluation: full (uses API credits)
uv run skills/edison-evaluation/scripts/evaluate_skills.py \
    --skill all --full --output results/skill_evaluation.md
```

## Development Notes

### Adding a Script to an Existing Skill

1. Create at `skills/<skill>/scripts/<name>.py`
2. Follow the standard pattern:
   - Load `.env` by walking up via `python-dotenv`
   - Import `EdisonClient` and `JobNames` with `ImportError` fallback that exits 1
   - Import retry helpers: `sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "_common"))` then `from edison_retry import add_retry_args, load_api_key, submit_with_retry, truncation_prefix, DEFAULT_MAX_STEPS`
   - Call `add_retry_args(parser)` to add `--max-steps`, `--max-retries`, `--no-retry` flags
   - Define `_build_task(budget: int) -> TaskRequest` closure and call `submit_with_retry(client, _build_task, args.max_steps, max_retries)`
   - Accept `--output`, `--continued-from`, optionally `--verbose`
   - Print task ID to stderr after completion
   - Exit 2 on truncation or `has_successful_answer == False`
3. Update the skill's `SKILL.md` if the interface changes

### JSONL Batch Format

```json
{"name": "LITERATURE", "query": "What is X?"}
{"name": "MOLECULES", "query": "Design Y compound"}
{"name": "ANALYSIS", "query": "Analyze dataset Z"}
```

Comments (`#`) and blank lines are ignored. `name` must be a valid `JobNames` key.

### Data Size Limit

`data_analysis.py` truncates inline data at 20,000 characters (`MAX_DATA_CHARS`). Pre-filter large datasets before submitting.

## Environment

- **Python**: 3.10+ on PATH
- **uv**: Recommended package runner — handles dependencies automatically via PEP 723 inline metadata
- **Dependencies**: `edison-client`, `python-dotenv` (declared inline in each script)
- **API endpoint**: `https://platform.edisonscientific.com` (configured in `edison-client`)
- **API key source**: `https://platform.edisonscientific.com/profile`
- **SessionStart hook**: Automatically checks for `uv`, `.env`, and `EDISON_PLATFORM_API_KEY` when Claude Code starts
