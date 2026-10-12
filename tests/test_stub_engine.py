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
