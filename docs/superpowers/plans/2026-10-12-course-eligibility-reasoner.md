# Course Eligibility Reasoner (KB Module + Stub Engine) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Saatvika's knowledge-base module (schema, demo KB, generator, loader/validator, predicate bridge) plus a minimal backward-chaining stub engine to verify KBs standalone.

**Architecture:** Layered pipeline — domain JSON (canonical schema) → `kb_loader.py` (validate/load/save) → `to_predicates.py` (expand to facts + Horn-clause rules) → `stub_engine.py` (backward-chaining prover). Flat modules at the project root so they merge cleanly with Deepak's `reasoning_engine.py` and Mohammed's `evaluate.py`/`cli.py` later.

**Tech Stack:** Python 3.12.3 (satisfies 3.11+), `uv` for the virtualenv, `pytest` for tests. No external inference library.

## Global Constraints

- Python 3.11+ (use the installed 3.12.3).
- No external inference/rule-engine library — stdlib + `pytest` only.
- Domain JSON is the canonical interchange format handed to Deepak and Mohammed.
- Corequisite is satisfied by `taking(S,Q)` only.
- A prerequisite is satisfied by `completed(S,P)` **or** `waiver(S,C,P)` — **never** by eligibility (`eligibility != completion`).
- Generated benchmark KBs (50/100/250/500) are **acyclic**; the hand-written demo KB carries the single deliberate cycle.
- One test command: `uv run pytest` (run from the project root).
- Variables in rule heads/bodies are `Var` objects (`to_predicates.Var`); constants are plain strings.
- All commits use the local identity `Saatvika04 <saatvika.ed@gmail.com>` (already set).

---

### Task 1: Scaffolding, demo KB, schema doc

**Files:**
- Create: `.gitignore`
- Create: `requirements.txt`
- Create: `pytest.ini`
- Create: `data/knowledge_base.json`
- Create: `kb_schema.md`

**Interfaces:**
- Produces: `data/knowledge_base.json` (validated demo KB consumed by Tasks 2–4 tests), `kb_schema.md` (schema documentation), `pytest.ini` (makes project root importable so `import kb_loader` works from `tests/`).

- [ ] **Step 1: Write `.gitignore`**

```gitignore
.venv/
__pycache__/
*.pyc
.pytest_cache/
data/generated/
```

- [ ] **Step 2: Write `requirements.txt`**

```
pytest
```

- [ ] **Step 3: Write `pytest.ini`**

```ini
[pytest]
pythonpath = .
testpaths = tests
```

- [ ] **Step 4: Write `data/knowledge_base.json`**

```json
{
  "courses": {
    "MATH101": {"prerequisite": null, "corequisites": []},
    "CS101": {"prerequisite": null, "corequisites": []},
    "CS102": {"prerequisite": "CS101", "corequisites": []},
    "CS201": {"prerequisite": {"and": ["CS101", "MATH101"]}, "corequisites": []},
    "CS202": {"prerequisite": {"or": ["CS101", "MATH101"]}, "corequisites": []},
    "CS203": {"prerequisite": "CS102", "corequisites": ["CS201"]},
    "CS301": {"prerequisite": "CS203", "corequisites": []},
    "CS302": {"prerequisite": {"and": ["CS102", {"or": ["CS101", "MATH101"]}]}, "corequisites": []},
    "CS401": {"prerequisite": "CS402", "corequisites": []},
    "CS402": {"prerequisite": "CS401", "corequisites": []}
  },
  "students": {
    "bob": {
      "completed": ["CS101", "MATH101", "CS102"],
      "taking": ["CS201"],
      "waivers": [{"course": "CS202", "prerequisite": "MATH101"}]
    },
    "alice": {
      "completed": ["CS101"],
      "taking": [],
      "waivers": []
    }
  }
}
```

This covers every rule type: no prereq (`MATH101`, `CS101`), single (`CS102`), AND (`CS201`), OR (`CS202`), corequisite (`CS203`), multi-step chain (`CS301` → `CS203` → `CS102` → `CS101`), nested AND-of-OR (`CS302`), and a deliberate cycle (`CS401` ↔ `CS402`).

- [ ] **Step 5: Write `kb_schema.md`**

````markdown
# Knowledge-Base Schema

The canonical interchange format is a JSON object with two top-level keys.

## Top level

```json
{ "courses": { ... }, "students": { ... } }
```

- `courses`: object mapping course id (string) → course object.
- `students`: object mapping student id (string) → student object.

## Course object

```json
{ "prerequisite": <expr>, "corequisites": ["CS201"] }
```

- `prerequisite`: `null`, a course id string, or a nested expression
  `{"and": [<expr>, ...]}` / `{"or": [<expr>, ...]}`. `and`/`or` arrays are
  non-empty and may nest arbitrarily.
