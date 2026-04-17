#!/usr/bin/env python3
"""
skills/edison-evaluation/scripts/evaluate_skills.py

Evaluate Edison skill health and performance by running test queries.

Modes:
  --quick (default):  DUMMY tasks only, validates connectivity + imports (free)
  --full:             Real test queries for each skill type (uses credits)

Usage:
  # Quick check (instant, free)
  python evaluate_skills.py --quick

  # Full evaluation of all skills
  python evaluate_skills.py --skill all --full --output results/eval.md

  # Specific skill
  python evaluate_skills.py --skill literature --full --output results/eval.md
"""
# /// script
# requires-python = ">=3.11"
# dependencies = ["edison-client", "python-dotenv"]
# ///

import sys
import os
import argparse
import time
import json
from pathlib import Path
from datetime import datetime
import re

# ── Load .env from project root ──────────────────────────────────────────────
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

# ── Import Edison client ─────────────────────────────────────────────────────
try:
    from edison_client import EdisonClient, JobNames
except ImportError as e:
    print(f"✗ Import failed: {e}\n  Run setup_venv.sh to install dependencies.", file=sys.stderr)
    sys.exit(1)


def _has_literature_high() -> bool:
    """Check at runtime whether LITERATURE_HIGH is available in the installed package."""
    return hasattr(JobNames, "LITERATURE_HIGH")


# ── Constants ────────────────────────────────────────────────────────────────

TEST_QUERIES = {
    "literature": "What is the role of TDP-43 in ALS pathogenesis?",
    "literature_high": "What is the role of TDP-43 in ALS pathogenesis?",
    "precedent": "Has anyone performed iPSC differentiation to motor neurons for ALS modelling?",
    "molecules": "What is the SMILES for aspirin?",
    "analysis": None,  # Special case: embedded CSV
}

# Embedded test dataset for analysis skill
ANALYSIS_TEST_CSV = """gene_id,control_mean,als_mean
TP53,5.2,4.8
TARDBP,6.1,2.3
SOD1,5.8,1.9
FUS,5.5,3.2
"""

ANALYSIS_TEST_QUERY = "Are any genes significantly downregulated in ALS vs control?"


# ── Evaluation functions ─────────────────────────────────────────────────────

def evaluate_dummy(client, skill_name):
    """Quick validation using DUMMY task."""
    start = time.perf_counter()
    try:
        response = client.run_tasks_until_done({
            "name": JobNames.DUMMY,
            "query": f"ping {skill_name}"
        })
        elapsed = time.perf_counter() - start

        success = hasattr(response, 'answer') or str(response).strip()
        answer = getattr(response, 'answer', str(response))[:200]

        return {
            "pass": success,
            "latency": elapsed,
            "answer": answer,
            "test_type": "connectivity"
        }
    except Exception as e:
        return {
            "pass": False,
            "latency": time.perf_counter() - start,
            "answer": f"Error: {str(e)[:100]}",
            "test_type": "connectivity"
        }


def evaluate_skill(client, skill_type, query):
    """Run a real test query against a skill."""
    job_name_map = {
        "literature": JobNames.LITERATURE,
        "precedent": JobNames.PRECEDENT,
        "molecules": JobNames.MOLECULES,
        "analysis": JobNames.ANALYSIS,
    }
    if _has_literature_high():
        job_name_map["literature_high"] = JobNames.LITERATURE_HIGH

    if skill_type not in job_name_map:
        return {"pass": False, "latency": 0, "answer": "Unknown skill type"}

    job_name = job_name_map[skill_type]
    start = time.perf_counter()

    try:
        response = client.run_tasks_until_done({
            "name": job_name,
            "query": query
        })
        elapsed = time.perf_counter() - start

        # Extract fields from response
        has_successful_answer = getattr(response, 'has_successful_answer', False)
        answer = getattr(response, 'formatted_answer', getattr(response, 'answer', ''))

        # Count citations for literature / literature_high
        citations = (
            len(re.findall(r'\[\d+\]', str(answer)))
            if skill_type in ("literature", "literature_high")
            else None
        )

        return {
            "pass": has_successful_answer,
            "latency": elapsed,
            "answer": str(answer)[:300],
            "answer_length": len(str(answer)),
            "citations": citations,
            "test_type": "real"
        }

    except Exception as e:
        elapsed = time.perf_counter() - start
        return {
            "pass": False,
            "latency": elapsed,
            "answer": f"Error: {str(e)[:100]}",
            "test_type": "real"
        }


def evaluate_analysis_skill(client):
    """Special case: analysis skill with embedded test CSV."""
    job_name = JobNames.ANALYSIS

    # Prepare the payload: CSV data + question
    query_with_data = f"{ANALYSIS_TEST_CSV}\n\nQuestion: {ANALYSIS_TEST_QUERY}"

    start = time.perf_counter()
    try:
        response = client.run_tasks_until_done({
            "name": job_name,
            "query": query_with_data
        })
        elapsed = time.perf_counter() - start

        has_successful_answer = getattr(response, 'has_successful_answer', False)
        answer = getattr(response, 'formatted_answer', getattr(response, 'answer', ''))

        return {
            "pass": has_successful_answer,
            "latency": elapsed,
            "answer": str(answer)[:300],
            "answer_length": len(str(answer)),
            "citations": None,
            "test_type": "real"
        }

    except Exception as e:
        elapsed = time.perf_counter() - start
        return {
            "pass": False,
            "latency": elapsed,
            "answer": f"Error: {str(e)[:100]}",
            "test_type": "real"
        }


