# Course Eligibility Reasoner — Saatvika's Module (+ Stub Engine) — Design

- **Date:** 2026-10-12
- **Owner:** Saatvika K (BCSE306L — Artificial Intelligence)
- **Scope:** Knowledge-base schema, sample KB, generator, loader/validator, predicate bridge, and a minimal stub engine to verify KBs standalone.

## 1. Context

The team project is a "Course Eligibility Reasoner" that decides, from a knowledge base of
prerequisites (AND/OR), corequisites, prerequisite-specific waivers, and multi-step
dependencies, whether a student is eligible for a course. Three owners:

- **Saatvika K** — knowledge-base schema + test-data generator (this module).
- **Deepak James** — core reasoning engine (Forward + Backward Chaining, unification, cycle detection).
- **Mohammed Wasif** — experiments, evaluation runner, and optional CLI/Streamlit/LLM interface.

The shared product must run Forward and Backward Chaining from scratch (no external inference
library), support variable substitution, detect cycles, explain decisions, report missing
prerequisites, and handle student/course pairs not hardcoded in examples. This module is
Saatvika's slice: it must produce a canonical, validated, documented knowledge base that
Deepak's engine and Mohammed's evaluation runner can consume without hand-editing.

## 2. Scope

In scope:

- Canonical domain-JSON knowledge-base schema.
- A hand-written demo KB covering every rule type (including one deliberate cycle).
- A deterministic generator for 50/100/250/500-rule KBs.
- A loader/validator that catches malformed expressions and unknown course references.
- A predicate bridge (`to_predicates`) that expands domain JSON into the fact/rule form (R1–R6).
- A minimal stub engine: backward-chaining prover with unification and active-path cycle detection.
- `pytest` tests for schema, loader, generator, bridge, and prover.
- `README.md` and `kb_schema.md` documentation.

Out of scope (owned by teammates):

- Forward chaining (Deepak).
- Full result/counter contract, benchmark timing, CSV/plots, CLI, Streamlit, and LLM parsing
  (Mohammed). The stub engine returns a minimal result shape only, for Saatvika's own verification.

## 3. Architecture

The module is layered so the domain JSON remains the canonical interchange format, while the
predicate form and prover are used internally by the stub engine (and serve as a documented
reference for Deepak):

```
domain JSON ──kb_loader.py──► validated KB ──to_predicates.py──► facts + R1–R6 rules ──stub_engine.py──► verdict + trace
```

- **Domain JSON** — canonical schema; hand-authored and generated. This is the interchange format
  handed to Deepak and Mohammed.
- **kb_loader.py** — loads and validates domain JSON.
- **to_predicates.py** — expands domain JSON into ground facts and general rules with variables.
- **stub_engine.py** — backward-chaining prover over the predicate form.

## 4. File layout

Flat modules at the project root, matching PRD naming so the team's files merge cleanly later.

```
course-eligibility-reasoner/
├── README.md
├── kb_schema.md
├── requirements.txt          # pytest only; no external inference library
├── .gitignore
├── data/
│   ├── knowledge_base.json   # hand-written demo KB (contains one deliberate cycle)
│   └── generated/            # 50/100/250/500 KBs, generated on demand (gitignored)
├── kb_loader.py
├── to_predicates.py
├── generate_kb.py
├── stub_engine.py
└── tests/
    ├── test_kb_loader.py
    ├── test_to_predicates.py
    ├── test_generate_kb.py
    └── test_stub_engine.py
```

## 5. Domain JSON schema (canonical interface)

```json
{
  "courses": {
    "BCSE201": {"prerequisite": null, "corequisites": []},
    "BCSE301": {"prerequisite": "BCSE201", "corequisites": []},
    "BCSE302": {"prerequisite": null, "corequisites": []},
    "BCSE401": {"prerequisite": {"and": ["BCSE301", "BCSE302"]}, "corequisites": ["BCSE402"]},
    "BCSE402": {"prerequisite": null, "corequisites": []}
  },
  "students": {
    "bob": {
      "completed": ["BCSE201", "BCSE301", "BCSE302"],
      "taking": ["BCSE402"],
      "waivers": [{"course": "BCSE401", "prerequisite": "BCSE302"}]
    }
  }
}
```

Field rules:

- `courses`: map of course id → `{prerequisite, corequisites}`.
- `prerequisite`: `null` | course id string | `{"and": [expr, ...]}` | `{"or": [expr, ...]}`.
  `and`/`or` arrays are non-empty and support arbitrary nesting.
- `corequisites`: list of course id strings (may be empty).
- `students`: map of student id → `{completed, taking, waivers}`.
- `completed`: list of course ids the student has finished.
- `taking`: list of course ids the student is currently enrolled in.
- `waivers`: list of `{course, prerequisite}` — a waiver scoped to `(student, target course, prerequisite)`.
- All course ids referenced anywhere (prerequisites, corequisites, `completed`, `taking`, waivers)
  must exist in `courses`.

## 6. Predicate bridge (`to_predicates`)

The bridge expands domain JSON into a predicate form matching the proposal's R1–R6. Output is a
dict with `facts` (list of ground facts) and `rules` (list of Horn clauses with variables).

Ground facts:

- `completed(student, course)`
- `taking(student, course)`
- `waiver(student, target_course, prerequisite)`
- `no_prereq(course)`
- `prereq(course, prerequisite)` (one fact per leaf prerequisite edge)
- `coreq(course, corequisite)`