- `corequisites`: list of course ids the student must be concurrently `taking`.

## Student object

```json
{ "completed": ["CS101"], "taking": ["CS201"], "waivers": [{"course": "CS202", "prerequisite": "MATH101"}] }
```

- `completed`: course ids the student has finished.
- `taking`: course ids the student is currently enrolled in.
- `waivers`: list of `{course, prerequisite}` — a waiver scoped to
  `(student, target course, prerequisite)`.

## Validity rules

Every course id referenced anywhere (prerequisite expressions, corequisites,
`completed`, `taking`, waivers) must exist in `courses`.

## Reasoning semantics

- A prerequisite `P` of course `C` is satisfied by `completed(S,P)` **or**
  `waiver(S,C,P)`. Being *eligible* for `P` does **not** satisfy `C`'s
  prerequisite (`eligibility != completion`).
- `AND` requires every child; `OR` requires at least one.
- A corequisite `Q` is satisfied by `taking(S,Q)` only.
````

- [ ] **Step 6: Verify the venv works**

Run: `uv run pytest --version`
Expected: `pytest 9.1.1`

- [ ] **Step 7: Commit**

```bash
git add .gitignore requirements.txt pytest.ini data/knowledge_base.json kb_schema.md
git commit -m "chore: scaffold project with demo KB, schema doc, and pytest config"
```

---

### Task 2: Knowledge-base loader and validator

**Files:**
- Create: `kb_loader.py`
- Test: `tests/test_kb_loader.py`

**Interfaces:**
- Produces (used by Tasks 4–6):
  - `load_kb(path: str) -> dict` — read + validate a JSON KB; raise `ValueError` listing all errors on invalid input.
  - `save_kb(kb: dict, path: str) -> None` — write indented JSON.
  - `validate_kb(kb: dict) -> list[str]` — return list of error strings (empty = valid).
  - `detect_prereq_cycles(kb: dict) -> list[list[str]]` — return prerequisite cycles, each a list of course ids.

- [ ] **Step 1: Write the failing test**

`tests/test_kb_loader.py`:

```python
import os

from kb_loader import load_kb, save_kb, validate_kb, detect_prereq_cycles


DEMO = os.path.join(os.path.dirname(__file__), "..", "data", "knowledge_base.json")


def test_demo_kb_loads_and_is_valid():
    kb = load_kb(DEMO)
    assert validate_kb(kb) == []
    assert "CS101" in kb["courses"]


def test_validate_rejects_unknown_prerequisite():
    kb = {"courses": {"A": {"prerequisite": "B", "corequisites": []}}, "students": {}}
    assert any("unknown course 'B'" in e for e in validate_kb(kb))


def test_validate_rejects_unknown_corequisite():
    kb = {"courses": {"A": {"prerequisite": None, "corequisites": ["ZZZ"]}}, "students": {}}
    assert any("unknown" in e for e in validate_kb(kb))


def test_validate_rejects_malformed_expression():
    kb = {"courses": {"A": {"prerequisite": {"and": []}, "corequisites": []}}, "students": {}}
    assert any("non-empty list" in e for e in validate_kb(kb))


def test_validate_rejects_unknown_student_course():
    kb = {
        "courses": {"A": {"prerequisite": None, "corequisites": []}},
        "students": {"s": {"completed": ["B"], "taking": [], "waivers": []}},
    }
    assert any("unknown course 'B'" in e for e in validate_kb(kb))


def test_validate_rejects_bad_waiver():
    kb = {
        "courses": {"A": {"prerequisite": None, "corequisites": []}},
        "students": {"s": {"completed": [], "taking": [], "waivers": [{"course": "B", "prerequisite": "A"}]}},
    }
    assert any("waiver" in e for e in validate_kb(kb))


def test_save_and_load_roundtrip(tmp_path):
    kb = {"courses": {"A": {"prerequisite": None, "corequisites": []}}, "students": {}}
    p = tmp_path / "kb.json"
    save_kb(kb, str(p))
    assert load_kb(str(p)) == kb


def test_detect_prereq_cycles_finds_cycle():
    kb = load_kb(DEMO)
    cycles = detect_prereq_cycles(kb)
    assert any(set(c) == {"CS401", "CS402"} for c in cycles)


def test_detect_prereq_cycles_none_when_acyclic():
    kb = {
        "courses": {
            "A": {"prerequisite": None, "corequisites": []},
            "B": {"prerequisite": "A", "corequisites": []},
        },
        "students": {},
    }
    assert detect_prereq_cycles(kb) == []
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_kb_loader.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'kb_loader'`

- [ ] **Step 3: Write `kb_loader.py`**

