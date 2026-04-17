# Edison Scientific Skills Collection

A set of Anthropic Open Standard skill files for integrating the Edison Scientific
platform (`edison-client`) into Claude Code and Claude Cowork workflows.

## Overview

Edison Scientific provides AI agents for scientific research tasks. This skill
collection wraps the platform's REST API with structured skill definitions and
ready-to-use Python scripts.

## Skills

| Skill | Job | Use When |
|---|---|---|
| `edison-setup` | — | First-time setup, auth validation |
| `edison-literature` | `LITERATURE` | Open scientific questions needing cited answers |
| `edison-precedent` | `PRECEDENT` | "Has anyone ever done X?" binary queries |
| `edison-molecules` | `MOLECULES` | Chemistry, synthesis, molecular design |
| `edison-analysis` | `ANALYSIS` | Analysing your own biological datasets |
| `edison-async` | All | Running multiple queries concurrently |
| `edison-evaluation` | All | Health checks and performance evaluation |

## Install

### 1. Install uv (if not already)

```bash
# Unix/Mac
curl -LsSf https://astral.sh/uv/install.sh | sh
# Windows
winget install --id=astral-sh.uv
# or: powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. Clone the repo and add your API key

```bash
git clone https://github.com/MungoHarvey/edison-api-skill.git
cd edison-api-skill
cp .env.example .env   # then edit .env: EDISON_API_KEY=<your-key>
# Get your key from: https://platform.edisonscientific.com/profile
```

Alternatively, export the key without a file:
```bash
export EDISON_API_KEY=<your-key>
# Or set EDISON_ENV_FILE=/path/to/.env.edison for a dedicated config file
```

### 3. Register skills in Claude Code (choose one)

```bash
# Option A — user-level (available in all projects):
bash install.sh --user
# On Windows PowerShell: .\install.ps1 -User

# Option B — print the --plugin-dir flag for project-level use:
bash install.sh --plugin-dir

# Option C — pass --plugin-dir directly to Claude Code:
# Add --plugin-dir /path/to/edison-api-skill to your Claude Code command
```

### 4. Verify

```bash
uv run skills/edison-setup/scripts/check_environment.py
```

### That's it

```bash
uv run skills/edison-literature/scripts/literature_search.py \
    --query "What causes Alzheimer's?" --output results/answer.md
```

Once installed, skills activate automatically based on your prompts — no need to
reference SKILL.md files manually. Ask a literature question, and Claude will invoke
`edison-literature`. Ask to design a molecule, and it invokes `edison-molecules`.

---

## Setup for Claude

> These instructions are for Claude Code to follow when a user asks to set up this plugin.

When the user asks to "set up Edison" or "configure the Edison plugin", execute these steps in order:

**Step 1 — Check for uv**

```bash
uv --version
```

If missing, install it:
- macOS/Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Windows: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`

After installing, ask the user to restart their terminal or run `source ~/.bashrc` (or equivalent), then confirm uv is available before continuing.

**Step 2 — Create the virtual environment**

From the plugin root directory:

```bash
bash skills/edison-setup/scripts/setup_venv.sh
```

This creates `.venv/` and installs `edison-client` and `python-dotenv`. Only run once.

**Step 3 — Configure the API key**

Check whether `.env` already exists. If not:

```bash
cp .env.example .env
```

Then check whether `EDISON_API_KEY` is already set in `.env`. If it contains `your_api_key_here` or is missing, tell the user:

> "Please get your API key from https://platform.edisonscientific.com/profile, then add it to `.env` as: `EDISON_API_KEY=<your_key>`"

Wait for the user to confirm before continuing.

**Step 4 — Verify setup**

```bash
uv run skills/edison-setup/scripts/check_environment.py --ping
```

- Exit code `0` = ready (includes a `⚠` warning if ping returned 404 — platform-side, key is fine).
- Exit code `1` = hard failure — show the error output and help the user fix it.
- Exit code `2` = API key missing or invalid — re-prompt the user to check `.env`.

**Step 5 — Confirm to user**

Report which checks passed (uv, .venv, .env, API key) and confirm Edison is ready for use. Suggest a test query:

```bash
uv run skills/edison-literature/scripts/literature_search.py \
    --query "What is the role of TDP-43 in ALS pathogenesis?" \
    --output results/test_literature.md
```

---

## Quick Start

The `uv run` path (above) handles everything automatically. If you prefer a persistent
venv, run `bash skills/edison-setup/scripts/setup_venv.sh` once, then invoke scripts
with `.venv/bin/python` (Unix/Mac) or `.venv\Scripts\python.exe` (Windows).

```bash
uv run skills/edison-literature/scripts/literature_search.py \
    --query "What is the role of TDP-43 in ALS pathogenesis?" \
    --output results/tdp43_literature.md
```

## Integration: Claude Code vs. Claude Cowork

All Edison skills work in **both** Claude Code and Claude Cowork with the same `SKILL.md` files and Python scripts. The environments differ in how they invoke scripts:

| Feature | Claude Code | Claude Cowork |
|---------|-------------|---------------|
| **Invocation** | User gives Claude Code a prompt; Claude reads SKILL.md and invokes script | User creates desktop task flows; Cowork runs scripts via shell commands |
| **Input** | Natural language questions in chat | Template-based or manual task definitions |
| **Output Handling** | Results returned in chat; files saved to `--output` path | Results saved to files and auto-imported to Obsidian/notes |
| **Real-time feedback** | Immediate (blocking, in chat) | Asynchronous (tasks complete in background) |
| **Best for** | Interactive research, quick lookups | Batch processing, automation workflows |

### Example: Same Skill in Both Environments

