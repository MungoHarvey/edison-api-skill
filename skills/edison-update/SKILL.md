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

## Purpose

Checks for and applies updates from the Edison Skills GitHub repository.
Handles both install modes: `--plugin-dir` (reads directly from repo) and
`--user` (copies into `~/.claude/skills/`).

---

## Step 1 — Check for updates

```bash
bash skills/edison-update/scripts/update.sh --check
```

This fetches the latest commits from GitHub and prints what's new without
changing anything. Safe to run at any time.

---

## Step 2 — Apply updates

```bash
bash skills/edison-update/scripts/update.sh --apply
```

This:
1. Pulls the latest commits from `origin/main`
2. If skills are installed under `~/.claude/skills/`, re-copies them automatically
3. If using `--plugin-dir`, the pull is sufficient (Claude Code reads directly from the repo)

After updating, restart Claude Code to pick up the new skill definitions.

---

## Quick one-liner

To check and apply in one shot:

```bash
bash skills/edison-update/scripts/update.sh
```

Without flags it will print what's new and ask for confirmation before pulling.

---

## Flags

| Flag | Behaviour |
|------|-----------|
| _(none)_ | Show new commits, prompt before applying |
| `--check` | Show new commits only, do not pull |
| `--apply` | Pull and reinstall without prompting |
| `--user` | Alias for `--apply` |

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| `Pull failed — local uncommitted changes` | `git stash` then re-run with `--apply` |
| `Could not reach remote` | Check network; confirm GitHub is accessible |
| Skills not updated in Claude Code | Restart Claude Code after the pull |
| `--user` reinstall failed | Check permissions on `~/.claude/skills/` |
