#!/usr/bin/env python3
"""
edison-async/scripts/async_batch.py

Submit multiple Edison tasks concurrently and aggregate results.
Supports fire-and-forget submission, polling, and full async batch execution.

Usage:
    # Full batch (submit + wait for all results)
    python async_batch.py --input queries.jsonl --output results/batch.md

    # Submit only, save task IDs for later
    python async_batch.py --input queries.jsonl --submit-only --task-ids-out ids.txt

    # Poll previously submitted task IDs
    python async_batch.py --poll ids.txt --output results/batch.md
"""

import argparse
import asyncio
import json
import os
import sys
import time
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

# Map string names to JobNames enum values
JOB_NAME_MAP = {
    "LITERATURE": JobNames.LITERATURE,
    "PRECEDENT":  JobNames.PRECEDENT,
    "MOLECULES":  JobNames.MOLECULES,
    "ANALYSIS":   JobNames.ANALYSIS,
    "DUMMY":      JobNames.DUMMY,
}

POLL_INTERVAL_SECS = 15
MAX_POLL_ATTEMPTS  = 120  # ~30 minutes total


def load_queries(jsonl_path: Path) -> list[dict]:
    """Parse a JSONL file into a list of task dicts."""
    queries = []
    for i, line in enumerate(jsonl_path.read_text().splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            task = json.loads(line)
        except json.JSONDecodeError as e:
            print(f"✗ Line {i} is not valid JSON: {e}", file=sys.stderr)
            sys.exit(1)
        if "name" not in task or "query" not in task:
            print(f"✗ Line {i} missing 'name' or 'query' field", file=sys.stderr)
            sys.exit(1)
        if task["name"].upper() not in JOB_NAME_MAP:
            print(f"✗ Line {i}: unknown job name '{task['name']}'. "
                  f"Valid: {list(JOB_NAME_MAP.keys())}", file=sys.stderr)
            sys.exit(1)
        task["name"] = JOB_NAME_MAP[task["name"].upper()]
        queries.append(task)
    return queries


async def submit_all(client: EdisonClient, queries: list[dict]) -> list[tuple[str, dict]]:
    """Submit all queries concurrently and return list of (task_id, original_query)."""
    print(f"Submitting {len(queries)} tasks concurrently ...", file=sys.stderr)
    tasks = []
    for q in queries:
        task_id = await client.acreate_task(q)
        print(f"  ✓ Submitted: {str(q.get('query', ''))[:60]}... → {task_id}", file=sys.stderr)
        tasks.append((task_id, q))
    return tasks


async def poll_until_done(
    client: EdisonClient,
    submitted: list[tuple[str, dict]],
) -> list[dict]:
    """Poll all submitted tasks until all are complete or failed."""
    pending = {task_id: query for task_id, query in submitted}
    results = []
    attempt = 0

    print(f"\nPolling {len(pending)} tasks (interval: {POLL_INTERVAL_SECS}s) ...", file=sys.stderr)

    while pending and attempt < MAX_POLL_ATTEMPTS:
        await asyncio.sleep(POLL_INTERVAL_SECS)
        attempt += 1
        completed_ids = []

        for task_id, query in list(pending.items()):
            try:
                status = await client.aget_task(task_id)
                task_status = getattr(status, "status", None)

                if task_status == "success":
                    print(f"  ✓ Done: {task_id}", file=sys.stderr)
                    results.append({
                        "task_id": task_id,
                        "query": query,
                        "response": status,
                        "status": "success",
                    })
                    completed_ids.append(task_id)
                elif task_status in ("failed", "error"):
                    print(f"  ✗ Failed: {task_id}", file=sys.stderr)
                    results.append({
                        "task_id": task_id,
                        "query": query,
                        "response": None,
                        "status": "failed",
                    })
                    completed_ids.append(task_id)
                else:
                    print(f"  … Pending ({task_status}): {task_id}", file=sys.stderr)
            except Exception as e:
                print(f"  ✗ Poll error for {task_id}: {e}", file=sys.stderr)

        for task_id in completed_ids:
            del pending[task_id]

        if pending:
            print(f"  {len(pending)} tasks still pending ...", file=sys.stderr)

    if pending:
        print(f"⚠ {len(pending)} tasks did not complete within poll limit.", file=sys.stderr)
        for task_id, query in pending.items():
            results.append({"task_id": task_id, "query": query, "response": None, "status": "timeout"})

    return results


def render_results(results: list[dict], submitted_at: str) -> str:
    """Render all results as a Markdown document."""
    completed_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    success_count = sum(1 for r in results if r["status"] == "success")

    header = [
        "# Edison Batch Results",
        f"*Submitted: {submitted_at} | Completed: {completed_at}*",
        f"*Tasks: {len(results)} submitted, {success_count} succeeded, "
        f"{len(results) - success_count} failed/timed out*",
        "",
    ]

    sections = []
    for i, r in enumerate(results, 1):
        query_str = r["query"].get("query", "N/A") if isinstance(r["query"], dict) else str(r["query"])
        job_name  = str(r["query"].get("name", "")).split(".")[-1] if isinstance(r["query"], dict) else "Unknown"

        lines = [
            f"## Task {i}: {job_name}",
            "",
            f"**Query:** {query_str}",
            "",
            f"**Status:** {r['status']}",
            "",
        ]

        if r["response"] and r["status"] == "success":
            answer = getattr(r["response"], "formatted_answer", None) or getattr(r["response"], "answer", "No answer.")
            lines += [answer, ""]

        lines += [f"*Task ID: `{r['task_id']}`*", "", "---", ""]
        sections.append("\n".join(lines))

    return "\n".join(header) + "\n" + "\n".join(sections)


async def async_main(args, api_key: str):
    client = EdisonClient(api_key=api_key)
    submitted_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    if args.poll:
        # Poll-only mode: load previously saved task IDs
        ids_path = Path(args.poll)
        lines = [l.strip() for l in ids_path.read_text().splitlines() if l.strip()]
        submitted = [(line.split("\t")[0], {"query": line.split("\t")[1] if "\t" in line else "unknown"})
                     for line in lines]
        print(f"Polling {len(submitted)} previously submitted tasks ...", file=sys.stderr)
        results = await poll_until_done(client, submitted)

    else:
        # Load and submit queries
        queries = load_queries(Path(args.input))
        submitted = await submit_all(client, queries)

        if args.submit_only:
            # Save task IDs and exit
            out_path = Path(args.task_ids_out)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with out_path.open("w") as f:
                for task_id, query in submitted:
                    f.write(f"{task_id}\t{query.get('query', '')}\n")
            print(f"✓ {len(submitted)} task IDs saved to: {out_path}", file=sys.stderr)
            return

        results = await poll_until_done(client, submitted)

    # ── Output ────────────────────────────────────────────────────────────────
    output_text = render_results(results, submitted_at)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output_text, encoding="utf-8")
        print(f"\n✓ Batch results saved to: {out_path}", file=sys.stderr)
    else:
        print(output_text)


def main():
    parser = argparse.ArgumentParser(description="Edison Async Batch")
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument("--input", metavar="JSONL",
                             help="JSONL file with tasks to submit")
    mode_group.add_argument("--poll", metavar="IDS_FILE",
                             help="File with task IDs to poll (from --submit-only)")

    parser.add_argument("--submit-only", action="store_true",
                        help="Submit tasks but don't wait for results")
    parser.add_argument("--task-ids-out", metavar="FILE", default="edison_task_ids.txt",
                        help="Where to save task IDs when using --submit-only")
    parser.add_argument("--output", metavar="PATH",
                        help="Save Markdown results to this path")
    args = parser.parse_args()

    api_key = os.getenv("EDISON_API_KEY")
    if not api_key:
        print("✗ EDISON_API_KEY not set in environment or .env", file=sys.stderr)
        sys.exit(1)

    asyncio.run(async_main(args, api_key))


if __name__ == "__main__":
    main()
