# Course Eligibility Reasoner

Decides whether a student is eligible for a course from a knowledge base of
prerequisites (AND/OR), corequisites, waivers, and multi-step chains. All
modules are merged and tested together: the **knowledge-base module**
(Saatvika), the symbolic **reasoning engine** (Deepak), the
**evaluation / benchmark / CLI layer** (Mohammed), and the
**explainability + Streamlit UI** layer (Saatvika).

## Setup

```bash
uv venv
uv pip install -r requirements.txt
```

## Files

- `kb_loader.py` — load, validate, save, and cycle-detect a KB.
- `to_predicates.py` — expand domain JSON into facts + Horn-clause rules.
- `reasoning_engine.py` — forward + backward chaining engine.
- `explain.py` — plain-English explanation of an eligibility verdict.
- `app.py` — Streamlit web UI (verdict + explanation + trace).
- `generate_kb.py` — seeded generator for 50/100/250/500-rule KBs.
- `evaluate.py` — run labelled cases against both engines.
- `cli.py` — command-line eligibility query.
- `benchmark.py` — repeatable benchmark runner for generated KBs.
- `metrics.py` — result normalization and timing helpers.
- `plot_results.py` — benchmark plots.
- `evaluation_cases.py` — labelled correctness cases.
- `data/knowledge_base.json` — hand-written demo KB (has one deliberate cycle).
- `kb_schema.md` — schema definition and reasoning semantics.

## Usage

### Web UI

```bash
streamlit run app.py
```

### Command line

```bash
python cli.py bob CS301
```

### Python

```python
from kb_loader import load_kb
from reasoning_engine import backward_chain

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
