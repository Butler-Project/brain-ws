"""
Flywheel benchmark for a distilled model exposed through Ollama /api/chat.

This benchmark replays the synthetic prompt datasets, measures latency, and
compares the model response against the expected JSON protocol.
"""

import argparse
import json
from collections import Counter, defaultdict

from common import (
    CATEGORY_KEYS,
    MODEL_NAME,
    OLLAMA_URL,
    TIMEOUT_SEC,
    call_ollama_streaming,
    ensure_output_dir,
    expected_landmarks,
    json_dump,
    jsonl_dump,
    load_prompt_entries,
    normalize_landmarks,
    percentile,
    read_container_memory_mb,
    safe_rate,
    slugify,
    text_dump,
    tqdm,
    validate_response,
)

TARGETS = {
    "avg_ttft_ms": {"target": 1000.0, "direction": "max"},
    "avg_total_latency_ms": {"target": 4000.0, "direction": "max"},
    "avg_tps": {"target": 10.0, "direction": "min"},
    "exact_match_rate": {"target": 90.0, "direction": "min"},
    "json_valid_rate": {"target": 100.0, "direction": "min"},
    "landmark_accuracy": {"target": 95.0, "direction": "min"},
    "rejection_accuracy": {"target": 95.0, "direction": "min"},
}


def _bool_rate_summary(records, key):
    applicable = [record["checks"][key] for record in records if record["checks"][key] is not None]
    passed = sum(1 for value in applicable if value)
    return {
        "passed": passed,
        "total": len(applicable),
        "rate": safe_rate(passed, len(applicable)),
    }


def _metric_pass(metric_name, value):
    if value is None or metric_name not in TARGETS:
        return None
    rule = TARGETS[metric_name]
    if rule["direction"] == "min":
        return value >= rule["target"]
    return value <= rule["target"]


def _category_summary(records):
    grouped = defaultdict(list)
    for record in records:
        grouped[record["category"]].append(record)

    summary = {}
    for category, cat_records in grouped.items():
        summary[category] = {
            "total": len(cat_records),
            "exact_match_rate": _bool_rate_summary(cat_records, "exact_match")["rate"],
            "json_valid_rate": _bool_rate_summary(cat_records, "json_valid")["rate"],
            "avg_total_latency_ms": _mean(
                [record["metrics"]["wall_time_ms"] for record in cat_records if record["metrics"]["wall_time_ms"] is not None]
            ),
            "avg_tps": _mean(
                [record["metrics"]["tps"] for record in cat_records if record["metrics"]["tps"] is not None]
            ),
        }
    return summary


def _mean(values):
    if not values:
        return None
    return sum(values) / len(values)


def _build_markdown_report(summary, category_summary, issue_counter, args):
    lines = [
        "# Flywheel Benchmark Report",
        "",
        f"- Model: `{args.model}`",
        f"- Ollama URL: `{args.ollama_url}`",
        f"- Categories: `{', '.join(args.category or CATEGORY_KEYS.keys())}`",
        f"- Total examples: `{summary['total_examples']}`",
        "",
        "## Overall Metrics",
        "",
        "| Metric | Value | Target | Status |",
        "|---|---:|---:|---|",
    ]

    rows = [
        ("Exact match rate", summary["exact_match_rate"], ">= 90.0%", _metric_pass("exact_match_rate", summary["exact_match_rate"])),
        ("JSON valid rate", summary["json_valid_rate"], "== 100.0%", _metric_pass("json_valid_rate", summary["json_valid_rate"])),
        ("Command accuracy", summary["command_accuracy"], "-", None),
        ("Landmark accuracy", summary["landmark_accuracy"], ">= 95.0%", _metric_pass("landmark_accuracy", summary["landmark_accuracy"])),
        ("Implicit follow-up accuracy", summary["implicit_follow_up_accuracy"], "-", None),
        ("Confirmation turn accuracy", summary["confirmation_turn_accuracy"], "-", None),
        ("Rejection accuracy", summary["rejection_accuracy"], ">= 95.0%", _metric_pass("rejection_accuracy", summary["rejection_accuracy"])),
        ("Average TTFT (ms)", summary["avg_ttft_ms"], "<= 1000", _metric_pass("avg_ttft_ms", summary["avg_ttft_ms"])),
        ("P95 TTFT (ms)", summary["p95_ttft_ms"], "-", None),
        ("Average total latency (ms)", summary["avg_total_latency_ms"], "<= 4000", _metric_pass("avg_total_latency_ms", summary["avg_total_latency_ms"])),
        ("P95 total latency (ms)", summary["p95_total_latency_ms"], "-", None),
        ("Average TPS", summary["avg_tps"], ">= 10", _metric_pass("avg_tps", summary["avg_tps"])),
        ("Average RAM (MB)", summary["avg_ram_mb"], "-", None),
    ]

    for label, value, target, passed in rows:
        status = "PASS" if passed is True else "FAIL" if passed is False else "INFO"
        pretty = "-" if value is None else f"{value:.2f}"
        lines.append(f"| {label} | {pretty} | {target} | {status} |")

    lines.extend([
        "",
        "## By Category",
        "",
        "| Category | Total | Exact Match % | JSON Valid % | Avg Latency ms | Avg TPS |",
        "|---|---:|---:|---:|---:|---:|",
    ])

    for category, stats in sorted(category_summary.items()):
        lines.append(
            "| "
            f"{category} | {stats['total']} | "
            f"{_fmt(stats['exact_match_rate'])} | {_fmt(stats['json_valid_rate'])} | "
            f"{_fmt(stats['avg_total_latency_ms'])} | {_fmt(stats['avg_tps'])} |"
        )

    lines.extend([
        "",
        "## Top Validation Issues",
        "",
        "| Issue | Count |",
        "|---|---:|",
    ])

    if issue_counter:
        for issue, count in issue_counter.most_common(15):
            lines.append(f"| {issue} | {count} |")
    else:
        lines.append("| No validation issues | 0 |")

    lines.append("")
    return "\n".join(lines)


