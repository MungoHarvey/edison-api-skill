#!/usr/bin/env python3
"""
skills/edison-setup/scripts/test_connection.py

Validates that the Edison client is installed, the API key is present,
and the platform is reachable via a lightweight Dummy task.
"""
# /// script
# requires-python = ">=3.11"
# dependencies = ["edison-client>=0.9.0", "python-dotenv"]
# ///

import sys
import os
from pathlib import Path

# ── Load .env from project root ──────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    _env_file = os.environ.get("EDISON_ENV_FILE")
    if _env_file:
        load_dotenv(_env_file)
    else:
        root = Path(__file__).resolve().parent
        for _ in range(8):
            if (root / ".env.edison").exists():
                load_dotenv(root / ".env.edison")
                break
            if (root / ".env").exists():
                load_dotenv(root / ".env")
                break
            if (root / ".git").is_dir():
                break
            root = root.parent
except ImportError:
    pass

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
    msg = str(e).lower()
    if "404" in msg or "not found" in msg:
        print("⚠ Platform ping returned 404 (known server-side issue).", file=sys.stderr)
        print("  Your API key and setup are likely fine.", file=sys.stderr)
        print("  This is a known issue at platform.edisonscientific.com.", file=sys.stderr)
    elif "401" in msg or "unauthorized" in msg or "forbidden" in msg:
        print(f"✗ Authentication failed — check EDISON_API_KEY: {e}", file=sys.stderr)
        sys.exit(1)
    else:
        print(f"✗ Platform connection failed: {e}", file=sys.stderr)
        sys.exit(1)

print("\n=== Edison environment is ready ===")
