"""
Analyze invalid responses from the dataset generation.

Reads all *_results.jsonl files from the 4 dataset categories
and reports on invalid entries.

Usage:
    python analyze_invalid_output.py --invalid_count
    python analyze_invalid_output.py --summary
    python analyze_invalid_output.py --summary -c explicit
    python analyze_invalid_output.py --analyze 1
    python analyze_invalid_output.py --analyze 1 -c implicit
"""

import argparse
import json
import sys
from pathlib import Path
from collections import Counter

import yaml

# ============================================================
# CONFIGURATION
# ============================================================

CONFIG_PATH = Path(__file__).resolve().parents[2] / "scripts" / "destillation" / "config.yaml"


def load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return yaml.safe_load(f)
    return {}


CONFIG = load_config()
DATASET_DIR = Path(CONFIG.get("paths", {}).get("dataset_dir", ""))
if not DATASET_DIR.is_absolute():
    DATASET_DIR = (Path(__file__).parent / DATASET_DIR).resolve()

CATEGORY_KEYS = {
    "explicit": "dataset_explicit",
    "implicit": "dataset_implicit",
    "natural_language": "dataset_natural_language",
    "invalids": "dataset_invalids",
}


def get_results_path(category_key):
    """Get the *_results.jsonl path for a category."""
    prompts_rel = CONFIG.get("paths", {}).get(category_key, "")
    prompts_path = DATASET_DIR / prompts_rel
    results_name = prompts_path.stem.replace("_prompts", "_results") + ".jsonl"
    return prompts_path.parent / results_name


# ============================================================
# LOAD ENTRIES
# ============================================================

def load_entries(categories=None, only_invalid=False):
    """Load entries from results files.

    Args:
        categories: list of category names to load, or None for all.
        only_invalid: if True, only return invalid entries.

    Returns:
        list of (category_name, entry) tuples.
    """
    results = []
    cats = categories or list(CATEGORY_KEYS.keys())

    for cat_name in cats:
        cat_key = CATEGORY_KEYS.get(cat_name)
        if not cat_key:
            print(f"WARNING: Unknown category '{cat_name}'")
            continue

        path = get_results_path(cat_key)
        if not path.exists():
            print(f"WARNING: Results not found: {path}")
            continue

        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                if only_invalid and entry.get("validation", {}).get("valid", True):
                    continue
                entry["_category"] = cat_name
                results.append(entry)

    return results


# ============================================================
# COMMANDS
# ============================================================

def cmd_invalid_count(categories=None):
    """Show total count of invalid responses."""
    invalids = load_entries(categories=categories, only_invalid=True)
    all_entries = load_entries(categories=categories)

    print(f"Total entries:   {len(all_entries)}")
    print(f"Total invalid:   {len(invalids)}")
    if all_entries:
        print(f"Invalid rate:    {len(invalids)/len(all_entries)*100:.1f}%")
    print()

    # Per category
    by_cat = Counter()
    total_by_cat = Counter()
    for e in all_entries:
        total_by_cat[e["_category"]] += 1
    for e in invalids:
        by_cat[e["_category"]] += 1

    print(f"  {'Category':<20s} {'Invalid':>8s} {'Total':>8s} {'Rate':>7s}")
    print(f"  {'-'*20} {'-'*8} {'-'*8} {'-'*7}")
    for cat in sorted(total_by_cat.keys()):
        inv = by_cat.get(cat, 0)
        tot = total_by_cat[cat]
        rate = inv / tot * 100 if tot > 0 else 0
        print(f"  {cat:<20s} {inv:>8d} {tot:>8d} {rate:>6.1f}%")


def cmd_summary(categories=None):
    """Show summary of invalid responses grouped by issue and category."""
    invalids = load_entries(categories=categories, only_invalid=True)

    if not invalids:
        print("No invalid responses found.")
        return

    print(f"Total invalid responses: {len(invalids)}")
    print()

    # Group by dataset category
    by_category = Counter()
    for entry in invalids:
        by_category[entry["_category"]] += 1

    print("By dataset category:")
    print(f"  {'Category':<20s} {'Count':>6s} {'%':>7s}")
    print(f"  {'-'*20} {'-'*6} {'-'*7}")
    for cat, count in by_category.most_common():
        pct = count / len(invalids) * 100
        print(f"  {cat:<20s} {count:>6d} {pct:>6.1f}%")
    print()

    # Group by use_case
    by_uc = Counter()
    for entry in invalids:
        by_uc[entry.get("use_case", "?")] += 1

    print("By use case:")
    print(f"  {'Use Case':<10s} {'Count':>6s} {'%':>7s}")
    print(f"  {'-'*10} {'-'*6} {'-'*7}")
    for uc, count in by_uc.most_common():
        pct = count / len(invalids) * 100
        print(f"  {uc:<10s} {count:>6d} {pct:>6.1f}%")
    print()

    # Group by subcategory
    by_sub = Counter()
    for entry in invalids:
        by_sub[entry.get("subcategory", "?")] += 1

    print("By subcategory:")
    print(f"  {'Subcategory':<40s} {'Count':>6s} {'%':>7s}")
    print(f"  {'-'*40} {'-'*6} {'-'*7}")
    for sub, count in by_sub.most_common():
        pct = count / len(invalids) * 100
        print(f"  {sub:<40s} {count:>6d} {pct:>6.1f}%")
    print()

    # Group by issue type
    by_issue = Counter()
    for entry in invalids:
        for issue in entry.get("validation", {}).get("issues", []):
            by_issue[issue] += 1

    print("By issue type:")
    print(f"  {'Issue':<70s} {'Count':>6s}")
    print(f"  {'-'*70} {'-'*6}")
    for issue, count in by_issue.most_common():
        print(f"  {issue:<70s} {count:>6d}")
    print()

    # Group by subcategory + issue
    by_sub_issue = Counter()
    for entry in invalids:
        for issue in entry.get("validation", {}).get("issues", []):
            by_sub_issue[(entry.get("subcategory", "?"), issue)] += 1

    print("By subcategory + issue:")
    print(f"  {'Subcategory':<30s} {'Issue':<50s} {'Count':>6s}")
    print(f"  {'-'*30} {'-'*50} {'-'*6}")
    for (sub, issue), count in by_sub_issue.most_common():
        print(f"  {sub:<30s} {issue:<50s} {count:>6d}")