def _fmt(value):
    if value is None:
        return "-"
    return f"{value:.2f}"


def run_benchmark(args):
    entries = load_prompt_entries(
        categories=args.category,
        max_examples=args.max_examples,
        seed=args.seed,
    )

    output_dir = ensure_output_dir(
        run_name=args.run_name,
        output_dir=args.output_dir,
        prefix="flywheel",
        model_name=args.model,
    )

    print("=" * 60)
    print("  FLYWHEEL BENCHMARK")
    print("=" * 60)
    print(f"  Model:      {args.model}")
    print(f"  Ollama URL: {args.ollama_url}")
    print(f"  Output dir: {output_dir}")
    print(f"  Examples:   {len(entries)}")
    print("=" * 60)

    records = []
    issue_counter = Counter()
    ttft_values = []
    total_latency_values = []
    tps_values = []
    ram_values = []

    pbar = tqdm(entries, desc="  flywheel", unit="prompt", leave=True)
    for entry in pbar:
        prompt_json = json.dumps(entry["input"], ensure_ascii=False)
        response = call_ollama_streaming(
            prompt_json,
            ollama_url=args.ollama_url,
            model=args.model,
            timeout=args.timeout,
        )

        if response["error"]:
            validation = {
                "valid": False,
                "is_json": False,
                "result_type": None,
                "command_name": None,
                "landmarks": [],
                "follow_up": None,
                "issues": [response["error"]],
            }
        else:
            validation = validate_response(response["content"], entry["expected_output"])

        expected_cmd = entry["expected_output"].get("command")
        expected_follow_up = entry["expected_output"].get("follow_up")
        expected_type = entry["expected_output"].get("result_type")

        command_correct = None
        if expected_cmd is not None:
            command_correct = validation["command_name"] == expected_cmd["name"]

        landmark_correct = None
        expected_lms = expected_landmarks(entry)
        if expected_lms is not None:
            landmark_correct = normalize_landmarks(validation["landmarks"]) == normalize_landmarks(expected_lms)

        implicit_follow_up_correct = None
        if expected_follow_up is not None:
            actual_follow_up = validation["follow_up"]
            implicit_follow_up_correct = (
                isinstance(actual_follow_up, dict)
                and actual_follow_up.get("required") is True
                and actual_follow_up.get("type") == expected_follow_up.get("type")
                and actual_follow_up.get("expires_in_sec") == expected_follow_up.get("expires_in_sec")
            )

        confirmation_turn_correct = None
        if expected_type == "interpreted_implicit_command_confirmation":
            confirmation_turn_correct = validation["valid"]

        rejection_correct = None
        if expected_type == "rejected":
            rejection_correct = (
                validation["result_type"] == "rejected"
                and validation["command_name"] is None
            )

        tps = None
        duration_ms = response["total_duration_ms"] or response["wall_time_ms"]
        if response["completion_tokens"] and duration_ms:
            tps = response["completion_tokens"] / (duration_ms / 1000.0)

        ram_mb = read_container_memory_mb(args.docker_container)

        record = {
            "category": entry.get("_category"),
            "use_case": entry.get("use_case"),
            "subcategory": entry.get("subcategory"),
            "input": entry["input"],
            "expected_output": entry["expected_output"],
            "response": response["content"],
            "validation": validation,
            "checks": {
                "exact_match": validation["valid"],
                "json_valid": validation["is_json"],
                "result_type_correct": validation["result_type"] == expected_type,
                "command_correct": command_correct,
                "landmark_correct": landmark_correct,
                "implicit_follow_up_correct": implicit_follow_up_correct,
                "confirmation_turn_correct": confirmation_turn_correct,
                "rejection_correct": rejection_correct,
            },
            "metrics": {
                "ttft_ms": response["ttft_ms"],
                "wall_time_ms": response["wall_time_ms"],
                "total_duration_ms": response["total_duration_ms"],
                "prompt_tokens": response["prompt_tokens"],
                "completion_tokens": response["completion_tokens"],
                "tps": tps,
                "ram_mb": ram_mb,
            },
        }
        records.append(record)

        if validation["issues"]:
            issue_counter.update(validation["issues"])
            tqdm.write(
                f"  INVALID [{entry.get('use_case')}] [{entry.get('subcategory')}] "
                f"\"{entry['input'].get('user_message', '')[:50]}\" → {validation['issues']}"
            )

        if response["ttft_ms"] is not None:
            ttft_values.append(response["ttft_ms"])
        if response["wall_time_ms"] is not None:
            total_latency_values.append(response["wall_time_ms"])
        if tps is not None:
            tps_values.append(tps)
        if ram_mb is not None:
            ram_values.append(ram_mb)

        exact = _bool_rate_summary(records, "exact_match")["rate"]
        pbar.set_postfix_str(
            f"exact={_fmt(exact)}% avg={_fmt(_mean(total_latency_values))}ms"
        )

    pbar.close()

    summary = {
        "model": args.model,
        "ollama_url": args.ollama_url,
        "total_examples": len(records),
        "exact_match_rate": _bool_rate_summary(records, "exact_match")["rate"],
        "json_valid_rate": _bool_rate_summary(records, "json_valid")["rate"],
        "command_accuracy": _bool_rate_summary(records, "command_correct")["rate"],
        "landmark_accuracy": _bool_rate_summary(records, "landmark_correct")["rate"],
        "implicit_follow_up_accuracy": _bool_rate_summary(records, "implicit_follow_up_correct")["rate"],
        "confirmation_turn_accuracy": _bool_rate_summary(records, "confirmation_turn_correct")["rate"],
        "rejection_accuracy": _bool_rate_summary(records, "rejection_correct")["rate"],
        "avg_ttft_ms": _mean(ttft_values),
        "p50_ttft_ms": percentile(ttft_values, 50),
        "p95_ttft_ms": percentile(ttft_values, 95),
        "avg_total_latency_ms": _mean(total_latency_values),
        "p50_total_latency_ms": percentile(total_latency_values, 50),
        "p95_total_latency_ms": percentile(total_latency_values, 95),
        "avg_tps": _mean(tps_values),
        "p50_tps": percentile(tps_values, 50),
        "p95_tps": percentile(tps_values, 95),
        "avg_ram_mb": _mean(ram_values),
        "p95_ram_mb": percentile(ram_values, 95),
        "docker_container": args.docker_container,
        "issue_counts": dict(issue_counter),
    }
    category_summary = _category_summary(records)

    jsonl_dump(output_dir / "benchmark_results.jsonl", records)
    json_dump(output_dir / "benchmark_results.json", summary)
    text_dump(
        output_dir / "benchmark_report.md",
        _build_markdown_report(summary, category_summary, issue_counter, args),
    )

    print()
    print("=" * 60)
    print("  FLYWHEEL COMPLETE")
    print("=" * 60)
    print(f"  Results: {output_dir / 'benchmark_results.json'}")
    print(f"  Report:  {output_dir / 'benchmark_report.md'}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Run Flywheel benchmark on a distilled model via Ollama")
    parser.add_argument("--model", default="distilled-1b-robot-router", help=f"Ollama model name (default: distilled-1b-robot-router, teacher default is {MODEL_NAME})")
    parser.add_argument("--ollama-url", default=OLLAMA_URL, help=f"Ollama API URL (default: {OLLAMA_URL})")
    parser.add_argument("--timeout", type=int, default=TIMEOUT_SEC, help=f"Request timeout in seconds (default: {TIMEOUT_SEC})")
    parser.add_argument("--category", "-c", action="append", choices=list(CATEGORY_KEYS.keys()), help="Benchmark only selected dataset categories (repeatable)")
    parser.add_argument("--max-examples", "-n", type=int, help="Max total examples to benchmark (proportional across categories)")
    parser.add_argument("--seed", type=int, default=42, help="Sampling seed for --max-examples")
    parser.add_argument("--run-name", help="Optional benchmark run name")
    parser.add_argument("--output-dir", help="Optional output directory override")
    parser.add_argument("--docker-container", help="Optional Docker container name for memory sampling")
    args = parser.parse_args()
    run_benchmark(args)


if __name__ == "__main__":
    main()
