"""
Generate the 4 synthetic dataset JSONL files using the Strategy pattern.

Each Use Case has its own strategy class in strategies/.
The orchestrator instantiates all strategies, collects entries,
routes them to the correct dataset, and prints a coverage report.

Usage:
    python sintetic_dataset_generator.py

Output files:
  artifacts/dataset/explicit/explicit_prompts.jsonl
  artifacts/dataset/implicit/implicit_prompts.jsonl
  artifacts/dataset/natural_language/natural_language_prompts.jsonl
  artifacts/dataset/invalids/invalid_prompts.jsonl
"""

import json
import random
from pathlib import Path
from collections import Counter

import yaml

from strategies import STRATEGY_REGISTRY

# ============================================================
# CONFIG
# ============================================================

CONFIG_PATH = Path(__file__).resolve().parents[2] / "scripts" / "destillation" / "config.yaml"

with open(CONFIG_PATH) as f:
    CONFIG = yaml.safe_load(f)

LANDMARKS = CONFIG["dataset"]["landmarks"]
ALL_LANDMARKS = sorted(LANDMARKS)
DATASET_DIR = Path(CONFIG["paths"]["dataset_dir"])
SEED = CONFIG["dataset"].get("seed", 42)

DATASET_FILE_KEYS = {
    "explicit": "dataset_explicit",
    "implicit": "dataset_implicit",
    "natural_language": "dataset_natural_language",
    "invalids": "dataset_invalids",
}


# ============================================================
# HELPERS
# ============================================================

def write_jsonl(path, entries):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for e in entries:
            # Remove internal routing key before writing
            clean = {k: v for k, v in e.items() if not k.startswith("_")}
            f.write(json.dumps(clean, ensure_ascii=False) + "\n")
    print(f"  {path.name}: {len(entries)} entries")


# ============================================================
# COVERAGE REPORT
# ============================================================

def print_coverage_report(all_entries):
    print("\n" + "=" * 60)
    print("COVERAGE REPORT")
    print("=" * 60)

    # 1. By Use Case
    print("\n1. Coverage by Use Case:")
    by_uc = Counter(e["use_case"] for e in all_entries)
    print(f"   {'Use Case':<10s} {'Count':>6s} {'%':>7s}")
    print(f"   {'-'*10} {'-'*6} {'-'*7}")
    for uc, count in sorted(by_uc.items()):
        pct = count / len(all_entries) * 100
        print(f"   {uc:<10s} {count:>6d} {pct:>6.1f}%")

    # 2. By Subcategory
    print("\n2. Coverage by Subcategory:")
    by_sub = Counter(e["subcategory"] for e in all_entries)
    print(f"   {'Subcategory':<40s} {'Count':>6s} {'%':>7s}")
    print(f"   {'-'*40} {'-'*6} {'-'*7}")
    for sub, count in sorted(by_sub.items(), key=lambda x: -x[1]):
        pct = count / len(all_entries) * 100
        print(f"   {sub:<40s} {count:>6d} {pct:>6.1f}%")

    # 3. By Landmark
    print("\n3. Coverage by Landmark:")
    landmark_counts = Counter()
    for e in all_entries:
        cmd = e["expected_output"].get("command")
        if cmd and "parameters" in cmd:
            for lm in cmd["parameters"].get("landmarks_to_visit", []):
                landmark_counts[lm] += 1
    # Filter out sentinel value
    landmark_counts.pop("ALL_LANDMARKS", None)
    if landmark_counts:
        print(f"   {'Landmark':<20s} {'Count':>6s}")
        print(f"   {'-'*20} {'-'*6}")
        for lm in ALL_LANDMARKS:
            print(f"   {lm:<20s} {landmark_counts.get(lm, 0):>6d}")
        counts = list(landmark_counts.values())
        if counts:
            balance = min(counts) / max(counts) * 100
            print(f"   Balance: {balance:.0f}% (min={min(counts)}, max={max(counts)})")

    # 4. Category Balance
    print("\n4. Category Balance:")
    by_dataset = Counter()
    for e in all_entries:
        ds = e.get("_dataset_override") or e.get("_dataset", "unknown")
        by_dataset[ds] += 1
    print(f"   {'Category':<20s} {'Count':>6s} {'%':>7s}")
    print(f"   {'-'*20} {'-'*6} {'-'*7}")
    for cat in ["explicit", "implicit", "natural_language", "invalids"]:
        count = by_dataset.get(cat, 0)
        pct = count / len(all_entries) * 100
        print(f"   {cat:<20s} {count:>6d} {pct:>6.1f}%")

    # 5. Bad Grammar
    bad_grammar_keywords = [
        "plz", "pls", "plese", "tak ", "too ", "wanna", "u ",
        "arond", "toor", "stpo", "cancle", "bak ", "stopp",
        "somwhere", "ther", "dont", "wats", "helo", "thx",
        "goodby", "wat ", "noting", "somone", "everthing",
    ]
    bad_count = sum(
        1 for e in all_entries
        if any(kw in e.get("input", {}).get("user_message", "").lower()
               for kw in bad_grammar_keywords)
    )
    print(f"\n5. Bad Grammar Entries: {bad_count} ({bad_count/len(all_entries)*100:.1f}%)")

    # 6. Non-English
    non_english = sum(1 for e in all_entries if e.get("subcategory") == "non_english")
    print(f"6. Non-English Entries: {non_english} ({non_english/len(all_entries)*100:.1f}%)")

    print()


# ============================================================
# MAIN
# ============================================================

def main():
    random.seed(SEED)

    print("Generating synthetic datasets using Strategy pattern...\n")
    print(f"Strategies registered: {len(STRATEGY_REGISTRY)}")
    print()

    # Collect all entries, tagged with target dataset
    datasets = {name: [] for name in DATASET_FILE_KEYS}
    all_entries = []

    for strategy_cls in STRATEGY_REGISTRY:
        strategy = strategy_cls(landmarks=LANDMARKS, all_landmarks=ALL_LANDMARKS)
        entries = strategy.generate()

        for e in entries:
            # Route to correct dataset (allow per-entry override)
            target = e.pop("_dataset_override", None) or strategy.dataset
            e["_dataset"] = target  # keep for coverage report
            datasets[target].append(e)
            all_entries.append(e)

        print(f"  {strategy.use_case:6s} {strategy_cls.__name__:45s} → {len(entries):4d} entries")

    print()

    # Write JSONL files
    paths_cfg = CONFIG["paths"]
    for ds_name, ds_entries in datasets.items():
        path = DATASET_DIR / paths_cfg[DATASET_FILE_KEYS[ds_name]]
        write_jsonl(path, ds_entries)

    total = len(all_entries)
    print(f"\nTotal: {total} entries")

    # Stats
    stats = {
        "total": total,
        **{name: len(entries) for name, entries in datasets.items()},
    }
    stats_path = DATASET_DIR / paths_cfg.get("dataset_stats", "dataset.stats.json")
    with open(stats_path, "w") as f:
        json.dump(stats, f, indent=2)

    # Coverage report
    print_coverage_report(all_entries)


if __name__ == "__main__":
    main()
