"""Repeatable benchmarks for exact 50/100/250/500 predicate-rule KBs."""

import csv
import os
from statistics import mean, median
from time import perf_counter

from generate_kb import generate_kb
from metrics import normalize_result
from reasoning_engine import backward_chain, forward_chain
from to_predicates import to_predicates

ALGORITHMS = {
    "forward": forward_chain,
    "backward": backward_chain,
}
DEFAULT_SIZES = (50, 100, 250, 500)


def _choose_one_or_branch(expr):
    """Remove OR branches so each course expands to exactly one eligible rule.

    A course emits one coreqs_satisfied rule and, when its prerequisite is in
    one-clause form, one eligible rule. The two generic prereq_satisfied rules
    make the total exactly 2 * course_count + 2. Functional tests separately
    exercise OR semantics.
    """
    if isinstance(expr, dict):
        if "or" in expr:
            return _choose_one_or_branch(expr["or"][0])
        if "and" in expr:
            return {"and": [_choose_one_or_branch(child) for child in expr["and"]]}
    return expr


def generate_exact_rule_kb(rule_count, seed=0):
    """Generate a deterministic synthetic KB with exactly `rule_count` rules.

    With this project's predicate expansion, the requested counts all satisfy
    rule_count = 2 * course_count + 2. OR clauses are reduced to one branch in
    performance-only fixtures to preserve exact counts; functional tests cover
    the full AND/OR semantics. Both algorithms receive the identical KB/query.
    """
    if not isinstance(rule_count, int) or rule_count < 4 or (rule_count - 2) % 2:
        raise ValueError("rule_count must be an even integer >= 4 (50, 100, 250 and 500 are supported)")
    course_count = (rule_count - 2) // 2
    kb = generate_kb(course_count, seed=seed)
    for course in kb["courses"].values():
        course["prerequisite"] = _choose_one_or_branch(course.get("prerequisite"))
    # Keep the original generator's `requested_rule_count` metadata semantics
    # (n courses) intact, and record the expanded logic-rule count separately.
    kb["benchmark_course_count"] = course_count
    kb["benchmark_rule_count"] = rule_count
    actual = len(to_predicates(kb)["rules"])
    if actual != rule_count:
        raise AssertionError(f"Expected {rule_count} predicate rules, generated {actual}")
    return kb


def run_benchmarks(sizes=DEFAULT_SIZES, seed=0, repeats=3, out_dir="results"):
    """Run selected sizes and preserve existing rows for other benchmark sizes.

    This allows longer runs to be split across commands, e.g. 50/100/250 first
    and 500 later, without losing earlier CSV measurements. Re-running a size
    replaces its old rows so the output does not silently duplicate a run.
    """
    if repeats < 1:
        raise ValueError("repeats must be at least 1")
    sizes = tuple(int(size) for size in sizes)
    os.makedirs(out_dir, exist_ok=True)
    raw_path = os.path.join(out_dir, "benchmark_results.csv")
    summary_path = os.path.join(out_dir, "benchmark_summary.csv")
    raw_fields = [
        "rule_count", "course_count", "seed", "student_id", "course_id", "algorithm",
        "run", "elapsed_ms", "eligible", "missing_prerequisites", "inference_steps",
        "rules_examined", "derived_facts",
    ]
    summary_fields = [
        "rule_count", "course_count", "seed", "student_id", "course_id", "algorithm",
        "repeats", "eligible", "runtime_ms_median", "runtime_ms_mean", "runtime_ms_min",
        "runtime_ms_max", "inference_steps", "rules_examined", "derived_facts",
    ]

    existing_rows = []
    if os.path.exists(raw_path):
        with open(raw_path, newline="", encoding="utf-8") as old_file:
            existing_rows = list(csv.DictReader(old_file))
    selected_sizes = set(sizes)
    preserved_rows = [row for row in existing_rows if int(row["rule_count"]) not in selected_sizes]

    with open(raw_path, "w", newline="", encoding="utf-8") as raw_file:
        writer = csv.DictWriter(raw_file, fieldnames=raw_fields)
        writer.writeheader()
        writer.writerows(preserved_rows)
        raw_file.flush()
        for size in sizes:
            kb = generate_exact_rule_kb(size, seed=seed)
            student_id = "student0"
            course_id = f"C{kb['benchmark_course_count'] - 1:03d}"
            actual_count = len(to_predicates(kb)["rules"])
            if actual_count != size:
                raise AssertionError(f"Benchmark KB size mismatch: expected {size}, found {actual_count}")
            for algorithm, engine_fn in ALGORITHMS.items():
                for run_index in range(1, repeats + 1):
                    start = perf_counter()
                    raw_result = engine_fn(kb, student_id, course_id)
                    elapsed = (perf_counter() - start) * 1000.0
                    result = normalize_result(raw_result, algorithm, student_id, course_id)
                    writer.writerow({
                        "rule_count": size,
                        "course_count": kb["benchmark_course_count"],
                        "seed": seed,
                        "student_id": student_id,
                        "course_id": course_id,
                        "algorithm": algorithm,
                        "run": run_index,
                        "elapsed_ms": f"{elapsed:.6f}",
                        "eligible": result["eligible"],
                        "missing_prerequisites": ";".join(result["missing_prerequisites"]),
                        "inference_steps": result["inference_steps"],
                        "rules_examined": result["rules_examined"],
                        "derived_facts": "N/A" if result["derived_facts"] is None else result["derived_facts"],
                    })
                    raw_file.flush()
            print(f"Benchmarked {size} predicate rules ({kb['benchmark_course_count']} courses).")

    # Build the summary from the full raw CSV (including preserved sizes).
    with open(raw_path, newline="", encoding="utf-8") as raw_file:
        all_rows = list(csv.DictReader(raw_file))
    grouped = {}
    for row in all_rows:
        grouped.setdefault((int(row["rule_count"]), row["algorithm"]), []).append(row)

    summary_rows = []
    for (size, algorithm), group in sorted(grouped.items()):
        timings = [float(row["elapsed_ms"]) for row in group]
        last = group[-1]
        summary_rows.append({
            "rule_count": size,
            "course_count": last["course_count"],
            "seed": last["seed"],
            "student_id": last["student_id"],
            "course_id": last["course_id"],
            "algorithm": algorithm,
            "repeats": len(group),
            "eligible": last["eligible"],
            "runtime_ms_median": f"{median(timings):.6f}",
            "runtime_ms_mean": f"{mean(timings):.6f}",
            "runtime_ms_min": f"{min(timings):.6f}",
            "runtime_ms_max": f"{max(timings):.6f}",
            "inference_steps": last["inference_steps"],
            "rules_examined": last["rules_examined"],
            "derived_facts": last["derived_facts"],
        })
    with open(summary_path, "w", newline="", encoding="utf-8") as summary_file:
        writer = csv.DictWriter(summary_file, fieldnames=summary_fields)
        writer.writeheader()
        writer.writerows(summary_rows)
    return {"raw_csv": raw_path, "summary_csv": summary_path, "rows": summary_rows}
