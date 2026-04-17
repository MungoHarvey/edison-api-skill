#!/usr/bin/env python3
"""
skills/edison-precedent/scripts/precedent_search.py

Submit Precedent ("HasAnyone") queries to the Edison platform.
Supports single queries, chained follow-ups, and batch mode.

Usage:
    python precedent_search.py --query "Has anyone done X in Y?"
    python precedent_search.py --batch queries.txt --output results/out.md
    python precedent_search.py --query "..." --continued-from <task_id>
"""
# /// script
# requires-python = ">=3.11"
# dependencies = ["edison-client>=0.9.0", "python-dotenv"]
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


def run_precedent_query(
    client: EdisonClient,
    query: str,
    continued_from: str | None = None,
) -> dict:
    """Run a single precedent query and return a result dict."""
    runtime_config = {}
    if continued_from:
        runtime_config["continued_job_id"] = continued_from

    task = TaskRequest(
        name=JobNames.PRECEDENT,
        query=query,
        runtime_config=runtime_config if runtime_config else None,
    )

    print(f"  Querying: {query!r}", file=sys.stderr)
    response = client.run_tasks_until_done(task)

    task_id = getattr(response, "id", getattr(response, "task_id", "unknown"))

    return {
        "query": query,
        "answer": getattr(response, "answer", "No answer returned."),
        "formatted_answer": getattr(response, "formatted_answer", None),
        "has_successful_answer": getattr(response, "has_successful_answer", None),
        "task_id": task_id,
    }


def render_result(result: dict, index: int = 1) -> str:
    """Render a single result as a Markdown section."""
    success_label = {True: "✓ Yes / Found", False: "✗ Not found / Ambiguous", None: "Unknown"}.get(
        result["has_successful_answer"]
    )

    lines = [
        f"## Query {index}: {result['query']}",
        "",
        f"**Result:** {success_label}",
        "",
        result["formatted_answer"] or result["answer"],
        "",
        f"*Task ID: `{result['task_id']}`*",
        "",
        "---",
        "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Edison Precedent Search")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--query", help="Single precedent question")
    group.add_argument("--batch", metavar="FILE", help="Text file with one question per line")

    parser.add_argument("--continued-from", metavar="TASK_ID",
                        help="Chain this query as a follow-up (single-query mode only)")
    parser.add_argument("--output", metavar="PATH",
                        help="Save Markdown results to this file")
    args = parser.parse_args()

    api_key = os.getenv("EDISON_API_KEY")
    if not api_key:
        print("✗ EDISON_API_KEY not set in environment or .env", file=sys.stderr)
        sys.exit(1)

    client = EdisonClient(api_key=api_key)

    # ── Collect queries ───────────────────────────────────────────────────────
    if args.query:
        queries = [args.query]
    else:
        batch_path = Path(args.batch)
        if not batch_path.exists():
            print(f"✗ Batch file not found: {batch_path}", file=sys.stderr)
            sys.exit(1)
        queries = [
            line.strip()
            for line in batch_path.read_text().splitlines()
            if line.strip() and not line.startswith("#")
        ]
        print(f"Loaded {len(queries)} queries from {batch_path}", file=sys.stderr)

    # ── Run queries ───────────────────────────────────────────────────────────
    results = []
    for i, query in enumerate(queries, 1):
        print(f"\n[{i}/{len(queries)}] Running precedent search ...", file=sys.stderr)
        continued_from = args.continued_from if (i == 1 and args.query) else None
        result = run_precedent_query(client, query, continued_from)
        results.append(result)

    # ── Render output ─────────────────────────────────────────────────────────
    header = [
        "# Edison Precedent Search Results",
        f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
        f"*Queries run: {len(results)}*",
        "",
    ]
    body = "".join(render_result(r, i) for i, r in enumerate(results, 1))
    full_output = "\n".join(header) + "\n" + body

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(full_output, encoding="utf-8")
        print(f"\n✓ Results saved to: {out_path}", file=sys.stderr)
    else:
        print(full_output)

    # Print task IDs for chaining
    print("\n=== TASK IDs (for follow-up chaining) ===", file=sys.stderr)
    for r in results:
        print(f"  {r['task_id']}  ← {r['query'][:60]}...", file=sys.stderr)


if __name__ == "__main__":
    main()
