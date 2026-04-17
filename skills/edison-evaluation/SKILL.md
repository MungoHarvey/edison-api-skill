---
name: edison-evaluation
description: >
  This skill should be used when the user wants to test or validate the Edison
  installation, asks "are the skills working", "check Edison health", "validate
  my setup", "run a health check", "test the API key", or wants baseline
  performance metrics. Includes a free connectivity check (DUMMY tasks, no API
  cost) and a comprehensive real-query mode. This skill should be run after
  initial setup or when troubleshooting a specific skill type.
version: 0.1.0
---

# Edison Skill Evaluation

## Purpose

Systematically test all Edison skill types and report on health and performance.

**Use when:**
- Validating Edison setup for the first time
- Troubleshooting a specific skill type that appears broken
- Gathering baseline performance metrics (latency, success rates)
- Running periodic health checks on the installation

---

## Prerequisites

- Edison environment configured (run `edison-setup` skill first if uncertain)
- `.env` file with `EDISON_PLATFORM_API_KEY` set at project root

---

## Usage

### Quick connectivity check (free — no API cost)

```bash
uv run skills/edison-evaluation/scripts/evaluate_skills.py --quick
```

Validates venv, imports, and API key using DUMMY tasks without consuming credits.
Good for rapid diagnostics and CI/CD checks.

### Evaluate a specific skill (real query, uses credits)

```bash
uv run skills/edison-evaluation/scripts/evaluate_skills.py \
    --skill literature \
    --full
```

Valid `--skill` values: `literature`, `literature_high`, `precedent`, `molecules`, `analysis`, `all`

Built-in test queries per skill:
- `literature`: "What is the role of TDP-43 in ALS pathogenesis?"
- `literature_high`: Same query as `literature`, run with `LITERATURE_HIGH` — slower, uses more credits. Requires compatible `edison-client` version.
- `precedent`: "Has anyone performed iPSC differentiation to motor neurons for ALS modelling?"
- `molecules`: "What is the SMILES for aspirin?"
- `analysis`: Embedded test CSV with known gene expression pattern

Note: `literature_high` is excluded from `--skill all` by default (slow and expensive).
Test it explicitly with `--skill literature_high --full`.

### Evaluate all skills

```bash
uv run skills/edison-evaluation/scripts/evaluate_skills.py \
    --skill all \
    --full \
    --output results/evaluation_report.md
```

---

## Output Format

### Summary table

| Skill | Status | Latency (s) | Answer Length | Citations | Details |
|---|---|---|---|---|---|
| literature | ✓ | 12.3 | 450 | 5 | TDP-43 in ALS |
| literature_high | ✓ | 187.4 | 650 | 8 | TDP-43 in ALS (high-reasoning) |
| precedent | ✓ | 8.1 | — | — | iPSC motor neurons |
| molecules | ✓ | 3.2 | 50 | — | Aspirin SMILES |
| analysis | ✓ | 6.5 | 200 | — | Gene expression |

### Detailed results per skill

- Pass/fail based on `has_successful_answer`
- Exact test query used
- Wall-clock latency in seconds
- First 200 characters of response
- Any warnings or issues

---

## Exit Codes

| Code | Meaning |
|---|---|
| `0` | All tested skills passed |
| `1` | One or more skills failed |
| `2` | Environment check failed (missing key, broken venv) |

---

## Quick vs. Full Mode

| Mode | Flag | Cost | Speed | Tests |
|---|---|---|---|---|
| **Quick** | `--quick` | Free | <2s | DUMMY tasks (connectivity + import) |
| **Full** | `--full` | ~1–2 credits per skill | ~30s | Real test queries per skill type |

Use `--quick` for daily checks and CI; use `--full` when onboarding or troubleshooting.

---

## Interpreting Results

**All skills pass:** Installation is healthy — proceed with using other skills.

**One skill fails:** To narrow down the issue, check the Details column for the
test query and run that skill manually with a similar query. If it persists,
verify the API key and platform status at https://platform.edisonscientific.com.

**Answer Length is 0:** Skill returned no substantive answer — may indicate
insufficient literature coverage, a too-specific query, or a data format issue.

**High latency (>30s):** Normal for the first query (cold start). Subsequent
queries should be faster. If consistently slow, verify network and platform status.

---

## API Costs

- `--quick` mode: 0 credits
- `--full` mode: ~1–2 credits per skill type (~4–8 credits for all four skills via `--skill all`)
- `--skill literature_high --full`: ~2–4 credits (higher-quality run, billed separately from `--skill all`)