```python
"""Load, validate, and save knowledge-base JSON files."""

import json


def load_kb(path):
    """Load and validate a knowledge base from a JSON file.

    Raises ValueError if the file is missing required fields or contains
    invalid references. Returns the parsed dict on success.
    """
    with open(path, "r", encoding="utf-8") as f:
        kb = json.load(f)
    errors = validate_kb(kb)
    if errors:
        raise ValueError("invalid knowledge base:\n- " + "\n- ".join(errors))
    return kb


def save_kb(kb, path):
    """Write a knowledge base to a JSON file (indented, stable key order)."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(kb, f, indent=2, ensure_ascii=False)
        f.write("\n")


def validate_kb(kb):
    """Return a list of human-readable errors; empty list means valid."""
    errors = []
    if not isinstance(kb, dict):
        return ["knowledge base must be a JSON object"]
    courses = kb.get("courses")
    students = kb.get("students")
    if not isinstance(courses, dict):
        errors.append("'courses' must be an object mapping course id -> course")
    if not isinstance(students, dict):
        errors.append("'students' must be an object mapping student id -> student")
    if not isinstance(courses, dict) or not isinstance(students, dict):
        return errors

    course_ids = set(courses.keys())

    for cid, course in courses.items():
        if not isinstance(course, dict):
            errors.append(f"course '{cid}' must be an object")
            continue
        errors.extend(_validate_expr(course.get("prerequisite"), course_ids, f"course '{cid}' prerequisite"))
        coreqs = course.get("corequisites", [])
        if not isinstance(coreqs, list):
            errors.append(f"course '{cid}' corequisites must be a list")
        else:
            for q in coreqs:
                if not isinstance(q, str):
                    errors.append(f"course '{cid}' corequisite must be a course id string")
                elif q not in course_ids:
                    errors.append(f"course '{cid}' corequisite '{q}' is unknown")

    for sid, student in students.items():
        if not isinstance(student, dict):
            errors.append(f"student '{sid}' must be an object")
            continue
        for field in ("completed", "taking"):
            lst = student.get(field, [])
            if not isinstance(lst, list):
                errors.append(f"student '{sid}' {field} must be a list")
                continue
            for c in lst:
                if not isinstance(c, str):
                    errors.append(f"student '{sid}' {field} must contain course id strings")
                elif c not in course_ids:
                    errors.append(f"student '{sid}' {field} references unknown course '{c}'")
        waivers = student.get("waivers", [])
        if not isinstance(waivers, list):
            errors.append(f"student '{sid}' waivers must be a list")
            continue
        for w in waivers:
            if not isinstance(w, dict):
                errors.append(f"student '{sid}' has a non-object waiver")
                continue
            target = w.get("course")
            prereq = w.get("prerequisite")
            if not isinstance(target, str) or target not in course_ids:
                errors.append(f"student '{sid}' waiver target '{target}' is unknown")
            if not isinstance(prereq, str) or prereq not in course_ids:
                errors.append(f"student '{sid}' waiver prerequisite '{prereq}' is unknown")

    return errors


def _validate_expr(expr, course_ids, path):
    """Validate a prerequisite expression; return a list of errors."""
    errors = []
    if expr is None:
        return errors
    if isinstance(expr, str):
        if expr not in course_ids:
            errors.append(f"{path} references unknown course '{expr}'")
        return errors
    if isinstance(expr, dict):
        keys = [k for k in expr if k in ("and", "or")]
        if len(keys) != 1:
            errors.append(f"{path} must be a course id, null, or an object with exactly one 'and'/'or' key")
            return errors
        op = keys[0]
        children = expr[op]
        if not isinstance(children, list) or len(children) == 0:
            errors.append(f"{path} '{op}' must be a non-empty list")
            return errors
        for i, child in enumerate(children):
            errors.extend(_validate_expr(child, course_ids, f"{path} {op}[{i}]"))
        return errors
    errors.append(f"{path} must be null, a course id string, or an 'and'/'or' object")
    return errors


def _leaves(expr):
    """Return the set of course ids referenced by a prerequisite expression."""
    if expr is None:
        return set()
    if isinstance(expr, str):
        return {expr}
    out = set()
    for child in expr.get("and", expr.get("or", [])):
        out |= _leaves(child)
    return out


def detect_prereq_cycles(kb):
    """Return a list of prerequisite cycles, each a list of course ids.

    A cycle is a loop in the prerequisite graph, e.g. A requires B and B
    requires A. Each cycle is reported as a list starting and ending at the
    same course. Assumes kb is already validated.
    """
    courses = kb["courses"]
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {cid: WHITE for cid in courses}
    cycles = []
    stack = []

    def dfs(cid):
        color[cid] = GRAY
        stack.append(cid)
        for p in sorted(_leaves(courses[cid]["prerequisite"])):
            if p not in color:
                continue
            if color[p] == GRAY:
                idx = stack.index(p)
                cycles.append(stack[idx:] + [p])
            elif color[p] == WHITE:
                dfs(p)
        stack.pop()
        color[cid] = BLACK

    for cid in courses:
        if color[cid] == WHITE:
            dfs(cid)
    return cycles
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run pytest tests/test_kb_loader.py -q`
Expected: PASS (9 passed)

