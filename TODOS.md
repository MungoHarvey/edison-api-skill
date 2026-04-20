# TODOS

## DRY: extract shared .env preamble

**What:** Extract the 12-line `.env` walk-up preamble (EDISON_ENV_FILE check → .env.edison → .env → .git stop) into a shared helper `skills/common/env_loader.py`, imported as a local `uv` path dependency in each script's PEP 723 block.

**Why:** Currently all 8 scripts have identical preambles. If the walk-up logic changes (e.g., adding `.env.local` support), it requires editing 8 files.

**Pros:** Single source of truth for env loading logic. Easier to test.

**Cons:** Requires adding `"./skills/common"` as a path dep in every PEP 723 `[tool.uv.sources]` block, which complicates standalone script execution. Non-trivial for the PEP 723 self-contained model.

**Context:** Added after the 2026-04-17 setup overhaul (design-404-fix-setup-overhaul-20260417.md). Walk-up logic was just updated from 7 scripts to 8 — next change will be 8+ edits again. Deferred because tests come first.

**Depends on:** §8 (pytest setup) green. Local path deps in uv verified to work with `uv run`.

**Where to start:** `uv` docs on `[tool.uv.sources]` with path dependencies in PEP 723 scripts.

## data_analysis.py answer extraction + proper data upload

**What:** Two bugs in `skills/edison-analysis/scripts/data_analysis.py`. (1) The script reads `response.answer`, but ANALYSIS tasks nest the real answer at `environment_frame["state"]["state"]["answer"]` — result is that successful runs look empty or mis-rendered. (2) Inline data is stitched into the query string, which is the wrong mechanism; the Edison SDK exposes `astore_file_content()` for data uploads, which avoids the 20k-char truncation and lets the agent reference data as a proper artifact.

**Why:** Users running `data_analysis.py` today either see blank answers, partial answers, or answers missing structured content. The inline-query approach also hits the `MAX_DATA_CHARS = 20_000` cap for any non-trivial dataset.

**Pros:** Makes the analysis skill actually usable. Removes the 20k-char ceiling. Brings the script in line with the other skills, which return useful output.

**Cons:** Requires understanding Edison's `environment_frame` schema (poorly documented). `astore_file_content()` changes the task submission shape (file_id vs inline), so error paths need a pass. Moderate-size change.

**Context:** Identified during the 2026-04-20 eng-review of the max_steps/retry design (`docs/superpowers/specs/2026-04-20-edison-max-steps-retry-design.md`) and explicitly held out of that spec's scope. The retry spec handles truncation across all skills uniformly; this data-analysis fix is orthogonal.

**Depends on:** Nothing — can land independently. Best landed after the retry spec so it inherits the retry wrapper automatically (one fewer merge to reconcile).

**Where to start:** (1) Read `environment_frame` in a verbose-mode sample response from ANALYSIS; confirm the answer path. (2) Read edison-client's `astore_file_content()` signature and an example in the SDK repo. (3) Refactor `build_query_with_data` into two branches: inline (small data, current behaviour) vs uploaded (large data, new path).
