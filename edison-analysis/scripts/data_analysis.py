#!/usr/bin/env python3
"""
edison-analysis/scripts/data_analysis.py

Submit a biological dataset and a research question to the Edison Analysis agent.

Usage:
    python data_analysis.py --query "..." --data path/to/data.csv
    python data_analysis.py --query "..." --data-inline "col1,col2\nval1,val2"
    python data_analysis.py --query "..." --data path/to/data.csv --output results/report.md
    python data_analysis.py --query "..." --continued-from <task_id>
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
    pass

try:
    from edison_client import EdisonClient, JobNames
    from edison_client.models.app import TaskRequest
except ImportError:
    print("✗ edison-client not installed. Run setup_venv.sh first.", file=sys.stderr)
    sys.exit(1)

MAX_DATA_CHARS = 20_000  # Practical limit for inline data submission


def load_data(data_path: Path) -> str:
    """Read dataset file and return as string, with size warning."""
    content = data_path.read_text(encoding="utf-8")
    if len(content) > MAX_DATA_CHARS:
        print(
            f"⚠ Data file is large ({len(content):,} chars). "
            f"Consider pre-filtering to top features. Truncating to {MAX_DATA_CHARS:,} chars.",
            file=sys.stderr,
        )
        content = content[:MAX_DATA_CHARS]
    return content


def build_query_with_data(query: str, data_str: str) -> str:
    """Embed the dataset into the query string for the agent."""
    return (
        f"{query}\n\n"
        f"Here is the dataset to analyse:\n\n"
        f"```\n{data_str}\n```"
    )


def main():
    parser = argparse.ArgumentParser(description="Edison Data Analysis")
    parser.add_argument("--query", required=True,
                        help="Biological research question to answer using the data")

    data_group = parser.add_mutually_exclusive_group()
    data_group.add_argument("--data", metavar="FILE",
                             help="Path to CSV/TSV data file")
    data_group.add_argument("--data-inline", metavar="STRING",
                             help="Inline data string (for small tables)")

    parser.add_argument("--continued-from", metavar="TASK_ID",
                        help="Chain as a follow-up to a prior analysis task")
    parser.add_argument("--verbose", action="store_true",
                        help="Include full agent state in output")
    parser.add_argument("--output", metavar="PATH",
                        help="Save Markdown report to this file path")
    args = parser.parse_args()

    api_key = os.getenv("EDISON_API_KEY")
    if not api_key:
        print("✗ EDISON_API_KEY not set in environment or .env", file=sys.stderr)
        sys.exit(1)

    # ── Build query ───────────────────────────────────────────────────────────
    query = args.query

    if args.data:
        data_path = Path(args.data)
        if not data_path.exists():
            print(f"✗ Data file not found: {data_path}", file=sys.stderr)
            sys.exit(1)
        data_str = load_data(data_path)
        query = build_query_with_data(query, data_str)
        print(f"Data loaded from: {data_path} ({len(data_str):,} chars)", file=sys.stderr)
    elif args.data_inline:
        query = build_query_with_data(query, args.data_inline)

    # ── Build task ────────────────────────────────────────────────────────────
    runtime_config = {}
    if args.continued_from:
        runtime_config["continued_job_id"] = args.continued_from

    task = TaskRequest(
        name=JobNames.ANALYSIS,
        query=query,
        runtime_config=runtime_config if runtime_config else None,
    )

    client = EdisonClient(api_key=api_key)

    print(f"Submitting analysis task ...", file=sys.stderr)
    print("Waiting for Edison Analysis agent ...", file=sys.stderr)

    response = client.run_tasks_until_done(task, verbose=args.verbose)

    task_id = getattr(response, "id", getattr(response, "task_id", "unknown"))
    answer = getattr(response, "answer", "No answer returned.")
    formatted = getattr(response, "formatted_answer", None)

    # ── Render Markdown output ────────────────────────────────────────────────
    lines = [
        "# Edison Data Analysis Report",
        f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
        "",
        "## Query",
        "",
        args.query,  # Original query, not the data-embedded version
        "",
    ]
    if args.data:
        lines += [f"*Dataset: `{args.data}`*", ""]

    lines += [
        "## Analysis Result",
        "",
        formatted or answer,
        "",
        f"*Task ID: `{task_id}`*",
        "",
    ]

    if args.verbose:
        lines += [
            "## Verbose: Agent State",
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
        print(f"✓ Report saved to: {out_path}", file=sys.stderr)
    else:
        print(output_text)

    print(f"\n=== TASK ID (save for follow-ups) ===\n{task_id}", file=sys.stderr)


if __name__ == "__main__":
    main()
