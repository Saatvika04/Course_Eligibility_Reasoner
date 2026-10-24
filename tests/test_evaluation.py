"""Regression tests for Mohammed's evaluation, metrics, benchmark and CLI layer."""

import csv
import os

from benchmark import generate_exact_rule_kb, run_benchmarks
from evaluate import run_evaluation
from evaluation_cases import build_evaluation_kb, get_labelled_cases
from kb_loader import validate_kb
from metrics import measure_call, normalize_result
from plot_results import generate_plots
from reasoning_engine import backward_chain, forward_chain
from to_predicates import to_predicates


def test_labelled_cases_match_both_algorithms():
    kb = build_evaluation_kb()
    assert validate_kb(kb) == []
    cases = get_labelled_cases()
    assert len(cases) >= 12
    for case in cases:
        for engine in (forward_chain, backward_chain):
            result = engine(kb, case["student"], case["course"])
            assert result["eligible"] is case["expected_eligible"], (case, result)


def test_benchmark_kbs_have_exact_predicate_rule_counts():
    for requested_count in (50, 100, 250, 500):
        kb = generate_exact_rule_kb(requested_count, seed=23)
        assert validate_kb(kb) == []
        assert len(to_predicates(kb)["rules"]) == requested_count
        # Reproducible generator: same size + seed = same KB.
        assert kb == generate_exact_rule_kb(requested_count, seed=23)


def test_normalize_result_supplies_shared_fields():
    result = normalize_result({"eligible": False}, "fake", "student", "course")
    assert result["student_id"] == "student"
    assert result["course_id"] == "course"
    assert result["missing_prerequisites"] == []
    assert result["missing_corequisites"] == []
    assert result["trace"] == []
    assert result["derived_facts"] is None


def test_measure_call_reports_repeat_timings_and_stable_verdict():
    kb = build_evaluation_kb()
    measured = measure_call(backward_chain, kb, "case_student", "INTRO", repeats=2, algorithm="backward")
    assert measured["repeats"] == 2
    assert len(measured["runtime_ms_runs"]) == 2
    assert measured["runtime_ms_median"] >= 0
    assert measured["result"]["eligible"] is True


def test_evaluation_writes_case_and_summary_csv(tmp_path):
    output = run_evaluation(repeats=1, out_dir=str(tmp_path))
    assert output["results_csv"]
    assert output["summary_csv"]
    with open(output["results_csv"], newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == len(get_labelled_cases()) * 2
    assert all(row["passed"] == "True" for row in rows)
    with open(output["summary_csv"], newline="", encoding="utf-8") as handle:
        summary = list(csv.DictReader(handle))
    assert {row["algorithm"] for row in summary} == {"forward", "backward"}
    assert all(row["accuracy_percent"] == "100.00" for row in summary)


def test_backward_engine_emits_cycle_trace_for_recursive_predicate_rules():
    from reasoning_engine import backward_prove
    from to_predicates import Var

    x = Var("X")
    rules = [
        {"head": ("a", x), "body": [("b", x)]},
        {"head": ("b", x), "body": [("a", x)]},
    ]
    proof = backward_prove([], rules, ("a", "student"))
    assert proof["proved"] is False
    assert any(line.startswith("CYCLE") for line in proof["trace"])
    assert proof["inference_steps"] < 10  # the cycle guard prevents runaway recursion


def test_benchmark_and_plots_write_regenerable_files(tmp_path):
    outputs = run_benchmarks(sizes=[50], seed=0, repeats=1, out_dir=str(tmp_path))
    assert os.path.exists(outputs["raw_csv"])
    assert os.path.exists(outputs["summary_csv"])
    plots = generate_plots(outputs["raw_csv"], str(tmp_path))
    assert len(plots) == 3
    assert all(os.path.exists(path) for path in plots)


def test_cli_displays_missing_corequisite(capsys):
    from cli import main

    code = main([
        "case_student", "COREQ_MISSING_TARGET",
        "--kb", "data/evaluation_knowledge_base.json",
        "--algorithm", "backward", "--no-trace",
    ])
    output = capsys.readouterr().out
    assert code == 0
    assert "NOT ELIGIBLE" in output
    assert "Missing corequisites (not currently taken): COREQ_M" in output


def test_benchmark_chunk_runs_preserve_other_sizes(tmp_path):
    from benchmark import run_benchmarks

    run_benchmarks(sizes=[50], seed=0, repeats=1, out_dir=str(tmp_path))
    output = run_benchmarks(sizes=[100], seed=0, repeats=1, out_dir=str(tmp_path))
    with open(output["summary_csv"], newline="", encoding="utf-8") as handle:
        summary = list(csv.DictReader(handle))
    assert {int(row["rule_count"]) for row in summary} == {50, 100}
    assert all(row["repeats"] == "1" for row in summary)
