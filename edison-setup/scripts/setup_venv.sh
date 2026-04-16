#!/usr/bin/env bash
# edison-setup/scripts/setup_venv.sh
# Creates a virtual environment and installs edison-client.
# Run from the project root: bash edison-setup/scripts/setup_venv.sh

set -euo pipefail

VENV_DIR=".venv"
PYTHON="${PYTHON:-python3}"

echo "=== Edison Environment Setup ==="

# Verify Python 3.10+
PYTHON_VERSION=$("$PYTHON" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null) || {
    echo "ERROR: Python not found. Install Python 3.10+ and ensure it is on PATH." >&2; exit 1
}
MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)
if [ "$MAJOR" -lt 3 ] || { [ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 10 ]; }; then
    echo "ERROR: Python 3.10+ required. Found: $PYTHON_VERSION" >&2; exit 1
fi
echo "Python $PYTHON_VERSION OK"

# Create venv if it doesn't already exist
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment at $VENV_DIR ..."
    if command -v uv &>/dev/null; then
        uv venv "$VENV_DIR"
    else
        "$PYTHON" -m venv "$VENV_DIR"
    fi
else
    echo "Virtual environment already exists at $VENV_DIR — skipping creation."
fi

# Install/upgrade packages
echo "Installing edison-client and python-dotenv ..."
if command -v uv &>/dev/null; then
    uv pip install --python "$VENV_DIR/bin/python" edison-client python-dotenv
else
    "$VENV_DIR/bin/pip" install --upgrade pip
    "$VENV_DIR/bin/pip" install edison-client python-dotenv
fi

# Verify import
echo "Verifying installation ..."
"$VENV_DIR/bin/python" -c "from edison_client import EdisonClient, JobNames; print('✓ edison-client import OK')"

echo ""
echo "=== Setup complete ==="
echo "Activate with: source $VENV_DIR/bin/activate"
echo "Or invoke scripts directly with: $VENV_DIR/bin/python <script>"
