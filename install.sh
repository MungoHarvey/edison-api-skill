#!/usr/bin/env bash
# Edison Skills installer
# Usage: bash install.sh --user       # copies to ~/.claude/skills/
#        bash install.sh --plugin-dir  # prints the --plugin-dir flag to use
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
case "${1:-}" in
  --user)
    mkdir -p ~/.claude/skills
    for skill in "$REPO_ROOT"/skills/edison-*; do
        name=$(basename "$skill")
        if [ -d "$HOME/.claude/skills/$name" ]; then
            echo "WARNING: $name already exists at ~/.claude/skills/$name — overwriting."
        fi
        cp -r "$skill" ~/.claude/skills/ || {
            echo "ERROR: failed to copy $name — check permissions on ~/.claude/skills/" >&2
            exit 1
        }
        echo "Installed $name"
    done
    echo "Done. Skills available in Claude Code."
    ;;
  --plugin-dir|*)
    echo "Add this flag to your Claude Code command:"
    echo "  --plugin-dir '$REPO_ROOT'"
    ;;
esac