**In Claude Code:**
```
Read the edison-literature SKILL.md, then search for:
"What is the role of TDP-43 in ALS pathogenesis?"
Save results to ~/Documents/Edison-Outputs/tdp43.md
```
Claude Code reads SKILL.md, executes:
```bash
uv run skills/edison-literature/scripts/literature_search.py \
    --query "What is the role of TDP-43 in ALS pathogenesis?" \
    --output ~/Documents/Edison-Outputs/tdp43.md
```

**In Claude Cowork:**
Create a desktop task:
```
Task: TDP-43 Literature Search
1. Run command: uv run skills/edison-literature/scripts/literature_search.py
                --query "What is the role of TDP-43 in ALS pathogenesis?"
                --output ${EDISON_OUTPUT_DIR}/tdp43.md
2. Import to Obsidian from ~/Documents/Edison-Outputs/
```

Both use the same script and produce the same output — the skill is **environment-agnostic**.

---

## Directory Structure

```
edison-api-skill/
├── .claude-plugin/
│   └── plugin.json              ← Claude Code plugin manifest
├── hooks/
│   ├── hooks.json               ← SessionStart hook (auto-checks environment)
│   └── scripts/check_env.sh
└── skills/                      ← Skill definitions and scripts (auto-discovered)
    ├── edison-setup/
    │   ├── SKILL.md
    │   ├── scripts/             ← setup_venv.sh, check_environment.py, test_connection.py
    │   └── references/
    ├── edison-literature/
    │   ├── SKILL.md
    │   ├── scripts/             ← literature_search.py
    │   └── references/
    ├── edison-precedent/
    │   ├── SKILL.md
    │   └── scripts/             ← precedent_search.py
    ├── edison-molecules/
    │   ├── SKILL.md
    │   └── scripts/             ← chemistry_task.py
    ├── edison-analysis/
    │   ├── SKILL.md
    │   ├── scripts/             ← data_analysis.py
    │   └── references/
    ├── edison-async/
    │   ├── SKILL.md
    │   ├── scripts/             ← async_batch.py
    │   └── references/
    └── edison-evaluation/
        ├── SKILL.md
        ├── scripts/             ← evaluate_skills.py
        └── test_queries/
```

## Integration: Claude Code

Claude Code reads the SKILL.md files and invokes adjacent scripts. Example prompts:

```
# Literature search
Read the edison-literature SKILL.md, then search for evidence on:
"What mechanisms underlie TDP-43 nuclear depletion in ALS?"
Save the result to results/tdp43_nuclear.md

# Precedent check
Read the edison-precedent SKILL.md, then check:
"Has anyone performed DRUGseq screening in ALS iPSC motor neurons?"

# Async batch
Read the edison-async SKILL.md, then submit all queries in
edison-queries/als_targets.jsonl and save results to results/als_batch.md
```

## Integration: Claude Cowork

Cowork can automate Edison queries as desktop tasks:
1. Generates query files from templates
2. Invokes scripts via shell commands
3. Saves Markdown results to a user-configurable location
4. Optionally imports into Obsidian vault via the `obsidian-mcp` skill

### Output Location Configuration

All scripts support flexible `--output` paths. Set your preferred location in one of these ways:

**Option 1: Environment variable (recommended)**
```bash
export EDISON_OUTPUT_DIR="$HOME/Documents/Edison-Outputs"
# or for Windows: set EDISON_OUTPUT_DIR=C:\Users\YourName\Documents\Edison-Outputs
```

Then use scripts with relative paths:
```bash
uv run skills/edison-literature/scripts/literature_search.py \
    --query "Your question" \
    --output $(date +%Y%m%d)_question.md
```

**Option 2: Explicit full path (per command)**
```bash
# Linux/Mac
uv run skills/edison-literature/scripts/literature_search.py \
    --query "Your question" \
    --output ~/Documents/Edison-Outputs/$(date +%Y%m%d)_question.md

# Windows (PowerShell)
python skills/edison-literature/scripts/literature_search.py `
    --query "Your question" `
    --output "$HOME\Documents\Edison-Outputs\question.md"
```

**Option 3: Obsidian vault (if using Obsidian)**
```bash
uv run skills/edison-literature/scripts/literature_search.py \
    --query "Your question" \
    --output ~/Library/Mobile\ Documents/iCloud\~md\~obsidian/Documents/vault-name/AI-Usage-Log/edison/question.md
```

### Typical Cowork Workflow

```
1. Set EDISON_OUTPUT_DIR environment variable in .env or shell config
2. Run: uv run skills/edison-literature/scripts/literature_search.py
         --query "<query>" --output $(date +%Y-%m-%d)_topic.md
3. Results automatically appear in ~/Documents/Edison-Outputs/
4. (Optional) If Obsidian vault path is set, trigger obsidian-mcp sync
```

## Task Continuation (Chaining)

All scripts support `--continued-from <task_id>` to chain follow-up questions:

```bash
# Initial query
uv run skills/edison-literature/scripts/literature_search.py \
    --query "What are TDP-43 aggregation mechanisms?" \
    --output results/step1.md
# → Note the task ID printed to stderr

# Follow-up (uses same retrieved papers)
uv run skills/edison-literature/scripts/literature_search.py \
    --query "Which of those mechanisms are druggable?" \
    --continued-from <task_id_from_step1> \
    --output results/step2.md
```

## API Key

Obtain your key from: https://platform.edisonscientific.com/profile

Store in `.env` at your project root:
```
EDISON_API_KEY=your_api_key_here
```

Add `.env` to `.gitignore` — never commit your key.

## Dependencies

- Python 3.11+
- `uv` (recommended) — used for venv creation and script execution
- `edison-client` and `python-dotenv` — installed into `.venv/` by `setup_venv.sh`
