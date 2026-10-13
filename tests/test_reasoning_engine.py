"""Focused tests for Deepak's symbolic reasoning algorithms."""

from reasoning_engine import backward_chain, backward_prove, forward_chain, forward_prove, substitute, unify
from to_predicates import Var


def kb(courses, completed=(), taking=(), waivers=()):
    return {"courses": {c: {"prerequisite": p, "corequisites": q}
                        for c, (p, q) in courses.items()},
            "students": {"s": {"completed": list(completed), "taking": list(taking),
                                "waivers": list(waivers)}}}


def test_no_prerequisite_and_unseen_identifiers():
    data = kb({"A": (None, [])})
    assert backward_chain(data, "new-student", "new-course")["eligible"] is False
    assert backward_chain(data, "s", "A")["eligible"] is True


def test_single_prerequisite_and_missing():
    data = kb({"A": ("B", []), "B": (None, [])}, completed=["B"])
    assert backward_chain(data, "s", "A")["eligible"] is True
    data["students"]["s"]["completed"] = []
    result = backward_chain(data, "s", "A")
    assert not result["eligible"] and result["missing_prerequisites"] == ["B"]


def test_and_and_or_semantics():
    data = kb({"A": ({"and": ["B", "C"]}, []), "B": (None, []), "C": (None, [])},
              completed=["B", "C"])
    assert backward_chain(data, "s", "A")["eligible"]
    data["students"]["s"]["completed"].remove("C")
    result = backward_chain(data, "s", "A")
    assert not result["eligible"] and result["missing_prerequisites"] == ["C"]
    data["courses"]["A"]["prerequisite"] = {"or": ["B", "C"]}
    assert backward_chain(data, "s", "A")["eligible"]
    data["students"]["s"]["completed"] = []
    assert not backward_chain(data, "s", "A")["eligible"]


def test_waiver_is_scoped_to_exact_target_and_prerequisite():
    data = kb({"A": ({"and": ["B", "C"]}, []), "X": ("C", []),
               "B": (None, []), "C": (None, [])},
              waivers=[{"course": "A", "prerequisite": "B"}])
    assert not backward_chain(data, "s", "A")["eligible"]
    assert not backward_chain(data, "s", "X")["eligible"]
    data["students"]["s"]["waivers"].append({"course": "A", "prerequisite": "C"})
    assert backward_chain(data, "s", "A")["eligible"]


def test_corequisite_uses_taking_only():
    data = kb({"A": (None, ["B"]), "B": (None, [])})
    assert not backward_chain(data, "s", "A")["eligible"]
    data["students"]["s"]["taking"] = ["B"]
    assert backward_chain(data, "s", "A")["eligible"]


def test_eligibility_does_not_imply_completion():
    data = kb({"A": ("B", []), "B": ("C", []), "C": (None, [])}, completed=["C"])
    assert backward_chain(data, "s", "B")["eligible"]
    result = backward_chain(data, "s", "A")
    assert not result["eligible"] and result["missing_prerequisites"] == ["B"]


def test_variable_bindings_carry_across_body_and_rule_uses_are_fresh():
    x, y = Var("X"), Var("Y")
    facts = [("parent", "a", "b"), ("parent", "b", "c"), ("tag", "c")]
    rules = [{"head": ("linked_tag", x), "body": [("parent", x, y), ("parent", y, Var("Z")), ("tag", Var("Z"))]}]
    answer = backward_prove(facts, rules, ("linked_tag", "a"))
    assert answer["proved"]
    assert substitute(x, unify(x, "a")) == "a"
    closure = forward_prove(facts, rules)
    assert closure["facts"].count(("linked_tag", "a")) == 1


def test_cycle_is_branch_local_and_terminates():
    x = Var("X")
    rules = [{"head": ("a", x), "body": [("b", x)]},
             {"head": ("b", x), "body": [("a", x)]},
             {"head": ("a", x), "body": [("base", x)]}]
    result = backward_prove([("base", "v")], rules, ("a", "v"))
    assert result["proved"] and any(line.startswith("CYCLE") for line in result["trace"])
    # The same goal reached in a completed sibling branch is not a cycle.
    branching = [{"head": ("goal", x), "body": [("base", x)]},
                 {"head": ("goal", x), "body": [("base", x)]}]
    sibling = backward_prove([("base", "v")], branching, ("goal", "v"))
    assert sibling["proved"] and not any(line.startswith("CYCLE") for line in sibling["trace"])


def test_forward_closure_is_idempotent_and_results_are_consistent():
    data = kb({"A": (None, []), "B": ("A", []), "C": ("B", [])})
    first = forward_chain(data, "s", "C")
    second = forward_chain(data, "s", "C")
    assert first["eligible"] == second["eligible"] is False
    satisfied = kb({"A": ("B", []), "B": (None, [])}, completed=["B"])
    assert forward_chain(satisfied, "s", "A")["eligible"]
    for result in (first, backward_chain(data, "s", "C")):
        assert {"eligible", "student_id", "course_id", "missing_prerequisites", "trace",
                "inference_steps", "rules_examined", "derived_facts"} <= result.keys()
        assert isinstance(result["inference_steps"], int)
