#!/usr/bin/env bash
# skills/edison-update/scripts/update.sh
#
# Check for and apply updates from the Edison Skills GitHub repo.
#
# Usage:
#   bash update.sh              # check for updates, prompt before applying
#   bash update.sh --check      # check only, do not pull
#   bash update.sh --apply      # pull and reinstall without prompting
#   bash update.sh --user       # pull and reinstall to ~/.claude/skills/ (same as --apply)
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
REMOTE_URL="https://github.com/MungoHarvey/edison-api-skill"

cd "$REPO_ROOT"

# ── Sanity checks ──────────────────────────────────────────────────────────────
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "✗ Not a git repository: $REPO_ROOT" >&2
    exit 1
fi

echo "=== Edison Skills Update Check ==="
echo "  Repo: $REPO_ROOT"
echo "  Remote: $(git remote get-url origin 2>/dev/null || echo 'unknown')"
echo ""

# ── Fetch latest from remote ───────────────────────────────────────────────────
echo "Fetching latest from remote ..."
if ! git fetch origin --quiet 2>&1; then
    echo "✗ Could not reach remote. Check network connectivity." >&2
    exit 1
fi

LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main 2>/dev/null || git rev-parse origin/master 2>/dev/null)

if [ "$LOCAL" = "$REMOTE" ]; then
    echo "✓ Already up to date. No updates available."
    exit 0
fi

# ── Show what's new ────────────────────────────────────────────────────────────
COMMIT_COUNT=$(git rev-list HEAD..origin/main --count 2>/dev/null || echo "?")
echo "  $COMMIT_COUNT new commit(s) available:"
echo ""
git log HEAD..origin/main --oneline --no-decorate 2>/dev/null | sed 's/^/  /'
echo ""

# Check-only mode
if [[ "${1:-}" == "--check" ]]; then
    echo "Run with --apply to pull and reinstall."
    exit 0
fi

# Prompt unless --apply or --user flag passed
if [[ "${1:-}" != "--apply" && "${1:-}" != "--user" ]]; then
    printf "Apply updates and reinstall? [y/N] "
    read -r answer
    if [[ "$answer" != "y" && "$answer" != "Y" ]]; then
        echo "Aborted. Run with --apply to update without prompting."
        exit 0
    fi
fi

# ── Pull ───────────────────────────────────────────────────────────────────────
echo "Pulling updates ..."
git pull --ff-only origin main 2>/dev/null || git pull --ff-only origin master 2>/dev/null || {
    echo "✗ Pull failed. You may have local uncommitted changes." >&2
    echo "  Run: git stash && bash skills/edison-update/scripts/update.sh --apply" >&2
    exit 1
}
echo "✓ Pulled $(git rev-parse --short HEAD)"
echo ""

# ── Reinstall skills to ~/.claude/skills/ (if installed that way) ─────────────
if [ -d "$HOME/.claude/skills/edison-literature" ] || [ -d "$HOME/.claude/skills/edison-setup" ]; then
    echo "Detected ~/.claude/skills/ install — reinstalling updated skills ..."
    bash "$REPO_ROOT/install.sh" --user
    echo ""
else
    echo "Using --plugin-dir mode — no reinstall needed (reads directly from repo)."
    echo ""
fi

echo "✓ Edison Skills updated successfully."
echo "  Restart Claude Code to pick up changes."
