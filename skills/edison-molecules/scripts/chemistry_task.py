#!/usr/bin/env python3
"""
skills/edison-molecules/scripts/chemistry_task.py

Submit chemistry and molecular design tasks to the Edison Phoenix agent.

Usage:
    python chemistry_task.py --query "Design an inhibitor of X with property Y"
    python chemistry_task.py --query "..." --verbose
    python chemistry_task.py --query "..." --continued-from <task_id>
    python chemistry_task.py --query "..." --output results/design.md
"""
# /// script
# requires-python = ">=3.11"
# dependencies = ["edison-client", "python-dotenv"]
# ///

import argparse
import os
import sys
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


def main():
    parser = argparse.ArgumentParser(description="Edison Molecules / Chemistry Tasks")
    parser.add_argument("--query", required=True,
                        help="Chemistry question or design task")
    parser.add_argument("--verbose", action="store_true",
                        help="Include full agent state and tool call trace")
    parser.add_argument("--continued-from", metavar="TASK_ID",
                        help="Chain this query as a follow-up to a prior task")
    parser.add_argument("--output", metavar="PATH",
                        help="Save Markdown output to this file path")
    args = parser.parse_args()

    api_key = os.getenv("EDISON_API_KEY")
    if not api_key:
        print("✗ EDISON_API_KEY not set in environment or .env", file=sys.stderr)
        sys.exit(1)

    client = EdisonClient(api_key=api_key)

    runtime_config = {}
    if args.continued_from:
        runtime_config["continued_job_id"] = args.continued_from

    task = TaskRequest(
        name=JobNames.MOLECULES,
        query=args.query,
        runtime_config=runtime_config if runtime_config else None,
    )

    print(f"Submitting chemistry task: {args.query!r}", file=sys.stderr)
    print("Waiting for Phoenix agent (may take 60–180 seconds) ...", file=sys.stderr)

    response = client.run_tasks_until_done(task, verbose=args.verbose)

    task_id = getattr(response, "id", getattr(response, "task_id", "unknown"))
    answer = getattr(response, "answer", "No answer returned.")
    formatted = getattr(response, "formatted_answer", None)

    # ── Render Markdown output ────────────────────────────────────────────────
    lines = [
        "# Edison Chemistry Task",
        f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
        "",
        "## Query",
        "",
        args.query,
        "",
        "## Result",
        "",
        formatted or answer,
        "",
        f"*Task ID: `{task_id}`*",
        "",
    ]

    if args.verbose:
        lines += [
            "## Verbose: Agent Tool Calls",
            "",
            "```",
            str(getattr(response, "agent_state", "N/A"))[:6000],
            "```",
        ]

    output_text = "\n".join(lines)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output_text, encoding="utf-8")
        print(f"✓ Output saved to: {out_path}", file=sys.stderr)
    else:
        print(output_text)

    print(f"\n=== TASK ID (save for follow-ups) ===\n{task_id}", file=sys.stderr)


if __name__ == "__main__":
    main()
