#!/usr/bin/env bash
# edison-setup/scripts/setup_venv.sh
# Creates a virtual environment and installs edison-client.
# Run from the project root: bash edison-skills/edison-setup/scripts/setup_venv.sh

set -euo pipefail

VENV_DIR=".venv"
PYTHON="${PYTHON:-python3}"

echo "=== Edison Environment Setup ==="

# Create venv if it doesn't already exist
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment at $VENV_DIR ..."
    "$PYTHON" -m venv "$VENV_DIR"
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
