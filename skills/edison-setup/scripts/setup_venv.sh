#!/usr/bin/env bash
# skills/edison-setup/scripts/setup_venv.sh
# Creates a virtual environment and installs edison-client.
# Run from the project root: bash skills/edison-setup/scripts/setup_venv.sh

set -euo pipefail

VENV_DIR=".venv"
PYTHON="${PYTHON:-python3}"

echo "=== Edison Environment Setup ==="

# Verify Python 3.11+
PYTHON_VERSION=$("$PYTHON" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null) || {
    echo "ERROR: Python not found. Install Python 3.11+ and ensure it is on PATH." >&2; exit 1
}
MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)
if [ "$MAJOR" -lt 3 ] || { [ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 11 ]; }; then
    echo "ERROR: Python 3.11+ required (edison-client needs 3.11+)." >&2
    echo "       Found: $PYTHON_VERSION. Install Python 3.11+ and ensure it is on PATH." >&2
    exit 1
fi
echo "Python $PYTHON_VERSION OK"

# Detect platform and set venv binary paths
_OS=$(uname -s)
if [[ "$_OS" == MINGW* || "$_OS" == CYGWIN* ]]; then
    VENV_PY="$VENV_DIR/Scripts/python.exe"
    VENV_PIP="$VENV_DIR/Scripts/pip.exe"
elif [[ "$_OS" == Darwin || "$_OS" == Linux ]]; then
    VENV_PY="$VENV_DIR/bin/python"
    VENV_PIP="$VENV_DIR/bin/pip"
else
    echo "WARNING: unrecognised OS ($_OS) — assuming Unix paths" >&2
    VENV_PY="$VENV_DIR/bin/python"
    VENV_PIP="$VENV_DIR/bin/pip"
fi

# Create venv if it doesn't already exist
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment at $VENV_DIR ..."
    if command -v uv &>/dev/null; then
        uv venv --python 3.11 "$VENV_DIR"
    else
        "$PYTHON" -m venv "$VENV_DIR"
    fi
else
    echo "Virtual environment already exists at $VENV_DIR — skipping creation."
fi

# Install/upgrade packages
echo "Installing edison-client and python-dotenv ..."
if command -v uv &>/dev/null; then
    uv pip install --python "$VENV_PY" "edison-client" python-dotenv
else
    "$VENV_PIP" install --upgrade pip
    "$VENV_PIP" install "edison-client" python-dotenv
fi

# Verify import
echo "Verifying installation ..."
"$VENV_PY" -c "from edison_client import EdisonClient, JobNames; print('✓ edison-client import OK')"

echo ""
echo "=== Setup complete ==="
if [[ "$_OS" == MINGW* || "$_OS" == CYGWIN* ]]; then
    echo "Or invoke scripts directly with: $VENV_DIR/Scripts/python.exe <script>"
else
    echo "Activate with: source $VENV_DIR/bin/activate"
    echo "Or invoke scripts directly with: $VENV_DIR/bin/python <script>"
fi