- [ ] **Step 5: Commit**

```bash
git add kb_loader.py tests/test_kb_loader.py
git commit -m "feat: add KB loader, validator, and cycle detection"
```

---

### Task 3: Predicate bridge

**Files:**
- Create: `to_predicates.py`
- Test: `tests/test_to_predicates.py`

**Interfaces:**
- Produces (used by Task 4):
  - `class Var` — logical variable; `Var("S") == Var("S")`, `str(Var("S")) == "S"`.
  - `to_predicates(kb: dict) -> dict` — returns `{"facts": [...], "rules": [...]}`. Facts are tuples of constant strings, e.g. `("completed", "bob", "CS101")`. Rules are `{"head": (...), "body": [...]}` where variables are `Var` objects.

- [ ] **Step 1: Write the failing test**

`tests/test_to_predicates.py`:

```python
import os

from to_predicates import to_predicates, Var


DEMO = os.path.join(os.path.dirname(__file__), "..", "data", "knowledge_base.json")


def test_facts_include_completed():
    kb = {
        "courses": {"A": {"prerequisite": None, "corequisites": []}},
        "students": {"s": {"completed": ["A"], "taking": [], "waivers": []}},
    }
    pred = to_predicates(kb)
    assert ("completed", "s", "A") in pred["facts"]


def test_single_prereq_emits_prereq_fact():
    kb = {
        "courses": {
            "A": {"prerequisite": "B", "corequisites": []},
            "B": {"prerequisite": None, "corequisites": []},
        },
        "students": {},
    }
    pred = to_predicates(kb)
    assert ("prereq", "A", "B") in pred["facts"]


def test_and_prereq_compiles_to_one_rule():
    kb = {
        "courses": {
            "A": {"prerequisite": {"and": ["B", "C"]}, "corequisites": []},
            "B": {"prerequisite": None, "corequisites": []},
            "C": {"prerequisite": None, "corequisites": []},
        },
        "students": {},
    }
    pred = to_predicates(kb)
    eligible_rules = [r for r in pred["rules"] if r["head"][0] == "eligible"]
    assert len(eligible_rules) == 1


def test_or_prereq_compiles_to_two_rules():
    kb = {
        "courses": {
            "A": {"prerequisite": {"or": ["B", "C"]}, "corequisites": []},
            "B": {"prerequisite": None, "corequisites": []},
            "C": {"prerequisite": None, "corequisites": []},
        },
        "students": {},
    }
    pred = to_predicates(kb)
    eligible_rules = [r for r in pred["rules"] if r["head"][0] == "eligible"]
    assert len(eligible_rules) == 2


def test_global_prereq_satisfied_rules_present():
    pred = to_predicates({"courses": {}, "students": {}})
    heads = [r["head"] for r in pred["rules"]]
    assert ("prereq_satisfied", Var("S"), Var("C"), Var("P")) in heads


def test_waiver_fact_emitted():
    kb = {
        "courses": {
            "A": {"prerequisite": "B", "corequisites": []},
            "B": {"prerequisite": None, "corequisites": []},
        },
        "students": {"s": {"completed": [], "taking": [], "waivers": [{"course": "A", "prerequisite": "B"}]}},
    }
    pred = to_predicates(kb)
    assert ("waiver", "s", "A", "B") in pred["facts"]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_to_predicates.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'to_predicates'`

- [ ] **Step 3: Write `to_predicates.py`**

