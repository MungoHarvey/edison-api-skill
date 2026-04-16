# Edison Query Writing Guide

Distilled from the Edison platform best-practices guide. Applies to `LITERATURE`,
`LITERATURE_HIGH`, `ANALYSIS`, and `PRECEDENT` jobs.

## Core Principle

A good Edison query has a single, well-defined objective with natural room for iteration.
The platform performs best when the question is specific enough to anchor a search but
open enough to allow the agent to synthesise across sources.

## What Makes a Good Query

**Frame the question like onboarding a new team member.**
Provide field context, unusual experimental design assumptions, and any domain nuances
the agent might not assume. A query like:

> "What mechanisms link TDP-43 nuclear depletion to RNA processing failure in ALS motor
> neurons, and which of those mechanisms have been validated in patient-derived iPSCs?"

gives the agent far more to work with than "What does TDP-43 do?".

**For ANALYSIS: quality over quantity of data.**
Pre-process data before submission — filter to the most informative rows, annotate
columns clearly, and pair data with a precise biological question. Raw count matrices
or unprocessed screening dumps produce poor results. The inline data path truncates at
20,000 characters; use file storage (see `references/files.md` in the analysis skill)
for larger datasets.

**Start familiar to calibrate expectations.**
When first using the platform on a new research area, run a query on a topic whose
answer is already known. This builds intuition for what quality answers look like and
how to interpret `has_successful_answer = False`.

**Use `--continued-from` to iterate rather than resubmitting.**
Pass the prior task ID with `--continued-from` to give the agent its previous context.
This produces more coherent follow-ups than starting a fresh query, and is the intended
workflow for multi-step research.

## What to Avoid

| Anti-pattern | Why | Better alternative |
|---|---|---|
| Vague prompts ("tell me about TDP-43") | Produces shallow summaries | Specify a mechanism, disease context, or experimental question |
| Obvious/trivial questions ("what is ATP?") | Wastes credits | Use Edison for non-trivial synthesis that requires scanning primary literature |
| Raw unprocessed data (for ANALYSIS) | Confuses the agent | Pre-filter, annotate columns, truncate to relevant rows |
| Overbroadly scoped reviews ("summarise all ALS genetics") | Exceeds synthesis scope | Break into sub-questions, chain with `--continued-from` |
| Questions answerable from a single abstract | Not cost-effective | Use for questions requiring synthesis across many papers |

## Iteration Pattern

```
1. Run initial query
   → note the task ID printed to stderr

2. Review the answer — identify what's missing or needs depth

3. Run follow-up with --continued-from <task_id>
   --query "From the previous answer, which of those mechanisms are
            therapeutically tractable in a CNS context?"

4. Repeat as needed; each step builds on prior context
```

This pattern is more credit-efficient than resubmitting broad queries repeatedly.
