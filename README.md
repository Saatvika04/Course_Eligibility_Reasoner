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
