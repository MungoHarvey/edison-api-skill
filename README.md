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

### 1. Clone the Repository

```bash
# Clone into your Claude Code projects folder
cd ~/Projects  # or your preferred location
git clone https://github.com/MungoHarvey/edison-api-skill.git edison-skills
cd edison-skills
```

### 2. Create Output Directory (Optional but Recommended)

```bash
# Create a dedicated folder for Edison results
mkdir -p ~/Documents/Edison-Outputs

# Or customize the path:
# mkdir -p ~/Claude/Edison-Results
# mkdir -p ~/Research/Edison-Outputs
```

### 3. Initialize Virtual Environment

```bash
# From the project root (edison-skills/)
bash edison-skills/edison-setup/scripts/setup_venv.sh
```

### 4. Configure API Key

```bash
# Add your Edison Scientific API key (never commit this!)
echo "EDISON_API_KEY=your_api_key_here" > .env

# Optional: Add output directory to .env
echo "EDISON_OUTPUT_DIR=$HOME/Documents/Edison-Outputs" >> .env
```

Get your API key from: https://platform.edisonscientific.com/profile

### 5. Verify Setup

```bash
# Run pre-flight check
.venv/bin/python edison-skills/edison-setup/scripts/check_environment.py --ping

# Should output:
# ✓ Edison environment is ready
```

### 6. Try Your First Query

```bash
# Literature search with results saved to output directory
.venv/bin/python edison-skills/edison-literature/scripts/literature_search.py \
    --query "What is the role of TDP-43 in ALS pathogenesis?" \
    --output ~/Documents/Edison-Outputs/tdp43_literature.md

# Or if you set EDISON_OUTPUT_DIR in .env:
# --output $EDISON_OUTPUT_DIR/tdp43_literature.md
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
.venv/bin/python edison-skills/edison-literature/scripts/literature_search.py \
    --query "What is the role of TDP-43 in ALS pathogenesis?" \
    --output ~/Documents/Edison-Outputs/tdp43.md
```

**In Claude Cowork:**
Create a desktop task:
```
Task: TDP-43 Literature Search
1. Run command: .venv/bin/python edison-skills/edison-literature/scripts/literature_search.py
                --query "What is the role of TDP-43 in ALS pathogenesis?"
                --output ${EDISON_OUTPUT_DIR}/tdp43.md
2. Import to Obsidian from ~/Documents/Edison-Outputs/
```

Both use the same script and produce the same output — the skill is **environment-agnostic**.

---

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
.venv/bin/python edison-skills/edison-literature/scripts/literature_search.py \
    --query "Your question" \
    --output $(date +%Y%m%d)_question.md
```

**Option 2: Explicit full path (per command)**
```bash
# Linux/Mac
.venv/bin/python edison-skills/edison-literature/scripts/literature_search.py \
    --query "Your question" \
    --output ~/Documents/Edison-Outputs/$(date +%Y%m%d)_question.md

# Windows (PowerShell)
python edison-skills\edison-literature\scripts\literature_search.py `
    --query "Your question" `
    --output "$HOME\Documents\Edison-Outputs\question.md"
```

**Option 3: Obsidian vault (if using Obsidian)**
```bash
.venv/bin/python edison-skills/edison-literature/scripts/literature_search.py \
    --query "Your question" \
    --output ~/Library/Mobile\ Documents/iCloud\~md\~obsidian/Documents/vault-name/AI-Usage-Log/edison/question.md
```

### Typical Cowork Workflow

```
1. Set EDISON_OUTPUT_DIR environment variable in .env or shell config
2. Run: .venv/bin/python edison-skills/edison-literature/scripts/literature_search.py
         --query "<query>" --output $(date +%Y-%m-%d)_topic.md
3. Results automatically appear in ~/Documents/Edison-Outputs/
4. (Optional) If Obsidian vault path is set, trigger obsidian-mcp sync
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
