#!/usr/bin/env python3
"""
skills/edison-async/scripts/async_batch.py

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
# /// script
# requires-python = ">=3.11"
# dependencies = ["edison-client", "python-dotenv"]
# ///

import argparse
import asyncio
import json
import os
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "_common"))
from edison_retry import (
    add_retry_args, load_api_key, submit_with_retry_async, truncation_prefix,
    DEFAULT_MAX_STEPS, DEFAULT_MAX_RETRIES,
)
import time
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

# Map string names to JobNames enum values
JOB_NAME_MAP = {
    "LITERATURE": JobNames.LITERATURE,
    "PRECEDENT":  JobNames.PRECEDENT,
    "MOLECULES":  JobNames.MOLECULES,
    "ANALYSIS":   JobNames.ANALYSIS,
    "DUMMY":      JobNames.DUMMY,
}
# Conditionally add LITERATURE_HIGH if supported by the installed package
if hasattr(JobNames, "LITERATURE_HIGH"):
    JOB_NAME_MAP["LITERATURE_HIGH"] = JobNames.LITERATURE_HIGH

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


async def run_one_task(
    client: EdisonClient,
    query: dict,
    default_max_steps: int,
    max_retries: int,
) -> dict:
    """Run a single task with retry, returning a result dict."""
    row_max_steps = query.get("max_steps", default_max_steps)

    def _build_task(budget: int) -> dict:
        rt = {"max_steps": budget}
        if query.get("continued_job_id"):
            rt["continued_job_id"] = query["continued_job_id"]
        return {**query, "runtime_config": rt}

    print(f"  Submitting: {str(query.get('query', ''))[:60]}...", file=sys.stderr)
    response, was_truncated = await submit_with_retry_async(
        client, _build_task, row_max_steps, max_retries,
        poll_interval=POLL_INTERVAL_SECS, max_poll_attempts=MAX_POLL_ATTEMPTS,
    )

    task_id = getattr(response, "task_id", getattr(response, "id", "unknown")) if response else "unknown"
    status = getattr(response, "status", "unknown") if response else "timeout"

    if was_truncated:
        print(f"  ⚠ Truncated: {task_id}", file=sys.stderr)
    elif status == "success":
        print(f"  ✓ Done: {task_id}", file=sys.stderr)
    else:
        print(f"  ✗ Failed ({status}): {task_id}", file=sys.stderr)

    return {
        "task_id": task_id,
        "query": query,
        "response": response,
        "status": "truncated" if was_truncated else status,
    }


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
    truncated_count = sum(1 for r in results if r["status"] == "truncated")

    header = [
        "# Edison Batch Results",
        f"*Submitted: {submitted_at} | Completed: {completed_at}*",
        f"*Tasks: {len(results)} submitted, {success_count} succeeded, "
        f"{truncated_count} truncated, "
        f"{len(results) - success_count - truncated_count} failed/timed out*",
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

        if r["response"] and r["status"] in ("success", "truncated"):
            answer = getattr(r["response"], "formatted_answer", None) or getattr(r["response"], "answer", "No answer.")
            if r["status"] == "truncated":
                lines += ["> ⚠ This result is truncated (retries exhausted).", "", answer, ""]
            else:
                lines += [answer, ""]

        lines += [f"*Task ID: `{r['task_id']}`*", "", "---", ""]
        sections.append("\n".join(lines))

    return "\n".join(header) + "\n" + "\n".join(sections)


async def async_main(args, api_key: str, max_retries: int):
    client = EdisonClient(api_key=api_key)
    submitted_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    if args.poll:
        # Poll-only mode: load previously saved task IDs and poll (no retry support)
        ids_path = Path(args.poll)
        lines = [l.strip() for l in ids_path.read_text().splitlines() if l.strip()]
        submitted = [(line.split("\t")[0], {"query": line.split("\t")[1] if "\t" in line else "unknown"})
                     for line in lines]
        print(f"Polling {len(submitted)} previously submitted tasks ...", file=sys.stderr)
        results = await poll_until_done(client, submitted)

    elif args.submit_only:
        # Fire-and-forget: submit only, save task IDs (no retry in submit-only mode)
        queries = load_queries(Path(args.input))
        print(f"Submitting {len(queries)} tasks ...", file=sys.stderr)
        submitted = []
        for q in queries:
            task_id = await client.acreate_task(q)
            print(f"  ✓ Submitted: {str(q.get('query', ''))[:60]}... → {task_id}", file=sys.stderr)
            submitted.append((task_id, q))
        out_path = Path(args.task_ids_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w") as f:
            for task_id, query in submitted:
                f.write(f"{task_id}\t{query.get('query', '')}\n")
        print(f"✓ {len(submitted)} task IDs saved to: {out_path}", file=sys.stderr)
        return

    else:
        # Full batch: submit + wait with per-task retry
        queries = load_queries(Path(args.input))
        print(f"Running {len(queries)} tasks concurrently (with retry) ...", file=sys.stderr)
        results = await asyncio.gather(*[
            run_one_task(client, q, args.max_steps, max_retries)
            for q in queries
        ])

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
    add_retry_args(parser)
    args = parser.parse_args()

    max_retries = 0 if args.no_retry else args.max_retries
    api_key = load_api_key()

    asyncio.run(async_main(args, api_key, max_retries))


if __name__ == "__main__":
    main()
