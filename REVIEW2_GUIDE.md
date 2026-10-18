# Review 2 — Mohammed Wasif: Evaluation and Interface

This guide documents the evaluation layer added around the existing symbolic engine. It does **not** reimplement Forward or Backward Chaining.

## 1. Quick setup

Use Python 3.11 or later. Open a terminal in the repository root (the folder containing `reasoning_engine.py`).

### Windows PowerShell

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell blocks activation scripts, do not change the system policy just for this project. Run the venv Python directly instead:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -q
```

### Ubuntu / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If `venv` is not installed on Ubuntu, install the distribution package `python3-venv` first.

## 2. Run checks before the demo

Run the original project tests plus the new evaluation tests:

```bash
python -m pytest -q
```

Run the independently labelled test cases against both algorithms:

```bash
python evaluate.py --mode tests --repeats 3
```

The expected console summary is 16/16 correct for Forward Chaining and 16/16 correct for Backward Chaining. If a source-code change causes a mismatch, the program prints the case ID and expected/actual verdict, and the detailed row is saved to `results/evaluation_results.csv`.

Run the scalability benchmark with a fixed seed and three timings per algorithm/size:

```bash
python evaluate.py --mode benchmark --repeats 3 --seed 0
```

Run the whole suite (tests + benchmark + plots) in one command:

```bash
python evaluate.py --mode all --repeats 3 --seed 0
```

The full command may take longer than the labelled checks because Forward Chaining scans facts during closure computation. Use `--repeats 1` for a quick smoke test; use `--repeats 3` for your Review 2 run.

## 3. CLI demonstration

From the repository root:

```bash
python cli.py bob CS203 --algorithm both
```

This runs both algorithms against the project's original demo KB (`data/knowledge_base.json`). Output includes the verdict, missing conditions, counters and readable trace.

Use the dedicated small evaluation KB to demonstrate a valid waiver and a target-specific invalid waiver:

```bash
python cli.py case_student WAIVER_TARGET --kb data/evaluation_knowledge_base.json --algorithm both
python cli.py case_student WAIVER_OTHER_TARGET --kb data/evaluation_knowledge_base.json --algorithm both
```

Demonstrate the domain KB cycle warning and the proof engine's active-path guard:

```bash
python cli.py case_student CYCLE_A --kb data/evaluation_knowledge_base.json --algorithm both
python cycle_demo.py
```

The first command detects the structural prerequisite cycle. Under the project semantics, a prerequisite is satisfied by completion or a scoped waiver, not by recursively proving eligibility, so that course query normally fails on a missing completed prerequisite. The second command exercises the existing `backward_prove()` cycle guard on a recursive predicate-rule loop and prints the `CYCLE` trace marker. To reduce CLI output length, use `--trace-limit 20` or hide the trace with `--no-trace`.

## 4. Generated output files

After evaluation and benchmarking, `results/` contains:

- `evaluation_results.csv` — one row per labelled case and algorithm, including verdict, expected answer, pass/fail, missing prerequisites, counters, runtime and trace.
- `evaluation_summary.csv` — correct/incorrect verdict counts and accuracy percentage for each algorithm.
- `benchmark_results.csv` — raw timing rows for every repeated run.
- `benchmark_summary.csv` — median/mean/min/max timing and engine counters by size and algorithm.
- `benchmark_runtime.png` — median runtime vs. rule count.
- `benchmark_steps.png` — inference steps vs. rule count.
- `benchmark_rules_examined.png` — rules examined vs. rule count.

Recreate plots from the raw CSV at any time:

```bash
python plot_results.py --csv results/benchmark_results.csv --out-dir results
```

Use the median runtime for comparisons. Local execution times depend on the machine, Python version, background load and repetition count; do not present runtime from one machine as universal.

## 5. Metric definitions used

The measurement layer follows the counters already implemented and documented in `reasoning_engine.py`:

- **Accuracy:** number of labelled verdicts matching the independent expected label divided by the number of labelled cases.
- **Runtime:** measured with `time.perf_counter()` around the entire engine call; median is the primary reported statistic, with mean/min/max and raw repeats retained.
- **Backward inference steps:** number of goals entered, including goals rejected due to a cycle.
- **Forward inference steps:** body-to-fact unification attempts.
- **Backward rules examined:** candidate rule heads checked while expanding proof goals.
- **Forward rules examined:** rule candidates visited across closure passes.
- **Derived facts:** count of unique facts added beyond initial facts in Forward Chaining. Backward Chaining reports `N/A` because it proves goals rather than creating a closure.

These counts are algorithm-specific operational counters, not interchangeable measures of work. Compare trends within the same metric and explain the definition during the viva.

## 6. Why the scale benchmark reports exact predicate-rule counts

The project's domain generator accepts a number of **courses**, but `to_predicates()` expands each course into predicate rules and also adds two generic prerequisite rules. OR prerequisites can expand into multiple eligibility rules. Calling `generate_kb(50)` therefore does not mean the expanded logic KB contains exactly 50 rules.

To meet the PRD's **exact 50/100/250/500 predicate-rule** sizes, `benchmark.py` constructs controlled benchmark KBs where each course expands to one eligibility rule and one corequisite-satisfaction rule, plus two generic rules. Thus the course counts are 24, 49, 124 and 249 respectively. OR branches are reduced to one branch **only in the scale-controlled benchmark fixtures** to make the expanded rule count exact; the labelled functional tests separately check OR behavior. The benchmark CSV records both `rule_count` and `course_count` so this distinction is visible.

For each rule count, both algorithms receive the same generated KB, student (`student0`) and target course (the final course ID). The fixed seed makes the test fixture reproducible. This is a controlled scaling experiment, not a statistically comprehensive benchmark across all possible KB shapes.

## 7. Suggested Review 2 demo flow

1. Run `python -m pytest -q` and show the passing test count.
2. Run `python evaluate.py --mode tests --repeats 3`; point out scenario coverage and the accuracy summary.
3. Run the valid-waiver and invalid-waiver CLI examples; show how a waiver is scoped to one target course.
4. Run the domain cycle query and `python cycle_demo.py`; explain the distinction between a KB cycle diagnostic and the proof engine's recursive-goal cycle guard.
5. Run `python evaluate.py --mode benchmark --repeats 3 --seed 0`; open `benchmark_summary.csv` and the three plot files.
6. Explain that Forward and Backward Chaining expose different operational counter definitions, while the correctness verdicts are checked against the same independent labels.

## 8. Scope and limitations to state honestly

- No LLM is needed; eligibility decisions remain symbolic.
- The current CLI is the required minimal interface. Streamlit and NLP parsing are intentionally left optional.
- The labelled cases are a focused functional suite, not proof of correctness for every possible KB.
- Synthetic benchmark outputs measure this engine and these generated KBs; do not assert that one algorithm is universally faster.
