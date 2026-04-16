---
name: edison-literature
description: >
  This skill should be used when the user asks a scientific literature question,
  wants cited evidence for a claim, asks "what does the literature say about X",
  wants a literature review or summary, needs references for a grant or paper,
  or asks an open-ended biological or clinical question requiring primary evidence.
  Use for synthesis questions like "what are the mechanisms of X" or "what evidence
  supports Y". Distinct from precedent search (binary yes/no) — this skill returns
  a synthesised, cited answer from published papers.
version: 0.1.0
---

# Edison Literature Search

## Purpose

Invoke `JobNames.LITERATURE` on the Edison platform — a PaperQA3-powered agent that
searches scientific databases, retrieves full papers, and synthesises a cited answer
to an open scientific question.

**Use for:**
- Open-ended scientific questions requiring evidence from published papers
- Literature-backed summaries for grant writing or research updates
- Formatted answers with references for biological or clinical questions
- Follow-up queries that build on a prior literature search

**Do NOT use for:**
- Binary "has anyone done X" questions — use `edison-precedent` instead
- Chemistry or synthesis questions — use `edison-molecules`
- Analysing your own datasets — use `edison-analysis`

---

## Prerequisites

- Edison environment configured (run `edison-setup` skill first if uncertain)
- `.env` file with `EDISON_API_KEY` set at project root

---

## Usage

### Single query

```bash
uv run edison-literature/scripts/literature_search.py \
    --query "What are the mechanisms by which TDP-43 aggregation impairs motor neuron function in ALS?"
```

### High-reasoning variant (LITERATURE_HIGH)

```bash
uv run edison-literature/scripts/literature_search.py \
    --query "What are the mechanisms by which TDP-43 aggregation impairs motor neuron function in ALS?" \
    --high
```

Use `--high` when:
- The standard `LITERATURE` result lacks depth or cites insufficient papers
- The question requires state-of-the-art synthesis across a complex or contested field
- Credit budget allows for a slower, higher-quality run

`LITERATURE_HIGH` is slower than `LITERATURE` (allow 3–10 minutes) and uses more credits.
Verify it is supported by the installed package before use:

```bash
python -c "from edison_client import JobNames; print([j.name for j in JobNames])"
```

### With verbose output (includes full paper metadata)

```bash
uv run edison-literature/scripts/literature_search.py \
    --query "..." \
    --verbose
```

### Follow-up / chained query

```bash
uv run edison-literature/scripts/literature_search.py \
    --query "From the previous answer, which of those mechanisms are therapeutically tractable?" \
    --continued-from <task_id_from_prior_run>
```

### Output to file

```bash
uv run edison-literature/scripts/literature_search.py \
    --query "..." \
    --output results/literature_output.md
```

---

## Output Format

```
=== ANSWER ===
<synthesised answer text>

=== FORMATTED ANSWER (with references) ===
<answer with inline citations and reference list>

=== TASK ID ===
<uuid>  ← save this to run follow-up queries with --continued-from
```

With `--output`, the formatted answer is saved as Markdown.

---

## Key Response Fields

| Field | Description |
|---|---|
| `answer` | Plain text synthesised answer |
| `formatted_answer` | Answer with inline citations and reference list |
| `has_successful_answer` | `False` means insufficient literature found |

With `--verbose`, also available:
- `environment_frame` — full paper contexts, metadata, and raw retrieval data
- `agent_state` — step-by-step agent reasoning trace

---

## Error Handling

| Error | Cause | Fix |
|---|---|---|
| `has_successful_answer = False` | Insufficient literature coverage | Rephrase query; broaden or narrow scope |
| `AuthenticationError` | Bad API key | Check `.env`; regenerate at platform |
| Timeout / long wait | Heavy search load | Use `edison-async` skill for non-blocking submission |

---

## Additional Resources

- **[`references/query-guide.md`](references/query-guide.md)** — how to write effective
  literature queries, iteration patterns with `--continued-from`, and common anti-patterns.
