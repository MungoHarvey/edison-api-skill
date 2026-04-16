---
name: edison-precedent
description: >
  This skill should be used when the user asks a binary scientific precedent question
  such as "has anyone done X", "has X been tested in Y", "has this been tried before",
  "is there precedent for X", or "has anyone used X to treat Y". Use for targeted
  yes/no feasibility checks against the scientific literature — not for open-ended
  review questions (use edison-literature for those) or chemistry tasks (use
  edison-molecules for those).
version: 0.1.0
---

# Edison Precedent Search

## Purpose

Invoke `JobNames.PRECEDENT` — the Edison "HasAnyone" agent — designed to answer
targeted precedent questions with a clear yes/no and cited supporting evidence.

**Use for:**
- "Has anyone ever done X?" in a scientific context
- Checking whether a drug/target/model combination has been reported
- Rapid feasibility checks before designing experiments
- Scoping a research area to identify gaps vs. existing work

**Do NOT use for:**
- Open-ended mechanistic or review questions — use `edison-literature`
- Chemistry synthesis planning — use `edison-molecules`

---

## Prerequisites

- Edison environment configured (run `edison-setup` skill first if uncertain)
- `.env` file with `EDISON_API_KEY` set at project root

---

## Usage

### Single precedent query

```bash
uv run edison-precedent/scripts/precedent_search.py \
    --query "Has anyone tested antisense oligonucleotides targeting TDP-43 in ALS patient iPSC-derived motor neurons?"
```

### Batch mode — multiple queries from a text file

```bash
uv run edison-precedent/scripts/precedent_search.py \
    --batch queries.txt \
    --output results/precedent_results.md
```

`queries.txt` is plain text — one question per line, blank lines ignored. This is not JSONL format; do not use the JSONL files from `edison-async` here.

### Follow-up chaining

```bash
uv run edison-precedent/scripts/precedent_search.py \
    --query "From the prior answer, which studies used human samples?" \
    --continued-from <task_id>
```

---

## Output Format

```
=== PRECEDENT RESULT ===
Query: Has anyone tested X in Y?

Answer: Yes — [summary of findings]

Successful: True
Task ID: <uuid>
```

With `--output`, results are saved as structured Markdown with one section per query.

---

## Batch Query File Format

`queries.txt` — one question per line:

```
Has anyone tested NAC in ALS mouse models?
Has TDP-43 nuclear depletion been measured in human post-mortem ALS tissue?
Has anyone done CRISPR screen in iPSC motor neurons for ALS?
```

---

## Interpreting Results

| `has_successful_answer` | Meaning |
|---|---|
| `True` | Agent found relevant precedent — check `answer` for details |
| `False` | No clear precedent found, or question is too ambiguous |

A `False` result does **not** mean the thing has never been done — it may mean the
literature is sparse or the query needs refinement. Always verify borderline results.

---

## Research Workflow Tip

Run precedent searches **before** literature searches to quickly triage whether
a topic warrants a deeper dive. Use the task ID from a promising precedent result
as `--continued-from` in a literature search to seamlessly deepen the enquiry.
