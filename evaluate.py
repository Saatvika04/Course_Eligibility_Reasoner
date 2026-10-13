"""Run labelled correctness checks and benchmark both reasoning algorithms."""

import argparse
import csv
import os

from benchmark import run_benchmarks
from evaluation_cases import build_evaluation_kb, get_labelled_cases
from metrics import measure_call
from plot_results import generate_plots
from reasoning_engine import backward_chain, forward_chain

ALGORITHMS = {
    "forward": forward_chain,
    "backward": backward_chain,
}


def run_evaluation(repeats=3, out_dir="results"):
    """Run every independent label with both engines; write CSV files."""
    if repeats < 1:
        raise ValueError("repeats must be at least 1")
    os.makedirs(out_dir, exist_ok=True)
    kb = build_evaluation_kb()
    cases = get_labelled_cases()
    result_path = os.path.join(out_dir, "evaluation_results.csv")
    summary_path = os.path.join(out_dir, "evaluation_summary.csv")
    fields = [
        "case_id", "scenario", "student_id", "course_id", "algorithm", "expected_eligible",
        "actual_eligible", "passed", "missing_prerequisites", "runtime_ms_median",
        "runtime_ms_mean", "runtime_ms_min", "runtime_ms_max", "inference_steps",
        "rules_examined", "derived_facts", "trace",
    ]
    rows = []
    with open(result_path, "w", newline="", encoding="utf-8") as result_file:
        writer = csv.DictWriter(result_file, fieldnames=fields)
        writer.writeheader()
        for case in cases:
            verdicts = {}
            for algorithm, engine_fn in ALGORITHMS.items():
                measured = measure_call(
                    engine_fn, kb, case["student"], case["course"],
                    repeats=repeats, algorithm=algorithm,
                )
                result = measured["result"]
                verdicts[algorithm] = result["eligible"]
                passed = result["eligible"] == case["expected_eligible"]
                row = {
                    "case_id": case["id"],
                    "scenario": case["scenario"],
                    "student_id": case["student"],
                    "course_id": case["course"],
                    "algorithm": algorithm,
                    "expected_eligible": case["expected_eligible"],
                    "actual_eligible": result["eligible"],
                    "passed": passed,
                    "missing_prerequisites": ";".join(result["missing_prerequisites"]),
                    "runtime_ms_median": f"{measured['runtime_ms_median']:.6f}",
                    "runtime_ms_mean": f"{measured['runtime_ms_mean']:.6f}",
                    "runtime_ms_min": f"{measured['runtime_ms_min']:.6f}",
                    "runtime_ms_max": f"{measured['runtime_ms_max']:.6f}",
                    "inference_steps": result["inference_steps"],
                    "rules_examined": result["rules_examined"],
                    "derived_facts": "N/A" if result["derived_facts"] is None else result["derived_facts"],
                    "trace": " | ".join(result["trace"]),
                }
                rows.append(row)
                writer.writerow(row)
                status = "PASS" if passed else "FAIL"
                print(f"{status} {case['id']} [{algorithm}] expected={case['expected_eligible']} actual={result['eligible']} - {case['scenario']}")
            if verdicts["forward"] != verdicts["backward"]:
                print(f"ALGORITHM MISMATCH {case['id']}: forward={verdicts['forward']} backward={verdicts['backward']}")

    summary_rows = []
    for algorithm in ALGORITHMS:
        alg_rows = [row for row in rows if row["algorithm"] == algorithm]
        # Keep summary robust to bool/string inputs.
        correct = sum(str(row["passed"]).lower() == "true" for row in alg_rows)
        summary_rows.append({
            "algorithm": algorithm,
            "labelled_cases": len(alg_rows),
            "correct_verdicts": correct,
            "incorrect_verdicts": len(alg_rows) - correct,
            "accuracy_percent": f"{(100.0 * correct / len(alg_rows)) if alg_rows else 0.0:.2f}",
            "repeats_per_case": repeats,
        })
    with open(summary_path, "w", newline="", encoding="utf-8") as summary_file:
        writer = csv.DictWriter(summary_file, fieldnames=[
            "algorithm", "labelled_cases", "correct_verdicts", "incorrect_verdicts",
            "accuracy_percent", "repeats_per_case",
        ])
        writer.writeheader()
        writer.writerows(summary_rows)
    print("\nEvaluation summary")
    for row in summary_rows:
        print(f"  {row['algorithm']}: {row['correct_verdicts']}/{row['labelled_cases']} correct ({row['accuracy_percent']}%)")
    print(f"Saved case results: {result_path}")
    print(f"Saved accuracy summary: {summary_path}")
    return {"results_csv": result_path, "summary_csv": summary_path, "rows": rows, "summary": summary_rows}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("tests", "benchmark", "all"), default="all",
                        help="run labelled tests, size benchmarks, or both (default: all)")
    parser.add_argument("--repeats", type=int, default=3, help="number of timed runs per query (default: 3)")
    parser.add_argument("--seed", type=int, default=0, help="fixed benchmark generator seed (default: 0)")
    parser.add_argument("--out-dir", default="results", help="directory for CSV files and plots")
    parser.add_argument("--sizes", type=int, nargs="+", default=[50, 100, 250, 500],
                        help="predicate-rule sizes for benchmark mode")
    args = parser.parse_args(argv)
    if args.repeats < 1:
        parser.error("--repeats must be at least 1")
    if args.mode in ("tests", "all"):
        run_evaluation(repeats=args.repeats, out_dir=args.out_dir)
    if args.mode in ("benchmark", "all"):
        outputs = run_benchmarks(sizes=args.sizes, seed=args.seed, repeats=args.repeats, out_dir=args.out_dir)
        print(f"Saved raw benchmark results: {outputs['raw_csv']}")
        print(f"Saved benchmark summary: {outputs['summary_csv']}")
        for path in generate_plots(outputs["raw_csv"], args.out_dir):
            print(f"Saved plot: {path}")


if __name__ == "__main__":
    main()