```python
"""Expand a validated knowledge base into ground facts and Horn-clause rules."""


class Var:
    """A logical variable used in rule heads and bodies."""

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.name

    def __eq__(self, other):
        return isinstance(other, Var) and other.name == self.name

    def __hash__(self):
        return hash(("Var", self.name))


S = Var("S")
C = Var("C")
P = Var("P")


def _to_dnf(expr):
    """Convert a prerequisite expression to disjunctive normal form.

    Returns a list of clauses; each clause is a list of leaf course ids that
    must ALL be satisfied. OR becomes multiple clauses; AND flattens into a
    single clause via the cartesian product of its children's clauses.
    """
    if isinstance(expr, str):
        return [[expr]]
    if "and" in expr:
        parts = [_to_dnf(child) for child in expr["and"]]
        clauses = [[]]
        for part in parts:
            clauses = [c + d for c in clauses for d in part]
        return clauses
    if "or" in expr:
        clauses = []
        for child in expr["or"]:
            clauses.extend(_to_dnf(child))
        return clauses
    return []  # unreachable for validated KBs


def to_predicates(kb):
    """Return {"facts": [...], "rules": [...]} for a validated knowledge base.

    Facts are tuples of constant strings, e.g. ("completed", "bob", "CS101").
    Rules are dicts {"head": (...), "body": [...]}; variables are Var objects.
    """
    facts = []
    rules = []
    courses = kb["courses"]
    students = kb["students"]

    for cid, course in courses.items():
        prereq = course["prerequisite"]
        coreqs = course.get("corequisites", [])

        for q in coreqs:
            facts.append(("coreq", cid, q))

        # corequisites satisfied only if every corequisite is being taken.
        rules.append({
            "head": ("coreqs_satisfied", S, cid),
            "body": [("taking", S, q) for q in coreqs],
        })

        if prereq is None:
            facts.append(("no_prereq", cid))
            rules.append({
                "head": ("eligible", S, cid),
                "body": [("no_prereq", cid), ("coreqs_satisfied", S, cid)],
            })
        elif isinstance(prereq, str):
            facts.append(("prereq", cid, prereq))
            rules.append({
                "head": ("eligible", S, cid),
                "body": [
                    ("prereq", cid, prereq),
                    ("prereq_satisfied", S, cid, prereq),
                    ("coreqs_satisfied", S, cid),
                ],
            })
        else:
            for clause in _to_dnf(prereq):
                body = [("prereq_satisfied", S, cid, p) for p in clause]
                body.append(("coreqs_satisfied", S, cid))
                rules.append({"head": ("eligible", S, cid), "body": body})

    # Global rules: how a single prerequisite is satisfied.
    rules.append({"head": ("prereq_satisfied", S, C, P), "body": [("waiver", S, C, P)]})
    rules.append({"head": ("prereq_satisfied", S, C, P), "body": [("completed", S, P)]})

    for sid, student in students.items():
        for c in student.get("completed", []):
            facts.append(("completed", sid, c))
        for c in student.get("taking", []):
            facts.append(("taking", sid, c))
        for w in student.get("waivers", []):
            facts.append(("waiver", sid, w["course"], w["prerequisite"]))

    return {"facts": facts, "rules": rules}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run pytest tests/test_to_predicates.py -q`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add to_predicates.py tests/test_to_predicates.py
git commit -m "feat: add predicate bridge (domain JSON -> facts + Horn rules)"
```

---

### Task 4: Stub engine (backward-chaining prover)

**Files:**
- Create: `stub_engine.py`
- Test: `tests/test_stub_engine.py`

**Interfaces:**
- Consumes: `to_predicates.to_predicates`, `to_predicates.Var` (Task 3).
- Produces (used by Task 6):
  - `backward_chain(kb: dict, student_id: str, course_id: str) -> dict` — returns `{"eligible": bool, "student_id": str, "course_id": str, "missing_prerequisites": [str], "trace": [str], "inference_steps": int}`.
  - `prove(facts: list, rules: list, goal: tuple) -> dict` — same shape minus student/course ids; exposed for the cycle-detection unit test.

- [ ] **Step 1: Write the failing test**

`tests/test_stub_engine.py`:

```python
import json
import os

from stub_engine import backward_chain, prove
from to_predicates import Var


DEMO = os.path.join(os.path.dirname(__file__), "..", "data", "knowledge_base.json")


def _demo():
    with open(DEMO) as f:
        return json.load(f)


def test_no_prereq_eligible():
    assert backward_chain(_demo(), "bob", "CS101")["eligible"] is True


def test_single_prereq_eligible():
    assert backward_chain(_demo(), "bob", "CS102")["eligible"] is True


def test_and_prereq_eligible():
    assert backward_chain(_demo(), "bob", "CS201")["eligible"] is True


def test_and_prereq_missing():
    r = backward_chain(_demo(), "alice", "CS201")
    assert r["eligible"] is False
    assert "MATH101" in r["missing_prerequisites"]


def test_or_prereq_eligible():
    assert backward_chain(_demo(), "bob", "CS202")["eligible"] is True


def test_coreq_satisfied_by_taking():
    kb = {
        "courses": {
            "A": {"prerequisite": "B", "corequisites": ["C"]},
            "B": {"prerequisite": None, "corequisites": []},
            "C": {"prerequisite": None, "corequisites": []},
        },
        "students": {"s": {"completed": ["B"], "taking": ["C"], "waivers": []}},
    }
    assert backward_chain(kb, "s", "A")["eligible"] is True


