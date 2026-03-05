---
name: edison-evaluation
description: >
  Evaluate the health and performance of all Edison skills by running test queries
  against each skill type. Reports on success rates, latency, answer quality, and
  connectivity. Use this skill to validate skill installation, test API key access,
  and baseline performance metrics. Includes both fast "connectivity only" mode (DUMMY tasks,
  no cost) and comprehensive "real queries" mode (uses API credits).
---

# Edison Skill Evaluation

## Purpose

This skill systematically tests all Edison skill types and reports on their health and performance.

**Use this skill when:**
- Setting up Edison for the first time (validate all skills are working)
- Troubleshooting issues with a specific skill type
- Gathering baseline performance metrics (latency, success rates)
- Validating API key access and platform connectivity
- Running periodic health checks on the installation

---

## Prerequisites

- Edison environment configured (run `edison-setup` skill first)
- `.env` file with `EDISON_API_KEY` set
- **Run pre-flight check:** `.venv/bin/python edison-skills/edison-setup/scripts/check_environment.py`

---

## Usage

### Quick connectivity check (DUMMY tasks only, no API cost)

```bash
.venv/bin/python edison-skills/edison-evaluation/scripts/evaluate_skills.py --quick
```

Validates venv, imports, and API key without consuming credits. Good for rapid diagnostics.

### Evaluate a specific skill (real query, uses credits)

```bash
.venv/bin/python edison-skills/edison-evaluation/scripts/evaluate_skills.py \
    --skill literature \
    --full
```

Runs a known test query against the specified skill:
- `literature`: "What is the role of TDP-43 in ALS pathogenesis?"
- `precedent`: "Has anyone performed iPSC differentiation to motor neurons for ALS modelling?"
- `molecules`: "What is the SMILES for aspirin?"
- `analysis`: Embedded test CSV with known gene expression pattern

### Evaluate all skills (real queries, uses credits)

```bash
.venv/bin/python edison-skills/edison-evaluation/scripts/evaluate_skills.py \
    --skill all \
    --full
```

### Save report to file

```bash
.venv/bin/python edison-skills/edison-evaluation/scripts/evaluate_skills.py \
    --skill all \
    --full \
    --output results/evaluation_report.md
```

---

## Output Format

The evaluation report is Markdown with two sections:

### 1. Summary Table

| Skill | Status | Latency (s) | Answer Length | Citations | Details |
|---|---|---|---|---|---|
| literature | ✓ | 12.3 | 450 | 5 | PII test: TDP-43 in ALS |
| precedent | ✓ | 8.1 | — | — | iPSC motor neurons |
| molecules | ✓ | 3.2 | 50 | — | Aspirin SMILES lookup |
| analysis | ✓ | 6.5 | 200 | — | Gene expression analysis |

### 2. Detailed Results

Each skill includes:
- **Pass/fail:** `has_successful_answer` field from response
- **Query:** The exact test query used
- **Latency:** Wall-clock time (seconds)
- **Answer preview:** First 200 characters of response
- **Status:** Any warnings or issues

---

## Exit Codes

| Code | Meaning |
|---|---|
| `0` | All tested skills passed |
| `1` | One or more skills failed |
| `2` | Environment check failed (missing key, broken venv) |

---

## Interpretation Guide

### All skills pass (green)
✓ Edison installation is healthy. Proceed to use other skills.

### One skill fails (yellow/red)
- Check the "Details" column for the specific test query
- Try running that skill manually (e.g. `literature_search.py`) with a similar query
- If the issue persists, check the API key and platform status

### "Answer Length" is 0
The skill succeeded but returned no substantive answer. This can indicate:
- Literature: insufficient coverage of the topic in available databases
- Precedent: the question is too specific or niche
- Molecules: the SMILES lookup failed
- Analysis: the CSV format was misinterpreted

### High latency (>30s)
- Normal for first query (cold start on platform)
- Subsequent queries should be faster
- If consistently slow, check network and platform status

---

## Quick vs. Full Mode

| Mode | Flag | Cost | Speed | Tests |
|---|---|---|---|---|
| **Quick** | `--quick` (default) | Free | <2s | DUMMY tasks only (connectivity + import validation) |
| **Full** | `--full` | ~1-2 credits per skill | ~30s | Real test queries for each skill type |

**Recommendation:** Use `--quick` in CI/CD and daily checks; use `--full` when onboarding or troubleshooting.

---

## Claude Code Integration

```
Use the Edison evaluation skill to test all skills and save a report:
Read edison-evaluation/SKILL.md, then run --skill all --full
and save to results/skill_evaluation.md
```

Claude Code will execute the script, parse the report, and display results.

---

## API Costs

- **--quick mode:** 0 credits (DUMMY tasks are free)
- **--full mode:** ~1-2 credits per skill type (4 skills = ~4-8 credits for complete evaluation)

---

## Example Workflow

```bash
# 1. Quick health check (instant, free)
.venv/bin/python edison-skills/edison-evaluation/scripts/evaluate_skills.py --quick

# 2. If quick passes, run full evaluation
.venv/bin/python edison-skills/edison-evaluation/scripts/evaluate_skills.py \
    --skill all \
    --full \
    --output results/eval_$(date +%Y%m%d).md

# 3. Review report
cat results/eval_$(date +%Y%m%d).md

# 4. If a specific skill fails, test it in isolation
.venv/bin/python edison-skills/edison-literature/scripts/literature_search.py \
    --query "What is the role of TDP-43 in ALS pathogenesis?" \
    --output results/tdp43_test.md
```
