# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Edison Scientific Skills Collection** — A monorepo of Anthropic Open Standard skill definitions wrapping the Edison Scientific platform's REST API. Used to integrate AI agents for scientific research tasks (literature search, molecular design, data analysis, etc.) into Claude Code and Claude Cowork workflows.

Six modular skills, each with:
- A `SKILL.md` file defining the skill interface (name, description, prerequisites)
- A `scripts/` directory with one or more Python entry points
- Support for `.env`-based API key management

## Architecture

### Directory Structure

```
edison-skills/
├── README.md                          ← High-level overview and quick start
├── CLAUDE.md                          ← This file
├── .env                               ← API key (git-ignored, user-created)
├── .venv/                             ← Virtual environment (git-ignored, auto-created)
└── {edison-setup, edison-literature, edison-precedent, edison-molecules, edison-analysis, edison-async}/
    ├── SKILL.md                       ← Anthropic Open Standard skill definition
    └── scripts/
        └── {*.py, *.sh}               ← Executable entry points
```

### Skill Modules

| Skill | Job Type | Purpose | Entry Point |
|-------|----------|---------|-------------|
| `edison-setup` | — | Environment setup, auth validation, pre-flight checks | `scripts/setup_venv.sh`, `scripts/test_connection.py`, `scripts/check_environment.py` |
| `edison-literature` | `LITERATURE` | Cited scientific literature search (PaperQA3-backed) | `scripts/literature_search.py` |
| `edison-precedent` | `PRECEDENT` | Binary "has anyone done X?" searches | `scripts/precedent_search.py` |
| `edison-molecules` | `MOLECULES` | Chemistry, synthesis, molecular design | `scripts/chemistry_task.py` |
| `edison-analysis` | `ANALYSIS` | Biological dataset analysis | `scripts/data_analysis.py` |
| `edison-async` | All | Batch submission & polling for concurrent queries | `scripts/async_batch.py` |
| `edison-evaluation` | All | Test and evaluate skill health and performance | `scripts/evaluate_skills.py` |

### Script Patterns

All scripts follow consistent patterns:
- **Environment loading**: Walk up from script location to find `.env` at project root via `python-dotenv`
- **Logging**: Warnings/errors to stderr, results to stdout or `--output` file
- **CLI interface**: Arguments parsed via `argparse`; support `--output` for file saving
- **Task tracking**: Print task ID to stderr for chaining follow-up queries via `--continued-from`
- **JSONL format**: Batch scripts accept task definitions as newline-delimited JSON

### Package Management (Virtual Environment)

- Virtual environment at `.venv/` is created by `setup_venv.sh`
- **Uses `uv` if available** (detected and invoked automatically)
- Falls back to `pip` if `uv` is not installed
- Installs: `edison-client`, `python-dotenv`
- All scripts invoked via `.venv/bin/python <script>`

### API Client

All scripts use `edison_client.EdisonClient` with:
- `api_key` from environment `EDISON_API_KEY`
- `run_tasks_until_done()` for blocking submission
- `acreate_task()` / `aget_task()` for async batch operations
- `JobNames` enum mapping skill names: `LITERATURE`, `PRECEDENT`, `MOLECULES`, `ANALYSIS`, `DUMMY`

## Common Development Commands

### Initial Setup (run from project root)

**Recommended: Using `uv` (fast, deterministic)**

```bash
# 1. Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Create virtual environment and install dependencies
bash edison-skills/edison-setup/scripts/setup_venv.sh
# ^ Script detects uv and uses it automatically; falls back to pip if uv unavailable

# 3. Configure API key
echo "EDISON_API_KEY=your_key_here" > .env

# 4. Verify connectivity
.venv/bin/python edison-skills/edison-setup/scripts/test_connection.py
```

**Alternative: Using standard `pip` (if `uv` not available)**

The setup script falls back to `pip` automatically, but for faster, more reliable environments, `uv` is strongly recommended.

### Activating the Virtual Environment

```bash
# Activate for the current shell session
source .venv/bin/activate

# Or invoke scripts directly without activation
.venv/bin/python edison-skills/<skill>/scripts/<script>.py <args>
```

### Run Individual Skills

```bash
# Literature search
.venv/bin/python edison-skills/edison-literature/scripts/literature_search.py \
    --query "Your scientific question" \
    --output results/answer.md

# Precedent check
.venv/bin/python edison-skills/edison-precedent/scripts/precedent_search.py \
    --query "Has anyone done X?" \
    --output results/precedent.md

# Chained follow-up (reuse papers/context from prior task)
.venv/bin/python edison-skills/edison-literature/scripts/literature_search.py \
    --query "Which mechanisms are druggable?" \
    --continued-from <task_id_from_prior_run> \
    --output results/followup.md

# Batch async submission
.venv/bin/python edison-skills/edison-async/scripts/async_batch.py \
    --input queries.jsonl \
    --output results/batch.md

# Submit-only mode (fire-and-forget, save task IDs for later polling)
.venv/bin/python edison-skills/edison-async/scripts/async_batch.py \
    --input queries.jsonl \
    --submit-only \
    --task-ids-out task_ids.txt

# Poll previously submitted task IDs
.venv/bin/python edison-skills/edison-async/scripts/async_batch.py \
    --poll task_ids.txt \
    --output results/batch.md

# Evaluate all skills (quick connectivity check, free)
.venv/bin/python edison-skills/edison-evaluation/scripts/evaluate_skills.py --quick

# Evaluate all skills (real queries, uses API credits)
.venv/bin/python edison-skills/edison-evaluation/scripts/evaluate_skills.py \
    --skill all \
    --full \
    --output results/skill_evaluation.md
```