def test_coreq_unsatisfied():
    kb = {
        "courses": {
            "A": {"prerequisite": "B", "corequisites": ["C"]},
            "B": {"prerequisite": None, "corequisites": []},
            "C": {"prerequisite": None, "corequisites": []},
        },
        "students": {"s": {"completed": ["B"], "taking": [], "waivers": []}},
    }
    assert backward_chain(kb, "s", "A")["eligible"] is False


def test_waiver_satisfies_prerequisite():
    kb = {
        "courses": {
            "A": {"prerequisite": "B", "corequisites": []},
            "B": {"prerequisite": None, "corequisites": []},
        },
        "students": {"s": {"completed": [], "taking": [], "waivers": [{"course": "A", "prerequisite": "B"}]}},
    }
    assert backward_chain(kb, "s", "A")["eligible"] is True


def test_eligibility_is_not_completion():
    # bob completed CS102 (so he IS eligible for CS203), but he has NOT
    # completed CS203, so he is NOT eligible for CS301 even though CS301's
    # only prerequisite is CS203.
    kb = _demo()
    assert backward_chain(kb, "bob", "CS203")["eligible"] is True
    r = backward_chain(kb, "bob", "CS301")
    assert r["eligible"] is False
    assert "CS203" in r["missing_prerequisites"]


def test_cycle_in_data_terminates():
    # CS401 <-> CS402 cycle. Completion-only semantics mean this is just data:
    # the query must terminate (no infinite recursion) and report not eligible.
    r = backward_chain(_demo(), "bob", "CS401")
    assert r["eligible"] is False


def test_unseen_query():
    # alice completed only CS101; CS302 needs CS102 AND (CS101 OR MATH101).
    r = backward_chain(_demo(), "alice", "CS302")
    assert r["eligible"] is False
    assert "CS102" in r["missing_prerequisites"]


def test_cycle_detection_on_recursive_rules():
    # Prove the prover's active-path cycle detection with a synthetic
    # recursive rule set: a(X) :- b(X), b(X) :- a(X), a(X) :- base(X).
    X = Var("X")
    facts = [("base", "x")]
    rules = [
        {"head": ("a", X), "body": [("b", X)]},
        {"head": ("b", X), "body": [("a", X)]},
        {"head": ("a", X), "body": [("base", X)]},
    ]
    result = prove(facts, rules, ("a", "x"))
    assert result["eligible"] is True
    assert any("CYCLE" in line for line in result["trace"])
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_stub_engine.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'stub_engine'`

- [ ] **Step 3: Write `stub_engine.py`**

```python
"""Minimal backward-chaining prover (stub engine) for verifying a KB."""

from to_predicates import to_predicates, Var


def _is_var(term):
    return isinstance(term, Var)


def _subst(term, subst):
    while _is_var(term) and term.name in subst:
        term = subst[term.name]
    return term


def _unify(x, y, subst):
    if subst is None:
        return None
    x = _subst(x, subst)
    y = _subst(y, subst)
    if x == y:
        return dict(subst)
    if _is_var(x):
        out = dict(subst)
        out[x.name] = y
        return out
    if _is_var(y):
        out = dict(subst)
        out[y.name] = x
        return out
    return None


def _unify_tuple(goal, pattern, subst):
    if len(goal) != len(pattern):
        return None
    for a, b in zip(goal, pattern):
        subst = _unify(a, b, subst)
        if subst is None:
            return None
    return subst


def _fmt(pred):
    return f"{pred[0]}({', '.join(str(t) for t in pred[1:])})"


def _prove(goal, subst, facts, rules, state):
    """Return (success, subst). state tracks steps, trace, missing, active path."""
    state["steps"] += 1
    goal = tuple(_subst(t, subst) for t in goal)
    key = tuple(t.name if _is_var(t) else t for t in goal)

    if key in state["active_path"]:
        state["trace"].append(f"  CYCLE {_fmt(goal)}")
        return False, subst

    state["active_path"].append(key)
    state["trace"].append(f"GOAL {_fmt(goal)}")
    try:
        for fact in facts:
            u = _unify_tuple(goal, fact, subst)
            if u is not None:
                state["trace"].append(f"  FACT {_fmt(fact)}")
                return True, u

        for rule in rules:
            u = _unify_tuple(goal, rule["head"], subst)
            if u is None:
                continue
            state["trace"].append(
                f"  RULE {_fmt(rule['head'])} :- {', '.join(_fmt(b) for b in rule['body'])}"
            )
            cur = u
            ok = True
            for lit in rule["body"]:
                ok, cur = _prove(lit, cur, facts, rules, state)
                if not ok:
                    break
            if ok:
                return True, cur

        if goal and goal[0] == "prereq_satisfied" and len(goal) == 4 and all(not _is_var(t) for t in goal):
            state["missing"].add(goal[3])
        state["trace"].append(f"  FAIL {_fmt(goal)}")
        return False, subst
    finally:
        state["active_path"].pop()


