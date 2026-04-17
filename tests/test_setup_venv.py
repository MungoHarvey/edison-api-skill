"""Tests for OS detection logic in setup_venv.sh.

Runs relevant bash fragments in a subprocess to verify path and version logic.
"""
import subprocess
import shutil

import pytest


def _bash_available() -> bool:
    return shutil.which("bash") is not None


skip_no_bash = pytest.mark.skipif(not _bash_available(), reason="bash not on PATH")


DETECT_FRAGMENT = """\
#!/usr/bin/env bash
_OS="$1"
if [[ "$_OS" == MINGW* || "$_OS" == CYGWIN* ]]; then
    VENV_PY=".venv/Scripts/python.exe"
elif [[ "$_OS" == Darwin || "$_OS" == Linux ]]; then
    VENV_PY=".venv/bin/python"
else
    echo "WARNING: unrecognised OS ($_OS)" >&2
    VENV_PY=".venv/bin/python"
fi
echo "$VENV_PY"
"""

VERSION_FRAGMENT = """\
#!/usr/bin/env bash
MAJOR="$1"
MINOR="$2"
if [ "$MAJOR" -lt 3 ] || { [ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 11 ]; }; then
    echo "ERROR: Python 3.11+ required" >&2
    exit 1
fi
echo "OK"
"""


def _run_bash_script(script_text: str, *args: str) -> tuple[int, str, str]:
    result = subprocess.run(
        ["bash", "-s", "--"] + list(args),
        input=script_text.encode("utf-8"),  # bytes avoids Windows \r\n translation
        capture_output=True,
    )
    return result.returncode, result.stdout.decode().strip(), result.stderr.decode().strip()


@skip_no_bash
def test_mingw_uses_scripts_path():
    rc, out, _ = _run_bash_script(DETECT_FRAGMENT, "MINGW64_NT-10.0-26100")
    assert rc == 0
    assert "Scripts/python.exe" in out


@skip_no_bash
def test_cygwin_uses_scripts_path():
    rc, out, _ = _run_bash_script(DETECT_FRAGMENT, "CYGWIN_NT-10.0")
    assert rc == 0
    assert "Scripts/python.exe" in out


@skip_no_bash
def test_darwin_uses_bin_path():
    rc, out, _ = _run_bash_script(DETECT_FRAGMENT, "Darwin")
    assert rc == 0
    assert "bin/python" in out
    assert "Scripts" not in out


@skip_no_bash
def test_linux_uses_bin_path():
    rc, out, _ = _run_bash_script(DETECT_FRAGMENT, "Linux")
    assert rc == 0
    assert "bin/python" in out


@skip_no_bash
def test_unknown_os_warns_and_uses_unix():
    rc, out, err = _run_bash_script(DETECT_FRAGMENT, "FreeBSD")
    assert rc == 0
    assert "bin/python" in out
    assert "WARNING" in err


@skip_no_bash
def test_python_311_passes_version_check():
    rc, out, _ = _run_bash_script(VERSION_FRAGMENT, "3", "11")
    assert rc == 0
    assert out == "OK"


@skip_no_bash
def test_python_310_fails_version_check():
    rc, _, err = _run_bash_script(VERSION_FRAGMENT, "3", "10")
    assert rc == 1
    assert "3.11+" in err


@skip_no_bash
def test_python_39_fails_version_check():
    rc, _, _ = _run_bash_script(VERSION_FRAGMENT, "3", "9")
    assert rc == 1


@skip_no_bash
def test_python_312_passes_version_check():
    rc, out, _ = _run_bash_script(VERSION_FRAGMENT, "3", "12")
    assert rc == 0
