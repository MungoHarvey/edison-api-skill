#!/usr/bin/env bash
# SessionStart hook: check Edison environment and report status to Claude's context.
# Runs automatically when Claude Code starts in a project with this plugin enabled.

STATUS=""
WARNINGS=""

# 1. Check for uv
if command -v uv &>/dev/null; then
    UV_VERSION=$(uv --version 2>/dev/null | head -1)
    STATUS="${STATUS}uv: ✓ ($UV_VERSION)\n"
else
    WARNINGS="${WARNINGS}⚠ uv not found. Install: curl -LsSf https://astral.sh/uv/install.sh | sh\n"
fi

# 2. Check for .venv (created by setup_venv.sh)
if [ -d ".venv" ]; then
    STATUS="${STATUS}.venv: ✓ (dependencies installed)\n"
else
    WARNINGS="${WARNINGS}⚠ .venv not found. Run: bash skills/edison-setup/scripts/setup_venv.sh\n"
fi

# 3. Check for .env file (must be copied from .env.example by user)
ENV_FILE=""
DIR="$(pwd)"
for i in $(seq 1 8); do
    if [ -f "$DIR/.env" ]; then
        ENV_FILE="$DIR/.env"
        break
    fi
    DIR="$(dirname "$DIR")"
done

if [ -n "$ENV_FILE" ]; then
    STATUS="${STATUS}.env: ✓ (found at $ENV_FILE)\n"
else
    WARNINGS="${WARNINGS}⚠ No .env file found. Run: cp .env.example .env  then add your EDISON_PLATFORM_API_KEY.\n"
fi

# 4. Check for EDISON_PLATFORM_API_KEY (or legacy EDISON_API_KEY) from env or .env
RESOLVED_KEY="${EDISON_PLATFORM_API_KEY:-$EDISON_API_KEY}"
if [ -n "$RESOLVED_KEY" ]; then
    KEY_PREFIX="${RESOLVED_KEY:0:8}..."
    STATUS="${STATUS}EDISON_PLATFORM_API_KEY: ✓ (${KEY_PREFIX})\n"
elif [ -n "$ENV_FILE" ]; then
    KEY_IN_FILE=$(grep -E '^EDISON_PLATFORM_API_KEY=' "$ENV_FILE" 2>/dev/null | head -1 | cut -d= -f2-)
    # Fall back to legacy name if new name not found
    if [ -z "$KEY_IN_FILE" ]; then
        KEY_IN_FILE=$(grep -E '^EDISON_API_KEY=' "$ENV_FILE" 2>/dev/null | head -1 | cut -d= -f2-)
    fi
    if [ -n "$KEY_IN_FILE" ] && [ "$KEY_IN_FILE" != "your_api_key_here" ]; then
        KEY_PREFIX="${KEY_IN_FILE:0:8}..."
        STATUS="${STATUS}EDISON_PLATFORM_API_KEY: ✓ in .env (${KEY_PREFIX})\n"
    else
        WARNINGS="${WARNINGS}⚠ EDISON_PLATFORM_API_KEY not set in .env. Get your key at https://platform.edisonscientific.com/profile\n"
    fi
else
    WARNINGS="${WARNINGS}⚠ EDISON_PLATFORM_API_KEY not found in environment or .env.\n"
fi

# 5. Report
echo "--- Edison Environment Status ---"
printf '%b' "$STATUS"
if [ -n "$WARNINGS" ]; then
    echo ""
    printf '%b' "$WARNINGS"
    echo ""
    echo "Run the edison-setup skill to fix issues."
else
    echo ""
    echo "✓ Edison environment ready."
fi
echo "--- End Edison Status ---"
