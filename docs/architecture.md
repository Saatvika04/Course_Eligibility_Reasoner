# Architecture

## 1. Overview

CourseLogic 2.0 is a symbolic course-eligibility reasoner. A JSON knowledge
base describes courses (prerequisite expressions over AND/OR, corequisites)
and students (completed courses, courses currently being taken, waivers). The
knowledge base is validated, compiled into ground facts and Horn-clause rules,
then solved by two independent reasoning algorithms — forward chaining and
backward chaining — which must agree. The result is a stable dictionary that
can be rendered as raw trace (CLI), a plain-English explanation (`explain.py`),
or an interactive browser UI (`app.py`).

## 2. Data flow

```
data/*.json  --load_kb/validate_kb-->  to_predicates() -->  reasoning_engine  -->  result dict
                                                              (forward/backward)        |
                                                                                        v
                                                              cli.py / app.py / explain.py
```

1. `load_kb` reads the JSON and `validate_kb` checks structural and reference
   integrity (unknown courses, malformed expressions, bad waivers, cycles).
2. `to_predicates` expands the validated KB into ground facts and Horn-clause
   rules (with `Var` objects for rule variables).
3. `reasoning_engine` runs either algorithm against the facts/rules and returns
   a result dict: `{eligible, student_id, course_id, missing_prerequisites,
   trace, inference_steps, rules_examined, derived_facts}`.
4. Presentation layers consume that dict: `cli.py` prints the verdict and raw
   trace, `app.py` renders it in a browser, and `explain.py` turns it into a
   readable justification derived from the KB itself.

## 3. Module responsibilities

| Module | Responsibility | Owner |
|---|---|---|
| `kb_loader.py` | Load, validate, save, cycle-detect a KB | Saatvika |
| `to_predicates.py` | Expand KB JSON into facts + Horn-clause rules | Saatvika |
| `reasoning_engine.py` | Forward + backward chaining; unification; result dict | Deepak |
| `explain.py` | Plain-English justification of a verdict | Saatvika |
| `app.py` | Streamlit web UI | Saatvika |
| `evaluate.py` | Run labelled cases against both engines | Mohammed |
| `metrics.py` | Result normalization and timing measurement | Mohammed |
| `benchmark.py` | Repeatable benchmarks on generated KBs | Mohammed |
| `cli.py` | Command-line eligibility query | Mohammed |
| `plot_results.py` | Benchmark plots | Mohammed |
| `evaluation_cases.py` | Labelled correctness cases | Mohammed |
| `generate_kb.py` | Seeded KB generator (50/100/250/500 rules) | Saatvika |

## 4. Reasoning semantics

- A prerequisite is satisfied by `completed(S,P)` **or** a waiver scoped to
  `(target_course, P)` — being *eligible* for `P` does **not** satisfy
  `C`'s prerequisite.
- A corequisite is satisfied by `taking(S,Q)` only.
- Eligibility is distinct from completion: eligibility reasons over the
  prerequisite/corequisite structure; it never infers that a course has been
  completed.
- AND/OR prerequisite expressions are evaluated to DNF over leaf courses.
- Generated KBs are acyclic; the demo KB's `CS401 <-> CS402` is a deliberate
  cycle used to exercise cycle detection.
