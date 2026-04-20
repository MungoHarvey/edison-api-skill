#!/usr/bin/env python3
"""
skills/edison-literature/scripts/literature_search.py

Submit a Literature search query to the Edison platform and print/save the result.
Optionally chain from a prior task for follow-up queries.

Usage:
    python literature_search.py --query "Your scientific question"
    python literature_search.py --query "..." --verbose
    python literature_search.py --query "..." --continued-from <task_id>
    python literature_search.py --query "..." --output results/answer.md
"""
# /// script
# requires-python = ">=3.11"
# dependencies = ["edison-client", "python-dotenv"]
# ///

import argparse
import os
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "_common"))
from edison_retry import (
    add_retry_args, load_api_key, submit_with_retry, truncation_prefix,
    DEFAULT_MAX_STEPS, DEFAULT_MAX_RETRIES,
)
from pathlib import Path
from datetime import datetime

# ── Environment setup ─────────────────────────────────────────────────────────
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

try:
    from edison_client import EdisonClient, JobNames
    from edison_client.models.app import TaskRequest
except ImportError:
    print("✗ edison-client not installed. Run setup_venv.sh first.", file=sys.stderr)
    sys.exit(1)


def _has_literature_high() -> bool:
    """Check at runtime whether LITERATURE_HIGH is available in the installed package."""
    return hasattr(JobNames, "LITERATURE_HIGH")


def build_task(query: str, verbose: bool, continued_from: str | None,
               high: bool = False, max_steps: int = DEFAULT_MAX_STEPS) -> TaskRequest:
    """Construct the TaskRequest with optional chaining, verbosity, and high-reasoning mode."""
    runtime_config: dict = {"max_steps": max_steps}

    if continued_from:
        runtime_config["continued_job_id"] = continued_from

    if high:
        if not _has_literature_high():
            print(
                "✗ LITERATURE_HIGH is not available in the installed edison-client.\n"
                "  Run: python -c \"from edison_client import JobNames; "
                "print([j.name for j in JobNames])\"\n"
                "  to see available job types. Install a newer version of "
                "edison-client if needed.",
                file=sys.stderr,
            )
            sys.exit(1)
        job_name = JobNames.LITERATURE_HIGH
    else:
        job_name = JobNames.LITERATURE

    return TaskRequest(
        name=job_name,
        query=query,
        runtime_config=runtime_config if runtime_config else None,
    )


def format_output(response, verbose: bool) -> str:
    """Render the task response as a readable Markdown string."""
    lines = [
        f"# Edison Literature Search",
        f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
        "",
        "## Answer",
        "",
        getattr(response, "answer", "No answer returned."),
        "",
    ]

    formatted = getattr(response, "formatted_answer", None)
    if formatted and formatted != getattr(response, "answer", None):
        lines += ["## Formatted Answer (with References)", "", formatted, ""]

    success = getattr(response, "has_successful_answer", None)
    if success is not None:
        lines += [f"*Successful answer: {success}*", ""]

    if verbose:
        lines += [
            "## Verbose: Environment Frame",
            "",
            "```json",
            str(getattr(response, "environment_frame", "N/A"))[:4000],
            "```",
            "",
            "## Verbose: Agent State",
            "",
            "```json",
            str(getattr(response, "agent_state", "N/A"))[:4000],
            "```",
        ]

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Edison Literature Search")
    parser.add_argument("--query", required=True, help="Scientific question to search")
    parser.add_argument("--verbose", action="store_true",
                        help="Return full agent state and environment frame")
    parser.add_argument("--continued-from", metavar="TASK_ID",
                        help="Chain this query as a follow-up to a prior task")
    parser.add_argument("--high", action="store_true",
                        help="Use LITERATURE_HIGH (state-of-the-art reasoning, slower, "
                             "more credits). Requires compatible edison-client version.")
    parser.add_argument("--output", metavar="PATH",
                        help="Save formatted Markdown output to this file path")
    add_retry_args(parser)
    args = parser.parse_args()

    max_retries = 0 if args.no_retry else args.max_retries

    api_key = load_api_key()
    client = EdisonClient(api_key=api_key)

    print(f"Submitting literature query: {args.query!r}", file=sys.stderr)
    wait_msg = (
        "Waiting for response (LITERATURE_HIGH may take 3–10 minutes) ..."
        if args.high
        else "Waiting for response (this may take 30–120 seconds) ..."
    )
    print(wait_msg, file=sys.stderr)

    def _build_task(budget: int) -> TaskRequest:
        return build_task(args.query, args.verbose, args.continued_from,
                          high=args.high, max_steps=budget)

    response, was_truncated = submit_with_retry(
        client, _build_task, args.max_steps, max_retries, verbose=args.verbose
    )

    # Print task ID for future chaining
    task_id = getattr(response, "task_id", getattr(response, "id", None))
    print(f"\n=== TASK ID (save for follow-ups) ===\n{task_id}\n", file=sys.stderr)

    # Render output
    output_text = format_output(response, args.verbose)
    if was_truncated:
        output_text = truncation_prefix(max_retries + 1, args.max_steps) + output_text

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output_text, encoding="utf-8")
        print(f"✓ Output saved to: {out_path}", file=sys.stderr)
    else:
        print(output_text)

    if was_truncated or getattr(response, "has_successful_answer", True) is False:
        if not was_truncated:
            print("⚠ Agent reported no successful answer found.", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
