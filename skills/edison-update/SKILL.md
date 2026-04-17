---
name: edison-update
description: >
  This skill should be used when the user asks to "update Edison skills", "pull
  latest Edison changes", "check for Edison updates", "upgrade Edison", or says
  "there's a new version of Edison skills". Run this to fetch and apply the latest
  changes from the GitHub repo and reinstall if needed.
version: 0.1.0
---

# Edison Skills Updater

When this skill is invoked, execute the following steps in order.

## Step 1 — Check for updates

Run this command and show the user the output:

```bash
bash skills/edison-update/scripts/update.sh --check
```

If the output says "Already up to date", tell the user and stop here.

## Step 2 — Ask the user whether to apply

If updates are available, show the user the list of new commits and ask:
"There are N new commits. Apply updates now?"

If they say no, stop here.

## Step 3 — Apply updates

Run:

```bash
bash skills/edison-update/scripts/update.sh --apply
```

Show the full output. If the command fails, show the error and the suggested fix from the output.

## Step 4 — Confirm

Tell the user the update is complete and remind them to **restart Claude Code** to
pick up any updated skill definitions.

---

## Flags reference (for manual use)

| Command | Behaviour |
|---------|-----------|
| `bash skills/edison-update/scripts/update.sh --check` | Show new commits, do not pull |
| `bash skills/edison-update/scripts/update.sh --apply` | Pull and reinstall without prompting |
| `bash skills/edison-update/scripts/update.sh` | Interactive — prompts before pulling |