## Key Files to Know

| File | Purpose |
|------|---------|
| `README.md` | User-facing overview, quick start, task chaining examples |
| `.gitignore` | Standard exclusions (`.env`, `.venv/`, results, etc.) |
| `edison-setup/SKILL.md` | Setup skill definition, prerequisites, error handling |
| `edison-setup/scripts/setup_venv.sh` | Creates `.venv/`, installs `edison-client` + `python-dotenv` |
| `edison-setup/scripts/check_environment.py` | Pre-flight environment validation before any skill executes |
| `edison-setup/scripts/test_connection.py` | Validates API key and platform connectivity |
| `edison-literature/scripts/literature_search.py` | Main entry point for literature searches; supports `--continued-from`, `--verbose` |
| `edison-async/scripts/async_batch.py` | Concurrent batch submission/polling; supports JSONL input and task ID persistence |
| `edison-evaluation/scripts/evaluate_skills.py` | Test and report on all skill health and performance |

## Development Notes

### Adding a New Script to an Existing Skill

1. Create the script at `<skill>/scripts/<name>.py`
2. Follow the standard pattern:
   - Load `.env` from project root via `python-dotenv`
   - Import `EdisonClient` and `JobNames` (with graceful ImportError fallback)
   - Accept `--output` for optional file saving
   - Print task ID to stderr for chaining
   - Return exit code 2 on "no successful answer" (see `literature_search.py`)
3. Update the `SKILL.md` with new usage examples if the skill's interface changes

### Testing Without API Key

Use `JobNames.DUMMY` for connectivity tests (see `test_connection.py`):
```python
response = client.run_tasks_until_done({"name": JobNames.DUMMY, "query": "ping"})
```

### Task Chaining Workflow

1. Run initial query, capture task ID from stderr
2. For follow-up, pass task ID via `--continued-from`
3. The platform reuses the same retrieved papers/context — faster and more coherent

### JSONL Format for Batch Queries

Each line is a JSON task object:
```json
{"name": "LITERATURE", "query": "What is X?"}
{"name": "MOLECULES", "query": "Design Y compound"}
{"name": "ANALYSIS", "query": "Analyze dataset Z"}
```

Comments and blank lines are ignored. Invalid JSON or missing `name`/`query` fields cause the script to exit with status 1.

## Environment

### Requirements

- **Python**: 3.10+ on PATH
- **Virtual environment**: Uses `.venv/` at project root (created by `setup_venv.sh`)
- **Key dependencies**: `edison-client`, `python-dotenv`

### Package Manager: `uv` (Recommended)

The `setup_venv.sh` script automatically detects and uses `uv` if available. For the best experience:

1. **Install `uv`** (one-time):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Run setup** as usual — it will use `uv` automatically:
   ```bash
   bash edison-skills/edison-setup/scripts/setup_venv.sh
   ```

Benefits of `uv`:
- **~10x faster** than `pip` for dependency resolution
- **Deterministic** — reproducible environments across machines
- Built-in virtual environment management

**Fallback**: If `uv` is not installed, the setup script silently falls back to `pip`.

### API Configuration

- **API endpoint**: https://platform.edisonscientific.com (configured in `edison-client`)
- **API key source**: https://platform.edisonscientific.com/profile
- **Storage**: `.env` file at project root (never committed — add to `.gitignore`)

The `.env` file is **never** committed and contains sensitive credentials.

## Integration Points

### Claude Code
Scripts are invoked directly by Claude Code when it reads `SKILL.md` files. Example prompt:
```
Read the edison-literature SKILL.md, then search for: "What mechanisms underlie X in Y?"
```

### Claude Cowork
Scripts can be invoked as shell commands in desktop task flows. Cowork detects `.venv/` and `.env` automatically.

### External Tools
Scripts write Markdown output suitable for piping to Obsidian, wikis, or other markdown processors.

## GitHub Repository

This repository is version-controlled and hosted on GitHub:

**Remote:** `https://github.com/MungoHarvey/edison-api-skill.git`

**Pushing changes:**
```bash
git add .
git commit -m "Your message"
git push origin main
```

**Key files tracked:**
- All source files (`*.py`, `*.sh`, `*.md`)
- `.gitignore` (standard Python + venv exclusions)
- Excluded from git: `.env`, `.venv/`, `results/`, `__pycache__/`

**Cloning for new environments:**
```bash
git clone https://github.com/MungoHarvey/edison-api-skill.git
cd edison-api-skill
bash edison-skills/edison-setup/scripts/setup_venv.sh
echo "EDISON_API_KEY=your_key" > .env
.venv/bin/python edison-skills/edison-setup/scripts/check_environment.py
```
