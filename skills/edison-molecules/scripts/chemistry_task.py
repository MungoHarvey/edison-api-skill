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
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "_common"))
from edison_retry import (
    add_retry_args, load_api_key, submit_with_retry, truncation_prefix,
    DEFAULT_MAX_STEPS,
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
    add_retry_args(parser)
    args = parser.parse_args()

    max_retries = 0 if args.no_retry else args.max_retries
    api_key = load_api_key()
    client = EdisonClient(api_key=api_key)

    def _build_task(budget: int) -> TaskRequest:
        runtime_config: dict = {"max_steps": budget}
        if args.continued_from:
            runtime_config["continued_job_id"] = args.continued_from
        return TaskRequest(
            name=JobNames.MOLECULES,
            query=args.query,
            runtime_config=runtime_config,
        )

    print(f"Submitting chemistry task: {args.query!r}", file=sys.stderr)
    print("Waiting for Phoenix agent (may take 60–180 seconds) ...", file=sys.stderr)

    response, was_truncated = submit_with_retry(
        client, _build_task, args.max_steps, max_retries, verbose=args.verbose
    )

    task_id = getattr(response, "task_id", getattr(response, "id", "unknown"))
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
    if was_truncated:
        output_text = truncation_prefix(max_retries + 1, args.max_steps) + output_text

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output_text, encoding="utf-8")
        print(f"✓ Output saved to: {out_path}", file=sys.stderr)
    else:
        print(output_text)

    print(f"\n=== TASK ID (save for follow-ups) ===\n{task_id}", file=sys.stderr)

    if was_truncated:
        sys.exit(2)


if __name__ == "__main__":
    main()
