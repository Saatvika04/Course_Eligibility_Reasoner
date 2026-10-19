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
    eligible_rules = [r for r in pred["rules"] if r["head"][0] == "eligible" and r["head"][2] == "A"]
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
    eligible_rules = [r for r in pred["rules"] if r["head"][0] == "eligible" and r["head"][2] == "A"]
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
