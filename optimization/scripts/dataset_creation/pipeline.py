#!/usr/bin/env python3
"""
Dataset Pipeline Manager.

Orchestrates the full dataset lifecycle:
  1. clean    — Remove all generated artifacts
  2. generate — Create prompt JSONL files (sintetic_dataset_generator.py)
  3. validate — Send prompts to 8B teacher and validate (teacher_dataset_evaluator.py)
  4. analyze  — Analyze invalid outputs (analyze_invalid_output.py)

Usage:
    python pipeline.py                     # Run full pipeline (clean → generate → validate → analyze)
    python pipeline.py generate validate   # Run only specific steps
    python pipeline.py clean               # Clean only
    python pipeline.py validate --category explicit  # Forward args to validate step
    python pipeline.py analyze --summary   # Forward args to analyze step
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent

STEPS = {
    "clean": {
        "description": "Remove all generated artifacts",
        "command": [sys.executable, str(SCRIPT_DIR / "teacher_dataset_evaluator.py"), "--clean_results"],
    },
    "generate": {
        "description": "Generate prompt JSONL files from strategies",
        "command": [sys.executable, str(SCRIPT_DIR / "sintetic_dataset_generator.py")],
    },
    "validate": {
        "description": "Send prompts to 8B teacher and validate responses",
        "command": [sys.executable, str(SCRIPT_DIR / "teacher_dataset_evaluator.py")],
    },
    "analyze": {
        "description": "Analyze invalid outputs",
        "command": [sys.executable, str(SCRIPT_DIR / "analyze_invalid_output.py"), "--summary"],
    },
}

STEP_ORDER = ["clean", "generate", "validate", "analyze"]


def run_step(name, extra_args=None):
    """Run a single pipeline step."""
    step = STEPS[name]
    cmd = step["command"] + (extra_args or [])

    print()
    print("=" * 60)
    print(f"  STEP: {name} — {step['description']}")
    print(f"  CMD:  {' '.join(cmd)}")
    print("=" * 60)
    print()

    t0 = time.time()
    result = subprocess.run(cmd, cwd=SCRIPT_DIR)
    elapsed = time.time() - t0

    if result.returncode != 0:
        print(f"\nERROR: '{name}' failed (exit code {result.returncode}) after {elapsed:.1f}s")
        sys.exit(result.returncode)

    print(f"\n  '{name}' completed in {elapsed:.1f}s")
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Dataset Pipeline Manager — orchestrates clean → generate → validate → analyze",
        usage="python pipeline.py [steps...] [-- step_args...]",
    )
    parser.add_argument(
        "steps",
        nargs="*",
        choices=STEP_ORDER + [[]],
        default=[],
        help=f"Steps to run (default: all). Options: {', '.join(STEP_ORDER)}",
    )
    parser.add_argument(
        "--category", "-c",
        action="append",
        help="Forward --category to validate/analyze steps",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Forward --summary to analyze step",
    )
    parser.add_argument(
        "--max-examples", "-n",
        type=int,
        help="Forward --max-examples to validate step",
    )
    parser.add_argument(
        "--skip-clean",
        action="store_true",
        help="Run full pipeline but skip the clean step",
    )

    # Split on '--' to allow passing raw args to steps
    args = parser.parse_args()

    # Determine which steps to run
    steps = args.steps if args.steps else STEP_ORDER
    if args.skip_clean and "clean" in steps:
        steps = [s for s in steps if s != "clean"]

    print("=" * 60)
    print("  DATASET PIPELINE")
    print(f"  Steps: {' → '.join(steps)}")
    print("=" * 60)

    t_total = time.time()

    for step_name in steps:
        extra = []

        # Forward relevant flags to validate step
        if step_name == "validate":
            if args.category:
                for c in args.category:
                    extra += ["--category", c]
            if args.max_examples:
                extra += ["--max-examples", str(args.max_examples)]

        # Forward relevant flags to analyze step
        if step_name == "analyze":
            if args.category:
                for c in args.category:
                    extra += ["-c", c]
            if args.summary:
                extra += ["--summary"]

        run_step(step_name, extra)

    elapsed_total = time.time() - t_total
    print()
    print("=" * 60)
    print(f"  PIPELINE COMPLETE — {len(steps)} steps in {elapsed_total:.1f}s")
    print("=" * 60)


if __name__ == "__main__":
    main()
