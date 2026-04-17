# TODOS

## DRY: extract shared .env preamble

**What:** Extract the 12-line `.env` walk-up preamble (EDISON_ENV_FILE check → .env.edison → .env → .git stop) into a shared helper `skills/common/env_loader.py`, imported as a local `uv` path dependency in each script's PEP 723 block.

**Why:** Currently all 8 scripts have identical preambles. If the walk-up logic changes (e.g., adding `.env.local` support), it requires editing 8 files.

**Pros:** Single source of truth for env loading logic. Easier to test.

**Cons:** Requires adding `"./skills/common"` as a path dep in every PEP 723 `[tool.uv.sources]` block, which complicates standalone script execution. Non-trivial for the PEP 723 self-contained model.

**Context:** Added after the 2026-04-17 setup overhaul (design-404-fix-setup-overhaul-20260417.md). Walk-up logic was just updated from 7 scripts to 8 — next change will be 8+ edits again. Deferred because tests come first.

**Depends on:** §8 (pytest setup) green. Local path deps in uv verified to work with `uv run`.

**Where to start:** `uv` docs on `[tool.uv.sources]` with path dependencies in PEP 723 scripts.
