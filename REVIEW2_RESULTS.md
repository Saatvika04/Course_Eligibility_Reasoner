# Review 2 Results — Mohammed Wasif

**Project:** Course Eligibility Reasoner — Forward & Backward Chaining Engine  
**Course:** BCSE306L — Artificial Intelligence  
**Role:** Experiments, evaluation, results and CLI presentation

## Verification status

- Repository regression suite: **51 passed** (`python -m pytest -q`).
- Labelled course eligibility evaluation: **16/16 correct for Forward Chaining and 16/16 correct for Backward Chaining** (100% labelled accuracy for each algorithm).
- Benchmark sizes: **50, 100, 250 and 500 actual predicate rules**, checked against `len(to_predicates(kb)["rules"])`.
- Timing repeats: **3 per algorithm and rule count**; the CSV retains each individual measured run and the summary retains median, mean, minimum and maximum.
- Both algorithms receive the same KB, student and target course for each benchmark size.

## Labelled scenario coverage

`evaluation_cases.py` defines independently expected verdicts for: no prerequisites, satisfied single prerequisite, satisfied AND, missing AND condition, satisfied OR, both OR branches missing, corequisite being taken, missing corequisite, target-specific waiver, waiver not transferable to another course, prerequisite chain, eligibility-not-completion semantics, completed intermediate course, cyclic prerequisite component with no completed dependency, unseen student/course pair, and unknown course query.

`results/evaluation_results.csv` records the expected and actual verdict, pass/fail, missing prerequisites, timing statistics, counters and reasoning trace for each scenario and algorithm. `results/evaluation_summary.csv` records the accuracy summary.

## Benchmark summary

Seed `0` was used. The size-controlled fixtures use one eligibility rule and one corequisite-satisfaction rule per course, plus two generic prerequisite rules. This gives course counts 24, 49, 124 and 249 for exact expanded rule counts 50, 100, 250 and 500. OR branches are reduced to a selected first branch **only in the scale-control fixtures**; the separate labelled functional tests continue to test OR behavior. All benchmark knowledge bases remain acyclic.

| Predicate rules | Courses | Algorithm | Median time (ms) | Inference steps | Rules examined | Derived facts |
|---:|---:|---|---:|---:|---:|---:|
| 50 | 24 | Backward | 1.253 | 3 | 150 | N/A |
| 50 | 24 | Forward | 119.832 | 55,881 | 150 | 412 |
| 100 | 49 | Backward | 4.303 | 5 | 500 | N/A |
| 100 | 49 | Forward | 633.585 | 260,284 | 300 | 936 |
| 250 | 124 | Backward | 11.405 | 5 | 1,250 | N/A |
| 250 | 124 | Forward | 5,566.345 | 1,849,690 | 750 | 3,204 |
| 500 | 249 | Backward | 11.936 | 3 | 1,500 | N/A |
| 500 | 249 | Forward | 11,032.218 | 5,821,726 | 1,500 | 5,208 |

*Timings are observed on the machine used to run this report and are not universal performance guarantees.*

### Counter definitions

These definitions match the counters already implemented in `reasoning_engine.py`:

- **Runtime:** `time.perf_counter()` around an engine call; median is the primary comparison statistic.
- **Backward inference steps:** number of goals entered, including goals rejected as cycles.
- **Forward inference steps:** body-to-fact unification attempts.
- **Backward rules examined:** candidate rule heads inspected during goal expansion.
- **Forward rules examined:** rule applications visited across closure passes.
- **Derived facts:** unique facts added beyond input facts by Forward Chaining; `N/A` for Backward Chaining because it proves goals without building a closure.

Because the engines count different operations, step counts should be interpreted within an algorithm, not treated as directly equivalent units of work.

## Files added for the role

- `evaluation_cases.py` — independent labels and their shared functional KB.
- `data/evaluation_knowledge_base.json` — readable KB for CLI demonstrations.
- `evaluate.py` — labelled correctness runner and benchmark entry point.
- `metrics.py` — result normalization and repeated timing.
- `benchmark.py` — exact expanded predicate-rule benchmark KBs and raw/summary CSVs.
- `plot_results.py` — recreates charts from the raw benchmark CSV.
- `cli.py` — student/course query and reasoning trace display.
- `cycle_demo.py` — direct demonstration of the engine's recursive-goal cycle guard.
- `tests/test_evaluation.py` — regression tests for labels, metrics, CSVs, benchmark sizes, plots and cycle guard.
- `REVIEW2_GUIDE.md` — installation, execution, viva demo and metric definitions.
- `results/` — evaluated case CSVs, benchmark CSVs, and three PNG plots.

## Run the demonstration

```bash
python -m pip install -r requirements.txt
python -m pytest -q
python evaluate.py --mode tests --repeats 3
python cli.py bob CS203 --algorithm both
python cli.py case_student WAIVER_TARGET --kb data/evaluation_knowledge_base.json --algorithm both
python cli.py case_student WAIVER_OTHER_TARGET --kb data/evaluation_knowledge_base.json --algorithm both
python cycle_demo.py
python evaluate.py --mode benchmark --repeats 3 --seed 0
```

To run tests and benchmarks together, use `python evaluate.py --mode all --repeats 3 --seed 0`. The benchmark can take noticeably longer than the functional suite because Forward Chaining computes a closure over the full KB.

## Limitations and honest interpretation

The labels are a focused correctness suite, not a mathematical proof of correctness for all knowledge bases. The synthetic scale benchmark uses one fixed seed, one student and one target course for each size, and controlled single-branch prerequisite expressions so that exact expanded rule counts can be selected. Runtime depends on machine, Python version, background load and KB structure. The result supports a comparison on these tests only; it does not establish that either algorithm is always faster for every query or knowledge base.
