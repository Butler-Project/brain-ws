"""
Shared helpers for distilled-model benchmark scripts.
"""

import json
import random
import re
import subprocess
import sys
import time
from pathlib import Path

import requests

try:
    from tqdm import tqdm
except ImportError:
    class tqdm:
        def __init__(self, iterable=None, total=None, **_kw):
            self._iterable = iterable if iterable is not None else []
            self.total = total
        def __iter__(self):
            return iter(self._iterable)
        def update(self, _n=1):
            pass
        def set_postfix_str(self, _t):
            pass
        def close(self):
            pass
        @staticmethod
        def write(msg):
            print(msg)

SCRIPT_DIR = Path(__file__).resolve().parent
DATASET_CREATION_DIR = SCRIPT_DIR.parent / "dataset_creation"

if str(DATASET_CREATION_DIR) not in sys.path:
    sys.path.insert(0, str(DATASET_CREATION_DIR))

from teacher_dataset_evaluator import (  # noqa: E402
    BENCHMARK_DIR,
    CATEGORY_KEYS,
    MODEL_NAME,
    OLLAMA_URL,
    TIMEOUT_SEC,
    get_dataset_path,
    load_dataset,
    validate_response,
)


def slugify(text):
    """Convert an arbitrary string into a filesystem-friendly slug."""
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "_", text.strip())
    return slug.strip("._-") or "run"


def default_run_name(prefix, model_name):
    """Return a benchmark run name with timestamp and model name."""
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{slugify(model_name)}_{timestamp}"


def ensure_output_dir(run_name=None, output_dir=None, prefix="benchmark", model_name="model"):
    """Create and return the benchmark output directory for a run."""
    if output_dir:
        path = Path(output_dir)
    else:
        run_name = run_name or default_run_name(prefix, model_name)
        path = BENCHMARK_DIR / run_name
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_prompt_entries(categories=None, max_examples=None, seed=42):
    """Load prompt dataset entries from one or more categories."""
    selected = categories or list(CATEGORY_KEYS.keys())
    datasets = {}
    total_entries = 0

    for cat_name, cat_key in CATEGORY_KEYS.items():
        if cat_name not in selected:
            continue
        path = get_dataset_path(cat_key)
        entries = load_dataset(path)
        if not entries:
            continue
        for entry in entries:
            entry["_category"] = cat_name
        datasets[cat_name] = entries
        total_entries += len(entries)

    if not datasets:
        raise FileNotFoundError("No prompt datasets found. Run sintetic_dataset_generator.py first.")

    if max_examples and max_examples < total_entries:
        rng = random.Random(seed)
        ratio = max_examples / total_entries
        for cat_name, entries in datasets.items():
            keep = max(1, int(len(entries) * ratio))
            shuffled = list(entries)
            rng.shuffle(shuffled)
            datasets[cat_name] = shuffled[:keep]

    flattened = []
    for cat_name in selected:
        flattened.extend(datasets.get(cat_name, []))
    return flattened


def call_ollama_streaming(prompt_json, ollama_url=OLLAMA_URL, model=MODEL_NAME, timeout=TIMEOUT_SEC):
    """Call Ollama in streaming mode and measure TTFT and total latency."""
    payload = {
        "model": model,
        "stream": True,
        "messages": [{"role": "user", "content": prompt_json}],
    }

    started_at = time.perf_counter()
    first_token_ms = None
    content_parts = []
    final_chunk = {}

    try:
        with requests.post(ollama_url, json=payload, timeout=timeout, stream=True) as response:
            response.raise_for_status()
            for raw_line in response.iter_lines(decode_unicode=True):
                if not raw_line:
                    continue
                chunk = json.loads(raw_line)
                piece = chunk.get("message", {}).get("content", "")
                if piece:
                    if first_token_ms is None:
                        first_token_ms = (time.perf_counter() - started_at) * 1000
                    content_parts.append(piece)
                if chunk.get("done"):
                    final_chunk = chunk

        wall_time_ms = (time.perf_counter() - started_at) * 1000
        return {
            "content": "".join(content_parts),
            "ttft_ms": first_token_ms,
            "wall_time_ms": wall_time_ms,
            "total_duration_ms": final_chunk.get("total_duration", 0) / 1e6,
            "prompt_tokens": final_chunk.get("prompt_eval_count", 0),
            "completion_tokens": final_chunk.get("eval_count", 0),
            "error": None,
        }
    except (requests.exceptions.RequestException, json.JSONDecodeError) as exc:
        wall_time_ms = (time.perf_counter() - started_at) * 1000
        return {
            "content": None,
            "ttft_ms": first_token_ms,
            "wall_time_ms": wall_time_ms,
            "total_duration_ms": None,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "error": str(exc),
        }


def percentile(values, pct):
    """Compute a percentile in the range [0, 100]."""
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * (pct / 100.0)
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    weight = rank - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def safe_rate(numerator, denominator):
    """Return a percentage or None when the denominator is zero."""
    if denominator == 0:
        return None
    return (numerator / denominator) * 100.0


def json_dump(path, payload):
    """Write a JSON payload with indentation."""
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def jsonl_dump(path, records):
    """Write a sequence of records to JSONL."""
    with open(path, "w") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def text_dump(path, text):
    """Write plain text to disk."""
    path.write_text(text)


def normalize_landmarks(values):
    """Normalize landmark names for set comparison."""
    return {value.lower().replace(" ", "_") for value in values or []}


def expected_landmarks(entry):
    """Return the expected landmarks list for an entry, or None."""
    command = entry.get("expected_output", {}).get("command")
    if not command:
        return None
    return command.get("parameters", {}).get("landmarks_to_visit")


def read_container_memory_mb(container_name):
    """Read container memory usage in MB from docker stats, or None on failure."""
    if not container_name:
        return None

    try:
        result = subprocess.run(
            [
                "docker",
                "stats",
                "--no-stream",
                "--format",
                "{{.MemUsage}}",
                container_name,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

    usage = result.stdout.strip()
    if not usage:
        return None
    current = usage.split("/", 1)[0].strip()
    return _memory_to_mb(current)


def _memory_to_mb(text):
    """Convert a docker memory string like 512.0MiB to MB."""
    match = re.match(r"([0-9.]+)\s*([KMG]i?B|B)", text)
    if not match:
        return None

    value = float(match.group(1))
    unit = match.group(2)
    factors = {
        "B": 1 / (1024 * 1024),
        "KiB": 1 / 1024,
        "KB": 1 / 1000,
        "MiB": 1.0,
        "MB": 1.0,
        "GiB": 1024.0,
        "GB": 1000.0,
    }
    return value * factors.get(unit, 1.0)