# ── Report generation ────────────────────────────────────────────────────────

def format_report(results, skills, mode):
    """Generate Markdown report."""
    lines = [
        f"# Edison Skill Evaluation Report",
        f"\n**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Mode:** {'Quick (DUMMY only)' if mode == 'quick' else 'Full (real queries)'}",
        f"**Skills tested:** {', '.join(skills)}",
        f"\n## Summary\n",
    ]

    # Summary table
    lines.append("| Skill | Status | Latency (s) | Answer Length | Citations | Test Query |")
    lines.append("|---|---|---|---|---|---|")

    all_pass = True
    for skill in skills:
        if skill not in results:
            continue

        result = results[skill]
        status = "✓ Pass" if result["pass"] else "✗ Fail"
        latency = f"{result['latency']:.2f}"
        answer_len = result.get("answer_length", len(result.get("answer", "")))
        citations = result.get("citations", "—")
        test_query = TEST_QUERIES.get(skill, "custom")

        lines.append(f"| {skill} | {status} | {latency} | {answer_len} | {citations} | {test_query[:30]}... |")

        if not result["pass"]:
            all_pass = False

    # Detailed results
    lines.append(f"\n## Detailed Results\n")

    for skill in skills:
        if skill not in results:
            continue

        result = results[skill]
        status = "✓ PASS" if result["pass"] else "✗ FAIL"
        test_type = result.get("test_type", "unknown")

        lines.append(f"### {skill.capitalize()} — {status} ({test_type})")
        lines.append(f"\n**Query:** {TEST_QUERIES.get(skill, 'N/A')}")
        lines.append(f"**Latency:** {result['latency']:.2f}s")
        lines.append(f"**Answer preview:** {result.get('answer', 'N/A')[:150]}...")
        lines.append("")

    # Summary line
    lines.append(f"\n## Result\n")
    if all_pass:
        lines.append(f"✓ **All {len(skills)} skill(s) passed.** Edison is ready to use.")
    else:
        failed = [s for s in skills if not results[s]["pass"]]
        lines.append(f"✗ **Failed:** {', '.join(failed)}")
        lines.append(f"\nSee detailed results above for diagnostics.")

    return "\n".join(lines)


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Evaluate Edison skill health and performance."
    )
    parser.add_argument(
        "--skill",
        choices=["literature", "literature_high", "precedent", "molecules", "analysis", "all"],
        default="all",
        help="Skill to evaluate (default: all). Note: literature_high is excluded from "
             "'all' — test it explicitly with --skill literature_high --full."
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run real skill queries (uses API credits); default is --quick (DUMMY only)"
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Quick connectivity check (DUMMY only, free) — default mode"
    )
    parser.add_argument(
        "--output",
        help="Save report to file (Markdown)"
    )

    args = parser.parse_args()

    # Determine mode
    mode = "full" if args.full else "quick"

    # Determine skills to test
    # Note: literature_high is excluded from 'all' — slow and expensive by default.
    # Test it explicitly with --skill literature_high --full.
    skills_to_test = ["all"] if args.skill == "all" else [args.skill]
    if skills_to_test == ["all"]:
        skills_to_test = ["literature", "precedent", "molecules", "analysis"]

    # Guard: check LITERATURE_HIGH availability before running it
    if "literature_high" in skills_to_test and not _has_literature_high():
        print(
            "✗ LITERATURE_HIGH is not available in the installed edison-client.\n"
            "  Run: python -c \"from edison_client import JobNames; "
            "print([j.name for j in JobNames])\"\n"
            "  to see available job types. Install a newer version of "
            "edison-client if needed.",
            file=sys.stderr,
        )
        sys.exit(2)

    print(f"=== Edison Skill Evaluation ({mode.upper()}) ===", file=sys.stderr)
    print(f"Skills: {', '.join(skills_to_test)}", file=sys.stderr)

    # Initialize client
    api_key = os.getenv("EDISON_API_KEY")
    if not api_key:
        print("✗ EDISON_API_KEY not set in environment", file=sys.stderr)
        sys.exit(2)

    client = EdisonClient(api_key=api_key)

    # Run evaluations
    results = {}

    for skill in skills_to_test:
        print(f"\nTesting {skill} ...", file=sys.stderr)

        if mode == "quick":
            result = evaluate_dummy(client, skill)
        elif skill == "analysis":
            result = evaluate_analysis_skill(client)
        else:
            query = TEST_QUERIES[skill]
            result = evaluate_skill(client, skill, query)

        results[skill] = result
        status = "✓" if result["pass"] else "✗"
        print(f"  {status} {skill}: {result['latency']:.2f}s", file=sys.stderr)

    # Generate report
    report = format_report(results, skills_to_test, mode)

    # Output
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report)
        print(f"\n✓ Report saved to {output_path.absolute()}", file=sys.stderr)
    else:
        print(report)

    # Exit code: 0 if all pass, 1 if any fail
    all_pass = all(results[s]["pass"] for s in results)
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
