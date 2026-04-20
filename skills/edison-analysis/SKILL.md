---
name: edison-analysis
description: >
  This skill should be used when the user has a biological dataset and wants
  AI-driven analysis, asks to "analyse this data", "interpret these results",
  "find patterns in this CSV", "identify differentially expressed genes",
  "analyse screening hits", or wants a natural-language report on numerical
  data. Requires the user's own dataset (CSV, TSV, or inline table). Distinct
  from literature and precedent search — this skill operates on the user's
  data, not the published literature.
version: 0.1.0
---

# Edison Data Analysis

## Purpose

Invoke `JobNames.ANALYSIS` — the Edison agent that accepts biological datasets
and returns detailed analyses in response to a research question.

**Use for:**
- Datasets needing AI-driven biological interpretation
- Exploratory analyses on RNA-seq, screening hits, or proteomics data
- Identifying patterns, pathways, or anomalies in numerical results
- Generating a natural-language analysis report on experimental data

**Do NOT use for:**
- Questions that don't require your own data — use `edison-literature` or `edison-precedent`
- Chemistry or molecule tasks — use `edison-molecules`

---

## Prerequisites

- Edison environment configured (run `edison-setup` skill first if uncertain)
- `.env` file with `EDISON_PLATFORM_API_KEY` set at project root
- Dataset prepared in a text-parseable format (CSV, TSV, or pasted table)

---

## Usage

### Dataset from file

```bash
uv run skills/edison-analysis/scripts/data_analysis.py \
    --query "Which genes are most differentially expressed between DMSO control and TDP-43 knockdown?" \
    --data data/rnaseq_counts.csv
```

### Inline data (small tables)

```bash
uv run skills/edison-analysis/scripts/data_analysis.py \
    --query "Identify outlier compounds by z-score" \
    --data-inline "compound,zscore\nCompoundA,3.2\nCompoundB,-0.4\nCompoundC,4.8"
```

`--data` and `--data-inline` are mutually exclusive. Data is truncated at 20,000 characters.

### With output saved

```bash
uv run skills/edison-analysis/scripts/data_analysis.py \
    --query "..." \
    --data data/my_data.csv \
    --output results/analysis_report.md
```

### Follow-up on prior analysis

```bash
uv run skills/edison-analysis/scripts/data_analysis.py \
    --query "From the previous result, which of those pathways are known ALS-relevant?" \
    --continued-from <task_id>
```

---

## Data Format Guidelines

The analysis agent works best with:
- **CSV/TSV** files with a header row
- Clearly labelled columns (gene names, compound IDs, sample groups)
- Reasonable size — the agent reads data as text

For RNA-seq workflows, pre-filter to the top 500–1,000 genes by variance before
submission rather than sending full count matrices. Data exceeding 20,000 characters
is automatically truncated.

---

## Output Format

```markdown
# Edison Data Analysis Report
*Generated: YYYY-MM-DD HH:MM*

## Query
<your question>

## Analysis Result
<agent's detailed answer — may include tables, pathway terms, statistical observations>

*Task ID: `<uuid>`*
```

---

## Retry on Truncation

Large datasets or complex analyses can hit the agent's step limit. The script retries
automatically with a larger budget (1.5× per attempt, up to 300 steps).

```bash
# Increase starting budget (default: 100)
uv run skills/edison-analysis/scripts/data_analysis.py \
    --query "..." --data data.csv --max-steps 150

# Allow more retries (default: 3)
uv run skills/edison-analysis/scripts/data_analysis.py \
    --query "..." --data data.csv --max-retries 5

# Disable retry
uv run skills/edison-analysis/scripts/data_analysis.py \
    --query "..." --data data.csv --no-retry
```

Exit code `2` means the result was truncated after all retries exhausted.

---

## Example Workflow

1. Prepare dataset in CSV format (e.g. DESeq2 output, z-scores, screening hits)
2. Run analysis with a specific biological question
3. Review the report and use the task ID for follow-up questions
4. Cross-reference findings with `edison-literature` for supporting evidence
