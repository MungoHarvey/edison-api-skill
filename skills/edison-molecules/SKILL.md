---
name: edison-molecules
description: >
  This skill should be used when the user asks about chemistry, molecular design,
  synthesis routes, drug-likeness, ADMET properties, or cheminformatics. Use when
  the user asks to "design a molecule", "plan a synthesis", "evaluate drug-like
  properties", "suggest analogues", "predict ADMET", or provides a SMILES string
  and wants chemical analysis. Distinct from literature search — this skill actively
  uses cheminformatics tools to reason about chemistry, not just retrieve papers.
version: 0.1.0
---

# Edison Molecules (Chemistry Tasks)

## Purpose

Invoke `JobNames.MOLECULES` — the Edison Phoenix/ChemCrow agent equipped with
cheminformatics tools for active chemical reasoning.

**Use for:**
- Planning synthesis routes for small molecules
- Designing novel molecular scaffolds or analogues
- Querying drug-like properties (ADMET, Lipinski, solubility)
- Evaluating chemical similarity to known compounds
- Exploring SAR (structure-activity relationship) hypotheses

**Do NOT use for:**
- General literature questions about a drug — use `edison-literature`
- Checking if a compound has been synthesised before — use `edison-precedent`

---

## Prerequisites

- Edison environment configured (run `edison-setup` skill first if uncertain)
- `.env` file with `EDISON_PLATFORM_API_KEY` set at project root

---

## Usage

### Basic chemistry query

```bash
uv run skills/edison-molecules/scripts/chemistry_task.py \
    --query "Design a small molecule inhibitor of TDP-43 aggregation with good CNS penetrance"
```

### Synthesis planning with SMILES

```bash
uv run skills/edison-molecules/scripts/chemistry_task.py \
    --query "Plan a synthetic route for compound with SMILES: CC(=O)Nc1ccc(O)cc1" \
    --output results/synthesis_plan.md
```

### Follow-up / iterative refinement

```bash
uv run skills/edison-molecules/scripts/chemistry_task.py \
    --query "From the previous design, suggest modifications to improve blood-brain barrier penetrance" \
    --continued-from <task_id>
```

---

## Effective Query Patterns

| Goal | Query Pattern |
|---|---|
| Analogue design | "Design analogues of [SMILES/name] with improved [property]" |
| Synthesis route | "Plan a synthesis for [compound name or SMILES]" |
| Property prediction | "What are the predicted ADMET properties of [SMILES]?" |
| SAR exploration | "What structural changes to [scaffold] would improve [activity]?" |
| Target docking context | "Which functional groups on [molecule] are likely to interact with [target]?" |

Providing SMILES strings (where available) gives the agent precise chemical context.

---

## Output Format

```
=== CHEMISTRY RESULT ===
Query: Design a ...

Answer:
[Molecular design rationale, SMILES, properties, synthesis steps]

Task ID: <uuid>
```

With `--output`, saved as a structured Markdown document.

---

## Retry on Truncation

Complex synthesis planning can hit the agent's step limit. The script retries
automatically with a larger budget (1.5× per attempt, up to 300 steps).

```bash
# Increase starting budget for multi-step synthesis (default: 100)
uv run skills/edison-molecules/scripts/chemistry_task.py \
    --query "..." --max-steps 150

# Allow more retries (default: 3)
uv run skills/edison-molecules/scripts/chemistry_task.py \
    --query "..." --max-retries 5

# Disable retry
uv run skills/edison-molecules/scripts/chemistry_task.py \
    --query "..." --no-retry
```

Exit code `2` means the result was truncated after all retries exhausted.

---

## Notes on Output Quality

- The Phoenix agent uses real cheminformatics tools; results include SMILES, predicted
  properties, and reasoning chains — not just text summaries.
- For complex multi-step synthesis, use `--verbose` to inspect the full agent state
  and tool call trace.
- SMILES in the output can be copied directly into tools like RDKit, ChemDraw, or
  PyMOL for visualisation.
