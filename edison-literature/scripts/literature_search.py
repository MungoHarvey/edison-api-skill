#!/usr/bin/env python3
"""
edison-literature/scripts/literature_search.py

Submit a Literature search query to the Edison platform and print/save the result.
Optionally chain from a prior task for follow-up queries.

Usage:
    python literature_search.py --query "Your scientific question"
    python literature_search.py --query "..." --verbose
    python literature_search.py --query "..." --continued-from <task_id>
    python literature_search.py --query "..." --output results/answer.md
"""

import argparse
import os
import sys
from pathlib import Path
from datetime import datetime

# ── Environment setup ─────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    root = Path(__file__).resolve()
    for _ in range(8):
        root = root.parent
        if (root / ".env").exists():
            load_dotenv(root / ".env")
            break
except ImportError:
    pass  # .env loaded from shell environment instead

try:
    from edison_client import EdisonClient, JobNames
    from edison_client.models.app import TaskRequest
except ImportError:
    print("✗ edison-client not installed. Run setup_venv.sh first.", file=sys.stderr)
    sys.exit(1)


def build_task(query: str, verbose: bool, continued_from: str | None) -> TaskRequest:
    """Construct the TaskRequest with optional chaining and verbosity."""
    runtime_config = {}

    if continued_from:
        runtime_config["continued_job_id"] = continued_from

    return TaskRequest(
        name=JobNames.LITERATURE,
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
    parser.add_argument("--output", metavar="PATH",
                        help="Save formatted Markdown output to this file path")
    args = parser.parse_args()

    api_key = os.getenv("EDISON_API_KEY")
    if not api_key:
        print("✗ EDISON_API_KEY not set in environment or .env", file=sys.stderr)
        sys.exit(1)

    client = EdisonClient(api_key=api_key)
    task = build_task(args.query, args.verbose, args.continued_from)

    print(f"Submitting literature query: {args.query!r}", file=sys.stderr)
    print("Waiting for response (this may take 30–120 seconds) ...", file=sys.stderr)

    response = client.run_tasks_until_done(task, verbose=args.verbose)

    # Print task ID for future chaining
    task_id = getattr(response, "id", getattr(response, "task_id", None))
    print(f"\n=== TASK ID (save for follow-ups) ===\n{task_id}\n", file=sys.stderr)

    # Render output
    output_text = format_output(response, args.verbose)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output_text, encoding="utf-8")
        print(f"✓ Output saved to: {out_path}", file=sys.stderr)
    else:
        print(output_text)

    # Surface success flag as exit code
    if getattr(response, "has_successful_answer", True) is False:
        print("⚠ Agent reported no successful answer found.", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
