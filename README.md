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

## Quick Start

```bash
# 1. Set up environment (from your project root)
bash edison-skills/edison-setup/scripts/setup_venv.sh

# 2. Add your API key to .env
echo "EDISON_API_KEY=your_key_here" > .env

# 3. Test connectivity
.venv/bin/python edison-skills/edison-setup/scripts/test_connection.py

# 4. Run a literature search
.venv/bin/python edison-skills/edison-literature/scripts/literature_search.py \
    --query "What is the role of TDP-43 in ALS pathogenesis?" \
    --output results/tdp43_literature.md
```

## Directory Structure

```
edison-skills/
├── README.md
├── edison-setup/
│   ├── SKILL.md
│   └── scripts/
│       ├── setup_venv.sh
│       └── test_connection.py
├── edison-literature/
│   ├── SKILL.md
│   └── scripts/
│       └── literature_search.py
├── edison-precedent/
│   ├── SKILL.md
│   └── scripts/
│       └── precedent_search.py
├── edison-molecules/
│   ├── SKILL.md
│   └── scripts/
│       └── chemistry_task.py
├── edison-analysis/
│   ├── SKILL.md
│   └── scripts/
│       └── data_analysis.py
└── edison-async/
    ├── SKILL.md
    └── scripts/
        └── async_batch.py
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
3. Imports Markdown results into Obsidian vault via the `obsidian-mcp` skill

Typical Cowork workflow:
```
1. Write query to temp file
2. Run: .venv/bin/python edison-skills/edison-literature/scripts/literature_search.py
         --query "<query>" --output vault/AI-Usage-Log/edison/<date>-<topic>.md
3. Trigger Obsidian sync
```

## Task Continuation (Chaining)

All scripts support `--continued-from <task_id>` to chain follow-up questions:

```bash
# Initial query
.venv/bin/python ... literature_search.py \
    --query "What are TDP-43 aggregation mechanisms?" \
    --output results/step1.md
# → Note the task ID printed to stderr

# Follow-up (uses same retrieved papers)
.venv/bin/python ... literature_search.py \
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

- Python 3.10+
- `uv` (recommended) or `pip`
- `edison-client` (installed via `setup_venv.sh`)
- `python-dotenv` (installed via `setup_venv.sh`)
