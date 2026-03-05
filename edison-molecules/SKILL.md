---
name: edison-molecules
description: >
  Run chemistry and molecular design tasks using Edison's Phoenix agent (ChemCrow
  iteration). Use when planning chemical synthesis, designing novel molecules,
  evaluating drug-likeness, or querying cheminformatics properties. This skill is
  distinct from literature or precedent search — it actively uses cheminformatics
  tools to reason about chemistry.
---

# Edison Molecules (Chemistry Tasks)

## Purpose

This skill invokes `JobNames.MOLECULES` — the Edison Phoenix/ChemCrow agent equipped
with cheminformatics tools for active chemical reasoning.

**Use this skill when:**
- Planning synthesis routes for small molecules
- Designing novel molecular scaffolds or analogues
- Querying drug-like properties (ADMET, Lipinski, solubility)
- Evaluating chemical similarity to known compounds
- Exploring SAR (structure-activity relationship) hypotheses

**Do NOT use for:**
- General literature questions about a drug → use `edison-literature`
- Checking if a compound has been synthesised before → use `edison-precedent`

---

## Prerequisites

- Edison environment configured (run `edison-setup` skill first)
- `.env` file with `EDISON_API_KEY` set
- **Run pre-flight check:** `.venv/bin/python edison-skills/edison-setup/scripts/check_environment.py`

---

## Usage

### Basic chemistry query

```bash
.venv/bin/python edison-skills/edison-molecules/scripts/chemistry_task.py \
    --query "Design a small molecule inhibitor of TDP-43 aggregation with good CNS penetrance"
```

### Synthesis planning

```bash
.venv/bin/python edison-skills/edison-molecules/scripts/chemistry_task.py \
    --query "Plan a synthetic route for compound with SMILES: CC(=O)Nc1ccc(O)cc1" \
    --output results/synthesis_plan.md
```

### Follow-up / iterative refinement

```bash
.venv/bin/python edison-skills/edison-molecules/scripts/chemistry_task.py \
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

## Claude Code Integration

```
Use the Edison molecules skill to design a series of TDP-43 disaggregation compounds.
Start with the scaffold CC1=CC=C(C=C1)NC(=O)CN and suggest three analogues
with improved solubility. Save to results/tdp43_analogues.md
```

## Claude Cowork Integration

Cowork can run iterative design loops:
1. Submit initial design query
2. Capture task ID
3. Submit follow-up query to refine, using `--continued-from`
4. Aggregate all iterations into a design log

---

## Notes on Output Quality

- The Phoenix agent uses real cheminformatics tools; results include SMILES, predicted
  properties, and reasoning chains — not just text summaries.
- For complex multi-step synthesis, enable `--verbose` to inspect the full agent state
  and tool call trace.
- SMILES in the output can be copied directly into tools like RDKit, ChemDraw, or
  PyMOL for visualisation.
