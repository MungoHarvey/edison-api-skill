---
name: edison-analysis
description: >
  Submit biological datasets to the Edison Analysis agent to receive detailed,
  question-driven data analyses. Use when you have a dataset (e.g. RNA-seq counts,
  screening results, proteomic data) and a biological question you want the agent
  to answer about it. Distinct from literature or precedent search — this skill
  operates on your own data, not the published literature.
---

# Edison Data Analysis

## Purpose

This skill invokes `JobNames.ANALYSIS` — the Edison agent that accepts biological
datasets and returns detailed analyses in response to a research question.

**Use this skill when:**
- You have a dataset and want an AI-driven biological interpretation
- Running exploratory analyses on RNA-seq, screening hits, or proteomics data
- Asking the agent to identify patterns, pathways, or anomalies in your data
- Wanting a natural-language analysis report on numerical results

**Do NOT use for:**
- Questions that don't require your own data → use `edison-literature` or `edison-precedent`
- Chemistry/molecule tasks → use `edison-molecules`

---

## Prerequisites

- Edison environment configured (run `edison-setup` skill first)
- `.env` file with `EDISON_API_KEY` set
- **Run pre-flight check:** `.venv/bin/python edison-skills/edison-setup/scripts/check_environment.py`
- Your dataset prepared in a text-parseable format (CSV, TSV, or pasted table)

---

## Usage

### Single dataset + question

```bash
.venv/bin/python edison-skills/edison-analysis/scripts/data_analysis.py \
    --query "Which genes are most differentially expressed between DMSO control and TDP-43 knockdown?" \
    --data data/rnaseq_counts.csv
```

### Inline data (small tables)

```bash
.venv/bin/python edison-skills/edison-analysis/scripts/data_analysis.py \
    --query "Identify outlier compounds by z-score" \
    --data-inline "compound,zscore\nCompoundA,3.2\nCompoundB,-0.4\nCompoundC,4.8"
```

### With output saved

```bash
.venv/bin/python edison-skills/edison-analysis/scripts/data_analysis.py \
    --query "..." \
    --data data/my_data.csv \
    --output results/analysis_report.md
```

### Follow-up on prior analysis

```bash
.venv/bin/python edison-skills/edison-analysis/scripts/data_analysis.py \
    --query "From the previous result, which of those pathways are known ALS-relevant?" \
    --continued-from <task_id>
```

---

## Data Format Guidelines

The analysis agent works best with:
- **CSV/TSV** files with a header row
- Clearly labelled columns (gene names, compound IDs, sample groups)
- Reasonable size — the agent reads data as text, so very large files should be
  pre-filtered to relevant subsets before submission

For RNA-seq workflows, consider pre-filtering to the top 500–1000 genes by variance
before passing to Edison, rather than submitting full count matrices.

---

## Output Format

```
# Edison Data Analysis Report
*Generated: YYYY-MM-DD HH:MM*

## Query
<your question>

## Analysis Result
<agent's detailed answer — may include tables, pathway terms, statistical observations>

*Task ID: `<uuid>`*
```

---

## Claude Code Integration

```
Use the Edison analysis skill to analyse data/drugseq_zscores.csv.
Ask: "Which compound clusters show the most orthogonal transcriptional signatures
to our positive control?"
Save the report to results/drugseq_analysis.md
```

## Claude Cowork Integration

Cowork can:
1. Export a filtered dataset from your pipeline to CSV
2. Pass it to `data_analysis.py` with a biological question
3. Import the Markdown report back into your notes/Obsidian vault

---

## Workflow Integration with DRUGseq Pipeline

For your DRUGseq workflow, a typical sequence would be:

1. Run DESeq2 / z-score normalisation pipeline → export `top_hits.csv`
2. Submit to Edison Analysis: "Which of these hits have mechanisms consistent with
   restoring TDP-43 nuclear localisation?"
3. Use the task ID to ask follow-up: "Which of those compounds have known CNS bioavailability?"
4. Cross-reference results with `edison-literature` for deep evidence
