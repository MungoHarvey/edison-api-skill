#!/usr/bin/env python3
"""
skills/edison-setup/scripts/check_environment.py

Pre-flight environment check. Validates venv, packages, and API key before
any Edison skill executes. Auto-repairs where possible (e.g., re-runs setup_venv.sh
if imports fail).

Exit codes:
  0 = environment ready (includes ping 404 — platform-side issue, key is fine)
  1 = hard failure (broken venv, auth error, cannot recover)
  2 = soft failure (missing API key — needs user action)
"""
# /// script
# requires-python = ">=3.11"
# dependencies = ["edison-client", "python-dotenv"]
# ///

import sys
import os
import subprocess
import time
from pathlib import Path


def find_project_root():
    """Walk up from script location to the nearest .git directory (project root)."""
    root = Path(__file__).resolve().parent
    for _ in range(8):
        if (root / ".git").is_dir():
            return root
        root = root.parent
    # Fallback: 4 levels up from script directory (skills/edison-setup/scripts/ → project root)
    return Path(__file__).resolve().parents[3]


def check_dotenv():
    """Check 1: Can we import python-dotenv?"""
    try:
        from dotenv import load_dotenv
        return True, load_dotenv
    except ImportError:
        return False, None


def check_env_file(project_root, load_dotenv_fn):
    """Check 2: Does .env.edison or .env exist? Supports EDISON_ENV_FILE override."""
    explicit = os.environ.get("EDISON_ENV_FILE")
    if explicit:
        explicit_path = Path(explicit)
        if explicit_path.exists():
            if load_dotenv_fn:
                load_dotenv_fn(explicit_path)
            return True, explicit_path
        print(f"\n✗ EDISON_ENV_FILE set but file not found: {explicit_path.absolute()}", file=sys.stderr)
        return False, explicit_path

    for name in (".env.edison", ".env"):
        env_file = project_root / name
        if env_file.exists():
            if load_dotenv_fn:
                load_dotenv_fn(env_file)
            return True, env_file

    env_file = project_root / ".env"
    print(f"\n✗ .env file not found", file=sys.stderr)
    print(f"\n  Expected location: {env_file.absolute()}", file=sys.stderr)
    print(f"\n  To fix:", file=sys.stderr)
    print(f"    1. Create the file at the path above", file=sys.stderr)
    print(f"    2. Add your API key: EDISON_API_KEY=your_key_here", file=sys.stderr)
    print(f"    3. Get your key from: https://platform.edisonscientific.com/profile", file=sys.stderr)
    print(f"\n  Or set EDISON_ENV_FILE=/path/to/your/.env to use a custom location.", file=sys.stderr)

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
    except ImportError as import_err:
        err_msg = str(import_err).lower()
        if "python" in err_msg and ("version" in err_msg or "3.1" in err_msg):
            print("✗ edison-client requires Python 3.11+", file=sys.stderr)
            print("  Hint: re-create venv with: uv venv --python 3.11", file=sys.stderr)
            return False, None, None

        print(f"  Import failed: {import_err}", file=sys.stderr)
        # Try auto-repair: run setup_venv.sh
        print("  Attempting to auto-repair: running setup_venv.sh ...", file=sys.stderr)

        project_root = find_project_root()
        setup_script = project_root / "skills" / "edison-setup" / "scripts" / "setup_venv.sh"

        if not setup_script.exists():
            print(f"✗ setup_venv.sh not found at {setup_script}", file=sys.stderr)
            print("  Hint: run setup_venv.sh from the project root, or use:", file=sys.stderr)
            print("    uv run skills/edison-setup/scripts/check_environment.py", file=sys.stderr)
            return False, None, None

        try:
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
                print("  Hint: try uv venv --python 3.11 to ensure correct Python version.", file=sys.stderr)
                return False, None, None

            print("  setup_venv.sh completed, re-checking imports ...", file=sys.stderr)
            time.sleep(1)

            from edison_client import EdisonClient, JobNames
            return True, EdisonClient, JobNames

        except Exception as e:
            print(f"✗ Auto-repair failed: {e}", file=sys.stderr)
            return False, None, None


def ping_platform(client_class):
    """Check 5 (optional --ping): Submit DUMMY task to verify connectivity.

    Returns True (success), None (indeterminate/404), or False (hard failure).
    """
    api_key = os.getenv("EDISON_API_KEY")
    if not api_key:
        return False
    try:
        client = client_class(api_key=api_key)
        client.run_tasks_until_done({"name": "DUMMY", "query": "ping"})
        return True
    except Exception as e:
        msg = str(e).lower()
        # "not found" catches both "404 not found" (HTTP status text) and
        # "resource not found" (library error text) — both treated as indeterminate.
        if "404" in msg or "not found" in msg:
            print("  ⚠ Ping endpoint returned 404 (known platform issue).", file=sys.stderr)
            print("    Your API key and setup are likely fine.", file=sys.stderr)
            print("    This is a server-side issue at platform.edisonscientific.com.", file=sys.stderr)
            return None
        if "401" in msg or "unauthorized" in msg or "forbidden" in msg:
            print(f"  ✗ Authentication failed: {e}", file=sys.stderr)
            print("    Check that EDISON_API_KEY is correct.", file=sys.stderr)
        else:
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
        if ping_ok is True:
            print("  ✓ Platform connection confirmed", file=sys.stderr)
        elif ping_ok is None:
            print("  ⚠ Platform connectivity indeterminate (404 on ping endpoint)", file=sys.stderr)
        else:
            print("✗ Platform connectivity failed", file=sys.stderr)
            sys.exit(1)

    # Success
    print("\n✓ Edison environment is ready", file=sys.stderr)
    print(f"  Project root: {project_root}", file=sys.stderr)
    print(f"  API key: {os.getenv('EDISON_API_KEY', '')[:10]}...", file=sys.stderr)
    sys.exit(0)


if __name__ == "__main__":
    main()