def cmd_analyze(index, categories=None):
    """Analyze a specific invalid response by index (1-based)."""
    invalids = load_entries(categories=categories, only_invalid=True)
    total = len(invalids)

    if total == 0:
        print("No invalid responses found.")
        return

    if index < 1:
        print(f"ERROR: Index must be >= 1. You provided: {index}")
        sys.exit(1)
    if index > total:
        print(f"ERROR: Index must be <= {total} (total invalids). You provided: {index}")
        sys.exit(1)

    entry = invalids[index - 1]

    print(f"{'='*70}")
    print(f"INVALID RESPONSE #{index} of {total}")
    print(f"{'='*70}")
    print()

    # Metadata
    print(f"Dataset category: {entry.get('_category', '?')}")
    print(f"Use case:         {entry.get('use_case', '?')}")
    print(f"Subcategory:      {entry.get('subcategory', '?')}")
    print()

    # Input (what was sent to the model)
    print(f"{'─'*70}")
    print("INPUT (JSON sent to the 8B model):")
    print(f"{'─'*70}")
    input_obj = entry.get("input", {})
    print(json.dumps(input_obj, indent=2, ensure_ascii=False))
    print()

    # Expected output
    print(f"{'─'*70}")
    print("EXPECTED OUTPUT:")
    print(f"{'─'*70}")
    expected = entry.get("expected_output", {})
    print(f"  result_type: {expected.get('result_type')}")
    cmd = expected.get("command")
    if cmd:
        print(f"  command:     {cmd.get('name')} {cmd.get('parameters', {})}")
    else:
        print(f"  command:     null")
    print(f"  follow_up:   {expected.get('follow_up')}")
    print()

    # Actual response
    print(f"{'─'*70}")
    print("ACTUAL RESPONSE (what the 8B model returned):")
    print(f"{'─'*70}")
    response = entry.get("response")
    if response is None:
        print("  (no response — connection error)")
    else:
        try:
            parsed = json.loads(response)
            print(json.dumps(parsed, indent=2, ensure_ascii=False))
        except json.JSONDecodeError:
            print(response)
    print()

    # Validation details
    print(f"{'─'*70}")
    print("VALIDATION:")
    print(f"{'─'*70}")
    v = entry.get("validation", {})
    print(f"  Valid:       {v.get('valid')}")
    print(f"  Is JSON:     {v.get('is_json')}")
    print(f"  result_type: {v.get('result_type')}")
    print(f"  Command:     {v.get('command_name')}")
    print(f"  Landmarks:   {v.get('landmarks')}")
    print(f"  Issues:      {v.get('issues')}")
    print()

    # Inference metrics
    print(f"{'─'*70}")
    print("METRICS:")
    print(f"{'─'*70}")
    m = entry.get("metrics", {})
    print(f"  Inference time: {m.get('total_duration_ms', 0):.0f} ms")
    print(f"  Wall time:      {m.get('wall_time_ms', 0):.0f} ms")
    print(f"  Prompt tokens:  {m.get('prompt_tokens', 0)}")
    print(f"  Output tokens:  {m.get('completion_tokens', 0)}")
    print()

    # Navigation hints
    print(f"{'─'*70}")
    nav = []
    if index > 1:
        nav.append(f"Previous: --analyze {index - 1}")
    if index < total:
        nav.append(f"Next:     --analyze {index + 1}")
    nav.append(f"Range:    1 to {total}")
    for hint in nav:
        print(f"  {hint}")
    print()


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Analyze invalid responses from the training dataset"
    )
    parser.add_argument(
        "--invalid_count",
        action="store_true",
        help="Show total count of invalid responses",
    )
    parser.add_argument(
        "--analyze",
        type=int,
        metavar="N",
        help="Analyze invalid response number N (1-based index)",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Show summary grouped by category and issue type",
    )
    parser.add_argument(
        "--category", "-c",
        choices=list(CATEGORY_KEYS.keys()),
        action="append",
        help="Filter by dataset category (can repeat). Default: all",
    )

    args = parser.parse_args()

    if not any([args.invalid_count, args.analyze is not None, args.summary]):
        parser.print_help()
        print("\nExamples:")
        print("  python analyze_invalid_output.py --invalid_count")
        print("  python analyze_invalid_output.py --summary")
        print("  python analyze_invalid_output.py --summary -c explicit")
        print("  python analyze_invalid_output.py --summary -c explicit -c implicit")
        print("  python analyze_invalid_output.py --analyze 1")
        print("  python analyze_invalid_output.py --analyze 1 -c invalids")
        sys.exit(1)

    if args.invalid_count:
        cmd_invalid_count(categories=args.category)

    if args.summary:
        cmd_summary(categories=args.category)

    if args.analyze is not None:
        cmd_analyze(args.analyze, categories=args.category)


if __name__ == "__main__":
    main()
