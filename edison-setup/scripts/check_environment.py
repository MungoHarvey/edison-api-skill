#!/usr/bin/env python3
"""
edison-setup/scripts/check_environment.py

Pre-flight environment check. Validates venv, packages, and API key before
any Edison skill executes. Auto-repairs where possible (e.g., re-runs setup_venv.sh
if imports fail).

Exit codes:
  0 = environment ready
  1 = hard failure (broken venv, cannot recover)
  2 = soft failure (missing API key — needs user action)
"""

import sys
import os
import subprocess
import time
from pathlib import Path


def find_project_root():
    """Walk up from script location to find project root (contains .env or .venv)."""
    root = Path(__file__).resolve()
    for _ in range(8):
        root = root.parent
        # Look for markers of project root
        if (root / ".venv").exists() or (root / ".env").exists() or (root / "README.md").exists():
            return root
    # Fallback: 6 levels up from script
    return Path(__file__).resolve().parents[5]


def check_dotenv():
    """Check 1: Can we import python-dotenv?"""
    try:
        from dotenv import load_dotenv
        return True, load_dotenv
    except ImportError:
        return False, None


def check_env_file(project_root, load_dotenv_fn):
    """Check 2: Does .env exist? If not, print path and instructions."""
    env_file = project_root / ".env"

    if env_file.exists():
        if load_dotenv_fn:
            load_dotenv_fn(env_file)
        return True, env_file

    # .env missing — print full path and instructions
    print(f"\n✗ .env file not found", file=sys.stderr)
    print(f"\n  Expected location: {env_file.absolute()}", file=sys.stderr)
    print(f"\n  To fix:", file=sys.stderr)
    print(f"    1. Create the file at the path above", file=sys.stderr)
    print(f"    2. Add your API key: EDISON_API_KEY=your_key_from_platform", file=sys.stderr)
    print(f"    3. Get your key from: https://platform.edisonscientific.com/profile", file=sys.stderr)

    return False, env_file


def check_api_key():
    """Check 3: Is EDISON_API_KEY set and non-empty?"""
    api_key = os.getenv("EDISON_API_KEY", "").strip()

    if api_key:
        return True

    # Missing API key — print instructions
    project_root = find_project_root()
    env_file = project_root / ".env"

    print(f"\n✗ EDISON_API_KEY not set", file=sys.stderr)
    print(f"\n  Edit .env at: {env_file.absolute()}", file=sys.stderr)
    print(f"\n  Add this line:", file=sys.stderr)
    print(f"    EDISON_API_KEY=your_key_here", file=sys.stderr)
    print(f"\n  Get your key from: https://platform.edisonscientific.com/profile", file=sys.stderr)

    return False


def check_edison_client():
    """Check 4: Can we import edison_client? If not, try auto-repair."""
    try:
        from edison_client import EdisonClient, JobNames
        return True, EdisonClient, JobNames
    except ImportError:
        # Try auto-repair: run setup_venv.sh
        print("  Attempting to auto-repair: running setup_venv.sh ...", file=sys.stderr)

        project_root = find_project_root()
        setup_script = project_root / "edison-skills" / "edison-setup" / "scripts" / "setup_venv.sh"

        if not setup_script.exists():
            print(f"✗ setup_venv.sh not found at {setup_script}", file=sys.stderr)
            return False, None, None

        try:
            # Run setup script
            result = subprocess.run(
                ["bash", str(setup_script)],
                cwd=str(project_root),
                capture_output=True,
                timeout=120
            )

            if result.returncode != 0:
                print(f"✗ setup_venv.sh failed with exit code {result.returncode}", file=sys.stderr)
                if result.stderr:
                    print(f"  stderr: {result.stderr.decode()[:200]}", file=sys.stderr)
                return False, None, None

            print("  setup_venv.sh completed, re-checking imports ...", file=sys.stderr)
            time.sleep(1)  # Brief delay for filesystem sync

            # Re-attempt import
            from edison_client import EdisonClient, JobNames
            return True, EdisonClient, JobNames

        except Exception as e:
            print(f"✗ Auto-repair failed: {e}", file=sys.stderr)
            return False, None, None


def ping_platform(client_class):
    """Check 5 (optional --ping): Submit DUMMY task to verify connectivity."""
    try:
        api_key = os.getenv("EDISON_API_KEY")
        if not api_key:
            return False

        client = client_class(api_key=api_key)
        response = client.run_tasks_until_done({"name": "DUMMY", "query": "ping"})

        # Check for successful response
        if hasattr(response, 'answer') or hasattr(response, 'status'):
            return True

        return False
    except Exception as e:
        print(f"  Connectivity check failed: {e}", file=sys.stderr)
        return False


def main():
    project_root = find_project_root()
    ping_platform_flag = "--ping" in sys.argv

    print("=== Edison Environment Check ===", file=sys.stderr)

    # Check 1: python-dotenv
    print("  Check 1: python-dotenv ...", file=sys.stderr)
    dotenv_ok, load_dotenv_fn = check_dotenv()
    if not dotenv_ok:
        print("✗ python-dotenv not installed", file=sys.stderr)
        print("  Fix: run setup_venv.sh from project root", file=sys.stderr)
        sys.exit(1)
    print("  ✓ python-dotenv available", file=sys.stderr)

    # Check 2: .env file
    print("  Check 2: .env file ...", file=sys.stderr)
    env_ok, env_file = check_env_file(project_root, load_dotenv_fn)
    if not env_ok:
        sys.exit(2)  # Soft failure
    print(f"  ✓ .env found at {env_file}", file=sys.stderr)

    # Check 3: API key
    print("  Check 3: EDISON_API_KEY ...", file=sys.stderr)
    key_ok = check_api_key()
    if not key_ok:
        sys.exit(2)  # Soft failure
    print("  ✓ API key loaded", file=sys.stderr)

    # Check 4: edison-client
    print("  Check 4: edison-client ...", file=sys.stderr)
    client_ok, client_class, job_names = check_edison_client()
    if not client_ok:
        print("✗ edison-client import failed (auto-repair unsuccessful)", file=sys.stderr)
        print("  Fix: run setup_venv.sh and check for errors", file=sys.stderr)
        sys.exit(1)
    print("  ✓ edison-client available", file=sys.stderr)

    # Check 5 (optional): connectivity
    if ping_platform_flag:
        print("  Check 5: Platform connectivity (--ping) ...", file=sys.stderr)
        ping_ok = ping_platform(client_class)
        if not ping_ok:
            print("✗ Platform connectivity failed", file=sys.stderr)
            sys.exit(1)
        print("  ✓ Platform connection confirmed", file=sys.stderr)

    # Success
    print("\n✓ Edison environment is ready", file=sys.stderr)
    print(f"  Project root: {project_root}", file=sys.stderr)
    print(f"  API key: {os.getenv('EDISON_API_KEY', '')[:10]}...", file=sys.stderr)
    sys.exit(0)


if __name__ == "__main__":
    main()
