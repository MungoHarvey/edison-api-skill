---
name: edison-precedent
description: >
  Query the Edison Precedent agent (formerly "HasAnyone") to determine whether
  something has been done before in science. Use for binary or near-binary questions
  about scientific precedent: "Has anyone used X to treat Y?", "Has X been tested in
  model Z?". Returns a direct yes/no with supporting evidence. Distinct from Literature
  search, which synthesises open-ended scientific questions.
---

# Edison Precedent Search

## Purpose

This skill invokes `JobNames.PRECEDENT` — the Edison "HasAnyone" agent — designed to
answer targeted precedent questions with a clear yes/no and cited supporting evidence.

**Use this skill when:**
- Asking "Has anyone ever done X?" in a scientific context
- Checking whether a drug/target/model combination has been reported
- Performing rapid feasibility checks before designing experiments
- Scoping a research area to identify gaps vs. existing work

**Do NOT use for:**
- Open-ended mechanistic or review questions → use `edison-literature`
- Chemistry synthesis planning → use `edison-molecules`

---

## Prerequisites

- Edison environment configured (run `edison-setup` skill first)
- `.env` file with `EDISON_API_KEY` set
- **Run pre-flight check:** `.venv/bin/python edison-skills/edison-setup/scripts/check_environment.py`

---

## Usage

### Single precedent query

```bash
.venv/bin/python edison-skills/edison-precedent/scripts/precedent_search.py \
    --query "Has anyone tested antisense oligonucleotides targeting TDP-43 in ALS patient iPSC-derived motor neurons?"
```

### Batch mode — multiple queries from a text file

```bash
.venv/bin/python edison-skills/edison-precedent/scripts/precedent_search.py \
    --batch queries.txt \
    --output results/precedent_results.md
```

Where `queries.txt` contains one question per line.

### Follow-up chaining

```bash
.venv/bin/python edison-skills/edison-precedent/scripts/precedent_search.py \
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

`queries.txt` — one question per line, blank lines ignored:

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

## Claude Code Integration

```
Use the Edison precedent search to check:
"Has anyone performed DRUGseq screening in iPSC-derived motor neurons?"
Save the result to results/drugseq_precedent.md
```

## Claude Cowork Integration

Cowork can loop over a list of compounds or targets and invoke the precedent script
for each, aggregating results into a single summary document.

---

## Research Workflow Tip

Run precedent searches **before** literature searches to quickly triage whether
a topic warrants a deeper dive. Use the task ID from a promising precedent result
as `--continued-from` in a literature search to seamlessly deepen the enquiry.
