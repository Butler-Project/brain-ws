"""
Step 1: Prepare training data for Knowledge Distillation.

Reads the teacher's *_results.jsonl files, filters VALID entries only,
and converts them to the chat format expected by Unsloth SFTTrainer.

Output: dataset/training/train.jsonl + eval.jsonl (90/10 split)

Usage:
    python prepare_training_data.py
"""

import json
import random
from collections import Counter

from utils import (
    DATASET_DIR,
    EVAL_FILE,
    RESULT_FILES,
    SEED,
    TRAIN_FILE,
    TRAINING_DIR,
    extract_system_prompt,
)

EVAL_SPLIT = 0.1


def main():
    random.seed(SEED)

    system_prompt = extract_system_prompt()

    valid_entries = []
    stats = {"total": 0, "valid": 0, "invalid": 0, "no_response": 0}

    for result_file in RESULT_FILES:
        if not result_file.exists():
            print(f"  WARNING: {result_file} not found, skipping")
            continue

        category = result_file.parent.name
        cat_valid = 0
        cat_total = 0

        with open(result_file) as f:
            for line in f:
                entry = json.loads(line)
                cat_total += 1
                stats["total"] += 1

                if not entry.get("response"):
                    stats["no_response"] += 1
                    continue

                if not entry["validation"]["valid"]:
                    stats["invalid"] += 1
                    continue

                stats["valid"] += 1
                cat_valid += 1

                input_json = json.dumps(entry["input"], ensure_ascii=False)
                response_json = entry["response"]

                try:
                    parsed = json.loads(response_json)
                    response_json = json.dumps(parsed, ensure_ascii=False)
                except json.JSONDecodeError:
                    continue

                valid_entries.append({
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": input_json},
                        {"role": "assistant", "content": response_json},
                    ],
                    "_use_case": entry.get("use_case"),
                    "_subcategory": entry.get("subcategory"),
                    "_category": category,
                })

        print(f"  {category}: {cat_valid}/{cat_total} valid")

    print(f"\nTotal: {stats['valid']} valid / {stats['total']} total "
          f"({stats['valid']/stats['total']*100:.1f}%)")
    print(f"  Skipped: {stats['invalid']} invalid, {stats['no_response']} no response")

    random.shuffle(valid_entries)
    split_idx = int(len(valid_entries) * (1 - EVAL_SPLIT))
    train_entries = valid_entries[:split_idx]
    eval_entries = valid_entries[split_idx:]

    TRAINING_DIR.mkdir(parents=True, exist_ok=True)

    for path, entries in [(TRAIN_FILE, train_entries), (EVAL_FILE, eval_entries)]:
        with open(path, "w") as f:
            for e in entries:
                clean = {"messages": e["messages"]}
                f.write(json.dumps(clean, ensure_ascii=False) + "\n")
        print(f"  {path.name}: {len(entries)} examples")

    by_uc = Counter(e["_use_case"] for e in valid_entries)
    print(f"\nBy Use Case:")
    for uc, count in sorted(by_uc.items()):
        print(f"  {uc}: {count}")


if __name__ == "__main__":
    main()