def prove(facts, rules, goal):
    """Prove a single goal against a fact/rule set. Returns a result dict."""
    state = {"steps": 0, "trace": [], "missing": set(), "active_path": []}
    ok, _ = _prove(goal, {}, facts, rules, state)
    return {
        "eligible": ok,
        "missing_prerequisites": sorted(state["missing"]),
        "trace": state["trace"],
        "inference_steps": state["steps"],
    }


def backward_chain(kb, student_id, course_id):
    """Answer eligible(student_id, course_id) and return a result dict."""
    pred = to_predicates(kb)
    result = prove(pred["facts"], pred["rules"], ("eligible", student_id, course_id))
    result["student_id"] = student_id
    result["course_id"] = course_id
    return result
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run pytest tests/test_stub_engine.py -q`
Expected: PASS (12 passed)

- [ ] **Step 5: Commit**

```bash
git add stub_engine.py tests/test_stub_engine.py
git commit -m "feat: add backward-chaining stub engine with unification and cycle detection"
```

---

### Task 5: Seeded generator for 50/100/250/500-rule KBs

**Files:**
- Create: `generate_kb.py`
- Test: `tests/test_generate_kb.py`

**Interfaces:**
- Consumes: `kb_loader.save_kb` (Task 2).
- Produces (used by Task 6):
  - `generate_kb(n: int, seed: int = 0) -> dict` — deterministic synthetic KB with `n` courses; returns `{"courses": ..., "students": ..., "seed": int, "requested_rule_count": int}`.
  - CLI: `python generate_kb.py 50 --seed 0` writes `data/generated/kb_50_seed0.json`.

- [ ] **Step 1: Write the failing test**

`tests/test_generate_kb.py`:

```python
from kb_loader import validate_kb, detect_prereq_cycles
from generate_kb import generate_kb


def test_reproducible_same_seed():
    assert generate_kb(50, seed=7) == generate_kb(50, seed=7)


def test_different_seed_differs():
    assert generate_kb(50, seed=1) != generate_kb(50, seed=2)


def test_requested_rule_count():
    for n in (50, 100, 250, 500):
        kb = generate_kb(n, seed=0)
        assert kb["requested_rule_count"] == n
        assert len(kb["courses"]) == n


def test_generated_kb_is_valid():
    for n in (50, 100, 250, 500):
        assert validate_kb(generate_kb(n, seed=0)) == []


def test_generated_kb_is_acyclic():
    assert detect_prereq_cycles(generate_kb(500, seed=0)) == []
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_generate_kb.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'generate_kb'`

- [ ] **Step 3: Write `generate_kb.py`**

```python
"""Generate deterministic synthetic knowledge bases at a requested rule count."""

import argparse
import os
import random

from kb_loader import save_kb


def generate_kb(n, seed=0):
    """Return a synthetic knowledge base with n courses (one rule each).

    Prerequisites always reference earlier courses, so the resulting graph is
    acyclic. The same (n, seed) always produces identical data.
    """
    rng = random.Random(seed)
    courses = {}
    for i in range(n):
        cid = f"C{i:03d}"
        courses[cid] = {
            "prerequisite": _choose_prereq(rng, i),
            "corequisites": _choose_coreqs(rng, i),
        }
    students = _generate_students(rng, n)
    return {
        "courses": courses,
        "students": students,
        "seed": seed,
        "requested_rule_count": n,
    }


def _choose_prereq(rng, i):
    if i == 0:
        return None
    earlier = [f"C{j:03d}" for j in range(i)]
    r = rng.random()
    if r < 0.15:
        return None
    if r < 0.55:
        return rng.choice(earlier)
    if r < 0.80:
        a, b = rng.sample(earlier, 2)
        return {"and": [a, b]}
    a, b = rng.sample(earlier, 2)
    return {"or": [a, b]}


def _choose_coreqs(rng, i):
    if i >= 1 and rng.random() < 0.2:
        return [f"C{rng.randrange(i):03d}"]
    return []


