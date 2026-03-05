---
name: edison-literature
description: >
  Run deep, cited scientific literature searches using Edison's PaperQA3-backed
  Literature agent. Use when a user asks for a review of published evidence,
  wants citations for a scientific claim, or needs a comprehensive answer drawn
  from the primary literature. Distinct from Precedent search: Literature returns
  synthesised, referenced answers; Precedent answers binary "has anyone done X" queries.
---

# Edison Literature Search

## Purpose

This skill invokes `JobNames.LITERATURE` on the Edison platform — a PaperQA3-powered
agent that searches scientific databases, retrieves full papers, and synthesises a
cited answer to an open scientific question.

**Use this skill when:**
- Asking open-ended scientific questions requiring evidence from published papers
- Generating literature-backed summaries (e.g. for grant writing, research updates)
- Needing formatted answers with references for a specific biological or clinical question
- Running follow-up queries that build on a prior literature search

**Do NOT use for:**
- Binary "has anyone done X" questions → use `edison-precedent` instead
- Chemistry/synthesis questions → use `edison-molecules`
- Analysing your own datasets → use `edison-analysis`

---

## Prerequisites

- Edison environment configured (run `edison-setup` skill first)
- `.env` file with `EDISON_API_KEY` set
- **Run pre-flight check:** `.venv/bin/python edison-skills/edison-setup/scripts/check_environment.py`

---

## Usage

### Single query (blocking)

```bash
.venv/bin/python edison-skills/edison-literature/scripts/literature_search.py \
    --query "What are the mechanisms by which TDP-43 aggregation impairs motor neuron function in ALS?"
```

### With verbose output (includes full paper metadata)

```bash
.venv/bin/python edison-skills/edison-literature/scripts/literature_search.py \
    --query "..." \
    --verbose
```

### Follow-up / chained query

```bash
.venv/bin/python edison-skills/edison-literature/scripts/literature_search.py \
    --query "From the previous answer, which of those mechanisms are therapeutically tractable?" \
    --continued-from <task_id_from_prior_run>
```

### Output to file

```bash
.venv/bin/python edison-skills/edison-literature/scripts/literature_search.py \
    --query "..." \
    --output results/literature_output.md
```

---

## Output Format

By default the script prints to stdout:

```
=== ANSWER ===
<synthesised answer text>

=== FORMATTED ANSWER (with references) ===
<answer with inline citations and reference list>

=== TASK ID ===
<uuid>  ← save this if you want to run follow-up queries
```

With `--output`, the formatted answer is saved as Markdown.

---

## Key Fields Returned

| Field | Description |
|---|---|
| `answer` | Plain text synthesised answer |
| `formatted_answer` | Answer with inline citations and a reference list |
| `has_successful_answer` | Boolean — `False` means insufficient literature found |

With `--verbose`, also available:
- `environment_frame` — full paper contexts, metadata, and raw retrieval data
- `agent_state` — step-by-step agent reasoning trace

---

---

## Error Handling

| Error | Cause | Fix |
|---|---|---|
| `has_successful_answer = False` | Insufficient literature coverage | Rephrase query; broaden or narrow scope |
| `AuthenticationError` | Bad API key | Check `.env`; regenerate at platform |
| Timeout | Long-running search | Use `--async` mode (see `edison-async` skill) |
