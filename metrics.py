"""Timing and result-normalization helpers for the evaluation layer.

Counter definitions intentionally follow reasoning_engine.py:
- Backward inference_steps: number of goals entered, including cycle-rejected goals.
- Forward inference_steps: body-to-fact unification attempts.
- Backward rules_examined: candidate rule heads checked across goal expansions.
- Forward rules_examined: rule applications scanned across closure passes.
- Forward derived_facts: unique new facts added beyond the input facts.
- Backward derived_facts: None / not applicable (it proves a goal without closure).
"""

from statistics import mean, median
from time import perf_counter


_REQUIRED_FIELDS = (
    "eligible", "student_id", "course_id", "missing_prerequisites", "trace",
    "inference_steps", "rules_examined", "derived_facts",
)


def normalize_result(result, algorithm, student_id=None, course_id=None):
    """Return the shared result schema without changing the inference decision."""
    if not isinstance(result, dict):
        raise TypeError(f"{algorithm} engine must return a dict, got {type(result).__name__}")
    normalized = dict(result)
    normalized.setdefault("student_id", student_id)
    normalized.setdefault("course_id", course_id)
    normalized.setdefault("missing_prerequisites", [])
    normalized.setdefault("trace", [])
    normalized.setdefault("inference_steps", 0)
    normalized.setdefault("rules_examined", 0)
    normalized.setdefault("derived_facts", None)
    missing = [field for field in _REQUIRED_FIELDS if field not in normalized]
    if missing:
        raise ValueError(f"{algorithm} result missing required fields: {', '.join(missing)}")
    if not isinstance(normalized["eligible"], bool):
        raise TypeError(f"{algorithm} result field 'eligible' must be bool")
    for counter in ("inference_steps", "rules_examined"):
        value = normalized[counter]
        if not isinstance(value, (int, float)) or value < 0:
            raise ValueError(f"{algorithm} result field '{counter}' must be a non-negative number")
    if normalized["derived_facts"] is not None and (
        not isinstance(normalized["derived_facts"], (int, float)) or normalized["derived_facts"] < 0
    ):
        raise ValueError(f"{algorithm} result field 'derived_facts' must be non-negative or None")
    normalized["missing_prerequisites"] = sorted(set(normalized["missing_prerequisites"] or []))
    normalized["trace"] = list(normalized["trace"] or [])
    normalized["algorithm"] = algorithm
    return normalized


def measure_call(engine_fn, kb, student_id, course_id, repeats=3, algorithm="unknown"):
    """Execute an engine repeatedly, report timings, and return the last result.

    The engine result is checked for consistency across repeated runs. The
    median elapsed time is the primary reported runtime; mean/min/max and the
    individual timings are included for reproducibility.
    """
    if not isinstance(repeats, int) or repeats < 1:
        raise ValueError("repeats must be a positive integer")
    elapsed_ms = []
    results = []
    for _ in range(repeats):
        start = perf_counter()
        raw = engine_fn(kb, student_id, course_id)
        elapsed_ms.append((perf_counter() - start) * 1000.0)
        results.append(normalize_result(raw, algorithm, student_id, course_id))

    stable_fields = ("eligible", "missing_prerequisites", "inference_steps", "rules_examined", "derived_facts")
    baseline = results[0]
    for index, result in enumerate(results[1:], start=2):
        changed = [field for field in stable_fields if result.get(field) != baseline.get(field)]
        if changed:
            raise RuntimeError(
                f"{algorithm} returned inconsistent result fields across repeated runs; "
                f"run {index} differed in: {', '.join(changed)}"
            )

    return {
        "result": results[-1],
        "runtime_ms_median": median(elapsed_ms),
        "runtime_ms_mean": mean(elapsed_ms),
        "runtime_ms_min": min(elapsed_ms),
        "runtime_ms_max": max(elapsed_ms),
        "runtime_ms_runs": elapsed_ms,
        "repeats": repeats,
    }