def _generate_students(rng, n):
    ids = [f"C{i:03d}" for i in range(n)]
    students = {}
    for s in range(5):
        k = rng.randint(0, min(n, 10))
        completed = rng.sample(ids, k) if k else []
        taking = [rng.choice(ids)] if rng.random() < 0.5 else []
        waivers = []
        for _ in range(rng.randint(0, 2)):
            waivers.append({
                "course": rng.choice(ids),
                "prerequisite": rng.choice(ids),
            })
        students[f"student{s}"] = {
            "completed": completed,
            "taking": taking,
            "waivers": waivers,
        }
    return students


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate a synthetic course-eligibility KB.")
    parser.add_argument("n", type=int, help="number of courses (rules)")
    parser.add_argument("--seed", type=int, default=0, help="random seed (default 0)")
    parser.add_argument("--out-dir", default="data/generated", help="output directory")
    args = parser.parse_args(argv)

    kb = generate_kb(args.n, seed=args.seed)
    os.makedirs(args.out_dir, exist_ok=True)
    path = os.path.join(args.out_dir, f"kb_{args.n}_seed{args.seed}.json")
    save_kb(kb, path)
    print(f"wrote {args.n} rules (seed={args.seed}) to {path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run pytest tests/test_generate_kb.py -q`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add generate_kb.py tests/test_generate_kb.py
git commit -m "feat: add seeded generator for 50/100/250/500-rule KBs"
```

---

### Task 6: README and full-suite verification

**Files:**
- Create: `README.md`

**Interfaces:**
- Consumes: `load_kb`, `generate_kb`, `backward_chain` (Tasks 2, 4, 5).

- [ ] **Step 1: Write `README.md`**

````markdown
# Course Eligibility Reasoner

Decides whether a student is eligible for a course from a knowledge base of
prerequisites (AND/OR), corequisites, waivers, and multi-step chains. This
repo holds the **knowledge-base module** (Saatvika) plus a minimal
backward-chaining **stub engine** used to verify KBs standalone. Deepak's
`reasoning_engine.py` and Mohammed's `evaluate.py`/`cli.py` merge in later.

## Setup

```bash
uv venv
uv pip install -r requirements.txt
```

## Files

- `kb_loader.py` — load, validate, save, and cycle-detect a KB.
- `to_predicates.py` — expand domain JSON into facts + Horn-clause rules.
- `stub_engine.py` — backward-chaining prover (unification + cycle detection).
- `generate_kb.py` — seeded generator for 50/100/250/500-rule KBs.
- `data/knowledge_base.json` — hand-written demo KB (has one deliberate cycle).
- `kb_schema.md` — schema definition and reasoning semantics.

## Usage

```python
from kb_loader import load_kb
from stub_engine import backward_chain

kb = load_kb("data/knowledge_base.json")
result = backward_chain(kb, "bob", "CS301")
print(result["eligible"])                # True/False
print(result["missing_prerequisites"])   # e.g. ["CS203"]
print(result["trace"])                   # proof trace
```

Generate benchmark KBs:

```bash
python generate_kb.py 50 --seed 0     # -> data/generated/kb_50_seed0.json
python generate_kb.py 100 --seed 0
python generate_kb.py 250 --seed 0
python generate_kb.py 500 --seed 0
```

## Run tests

```bash
uv run pytest
```

## Key semantics

- A prerequisite is satisfied by `completed(S,P)` **or** `waiver(S,C,P)` —
  being *eligible* for `P` does **not** satisfy `C`'s prerequisite.
- A corequisite is satisfied by `taking(S,Q)` only.
- Generated KBs are acyclic; the demo KB's `CS401 <-> CS402` is a deliberate
  cycle used to exercise cycle detection.
````

- [ ] **Step 2: Run the full suite**

Run: `uv run pytest -q`
Expected: all tests pass (32 passed: 9 loader + 6 bridge + 12 engine + 5 generator)

- [ ] **Step 3: Smoke-test the CLI generator**

Run: `uv run python generate_kb.py 50 --seed 0`
Expected: prints `wrote 50 rules (seed=0) to data/generated/kb_50_seed0.json`

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: add README with setup, usage, and semantics"
```

---

## Self-Review

**Spec coverage** — every spec section maps to a task:
- Schema + demo KB → Task 1 (`kb_schema.md`, `data/knowledge_base.json`).
- Loader/validator + cycle detection → Task 2.
- Predicate bridge (R1–R6 / Horn clauses) → Task 3.
- Stub engine (backward chaining, unification, completion-vs-eligibility) → Task 4.
- Generator (deterministic, 50/100/250/500, acyclic) → Task 5.
- Documentation (`README.md`) → Task 6.
- Confirmed decisions (coreq=taking-only, acyclic benchmarks, one engine) are baked into the code and Global Constraints.

**Placeholder scan** — no TBD/TODO; every code step has complete code.

**Type consistency** — `load_kb`/`save_kb`/`validate_kb`/`detect_prereq_cycles` (Task 2) are consumed by Tasks 5–6 with matching signatures; `to_predicates`/`Var` (Task 3) consumed by Task 4; `backward_chain`/`prove` (Task 4) consumed by Task 6. Test helper `_demo()` uses the demo KB path consistently.
