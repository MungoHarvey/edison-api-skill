#!/usr/bin/env python3
"""
edison-setup/scripts/test_connection.py

Validates that the Edison client is installed, the API key is present,
and the platform is reachable via a lightweight Dummy task.
"""
# /// script
# dependencies = ["edison-client", "python-dotenv"]
# ///

import sys
import os
from pathlib import Path

# ── Load .env from project root ──────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    # Walk up until we find .env (supports running from any subdirectory)
    root = Path(__file__).resolve()
    for _ in range(8):
        root = root.parent
        env_file = root / ".env"
        if env_file.exists():
            load_dotenv(env_file)
            break
except ImportError:
    print("✗ python-dotenv not installed — run setup_venv.sh first", file=sys.stderr)
    sys.exit(1)

# ── Import check ──────────────────────────────────────────────────────────────
try:
    from edison_client import EdisonClient, JobNames
    print("✓ Edison client imported successfully")
except ImportError as e:
    print(f"✗ Import failed: {e}\n  Run setup_venv.sh to install dependencies.", file=sys.stderr)
    sys.exit(1)

# ── API key check ─────────────────────────────────────────────────────────────
api_key = os.getenv("EDISON_API_KEY")
if not api_key:
    print("✗ EDISON_API_KEY not found in environment or .env file", file=sys.stderr)
    sys.exit(1)
print("✓ API key loaded from environment")

# ── Connectivity check via Dummy task ─────────────────────────────────────────
print("  Submitting dummy task to verify platform connectivity ...")
try:
    client = EdisonClient(api_key=api_key)
    response = client.run_tasks_until_done({"name": JobNames.DUMMY, "query": "ping"})
    print("✓ Dummy task completed — connection confirmed")
    print(f"  Response: {getattr(response, 'answer', str(response))[:120]}")
except Exception as e:
    print(f"✗ Platform connection failed: {e}", file=sys.stderr)
    sys.exit(1)

print("\n=== Edison environment is ready ===")