Rule templates (variables `S`, `C`, `P`):

- R1: `eligible(S,C) :- no_prereq(C), coreqs_satisfied(S,C)`.
- R2: `eligible(S,C) :- prereq(C,P), prereq_satisfied(S,C,P), coreqs_satisfied(S,C)`.
- R5: `prereq_satisfied(S,C,P) :- waiver(S,C,P)`.
- R6: `prereq_satisfied(S,C,P) :- completed(S,P)`.
- R7: `coreqs_satisfied(S,C) :- coreq(C,Q), taking(S,Q)` (one clause per corequisite; all must hold).

Compilation of prerequisite expressions into Horn clauses:

- `null` → R1 (course has no prerequisite).
- single course id `P` → R2.
- `{"and": [e1, e2, ...]}` → one clause whose body is the conjunction of every child, each child
  compiled recursively; conjunctions flatten into additional `prereq_satisfied` body literals.
- `{"or": [e1, e2, ...]}` → one clause **per disjunct**; a disjunct that is itself an `and` becomes a
  clause whose body is the conjunction of that branch.

This compiles any nested AND/OR expression into a flat set of Horn clauses. The prover consumes
these clauses directly; it never interprets the JSON expression tree outside the rule set.

## 7. Stub engine semantics

The stub engine is a backward-chaining prover that answers `eligible(student, course)`. It uses
unification for the `S`/`C` variables and active-path cycle detection.

Correctness rules (must be preserved exactly):

1. **Eligibility is not completion.** A prerequisite `P` of course `C` is satisfied only by
   `completed(S,P)` or `waiver(S,C,P)`. A student's eligibility for `P` is never used to satisfy
   `C`'s prerequisite.
2. **AND** requires every child condition; **OR** requires at least one.
3. **Corequisite** `Q` of course `C` is satisfied by `taking(S,Q)` only (project policy).
4. **Cycle detection** uses the current recursion path. A repeated goal on the active path is
   reported as `"cycle detected"` and fails that branch (no infinite recursion). A repeated goal in
   a separate branch is not a cycle.
5. Missing prerequisites are collected and reported.

Result shape (minimal, for verification only; Mohammed owns the final contract):

```json
{
  "eligible": true,
  "student_id": "bob",
  "course_id": "BCSE401",
  "missing_prerequisites": [],
  "trace": ["..."],
  "inference_steps": 42
}
```

Forward chaining is intentionally omitted (Deepak's responsibility).

## 8. Generator (`generate_kb(n, seed=0)`)

- Deterministic: uses `random.Random(seed)` so the same `(n, seed)` produces byte-identical data.
- `n` is the number of **courses** (each course is one rule). Generator targets the requested count
  exactly and records it in the output (`"requested_rule_count": n`).
- Each course's `prerequisite` is drawn deterministically from: `null`, single id, `{"and": [...]}`,
  or `{"or": [...]}`; corequisites are added occasionally; a subset of students get `completed` /
  `taking` / `waivers` facts.
- Multi-step chains are produced by having some prerequisites reference earlier courses.
- **Benchmark KBs are acyclic** (deterministic timing for Mohammed's scalability runs). The
  hand-written demo KB carries the single deliberate cycle for cycle tests.
- Output includes `"seed"` and `"requested_rule_count"` for reproducibility and Mohammed's reporting.

## 9. Validator (`kb_loader.py`)

Rejects before inference:

- Unknown course ids referenced in prerequisites, corequisites, `completed`, `taking`, or waivers.
- Malformed prerequisite expressions (not `null`, string, or well-formed `and`/`or`; empty
  `and`/`or` arrays).
- Duplicate course or student ids.
- Waivers referencing an unknown student, target course, or prerequisite.
- Wrong top-level shape or missing required fields.

Errors are collected and reported with clear messages (course id + field) so a bad KB is fixed
before it reaches the engine.

## 10. Testing

- Framework: `pytest`; single command `pytest`.
- `tests/test_kb_loader.py` — valid KB loads; each malformed case is rejected.
- `tests/test_generate_kb.py` — reproducibility (same `(n, seed)` → identical), all four sizes
  (50/100/250/500), every rule type present, no dangling references.
- `tests/test_to_predicates.py` — bridge emits the expected facts/rules for a known KB.
- `tests/test_stub_engine.py` — single prereq, AND, OR, missing prereq, waiver changes verdict,
  corequisite pass/fail, multi-step chain, cycle terminates with "cycle detected", unseen
  student/course query, and the completion-vs-eligibility distinction.

## 11. Documentation

- `README.md` — how to load, generate, and verify KBs; one command to run all tests.
- `kb_schema.md` — field definitions, assumptions, examples, and the reasoning semantics.

## 12. Confirmed decisions

1. **Corequisite satisfaction** = `taking(S,Q)` only (matches PRD policy).
2. **Benchmark KBs acyclic**; the demo KB carries the one deliberate cycle.
3. **"All three" approaches combined** into the layered design: domain JSON (canonical schema) +
   `to_predicates` (bridge) + mini prover (stub engine). There is one engine, not two redundant ones.

## 13. Handoff interfaces (for teammates)

- Deepak consumes the **domain JSON** (canonical). The predicate bridge and stub engine are a
  documented reference for how domain JSON maps to R1–R6, not a required interchange format.
- Mohammed consumes the **domain JSON** plus generator options `(n, seed)` and the
  `requested_rule_count`/`seed` metadata; the stub engine's result shape is informational, not the
  final contract.
