from explain import explain
from kb_loader import load_kb
from reasoning_engine import backward_chain


def test_explain_eligible_chain():
    kb = load_kb("data/knowledge_base.json")
    result = backward_chain(kb, "carol", "DS301")
    text = explain(kb, result)
    assert "ELIGIBLE" in text
    assert "DS201" in text
    assert "satisfied" in text.lower()


def test_explain_not_eligible_missing_prereq():
    kb = load_kb("data/knowledge_base.json")
    result = backward_chain(kb, "dave", "CS301")
    text = explain(kb, result)
    assert "NOT ELIGIBLE" in text
    assert "CS202" in text
    assert "MISSING" in text


def test_explain_corequisite_reported():
    kb = load_kb("data/knowledge_base.json")
    result = backward_chain(kb, "ivan", "CS204")  # CS204 coreq CS203, ivan not taking it
    text = explain(kb, result)
    assert "CS203" in text
    assert "taking" in text.lower()


def test_explain_unknown_course():
    kb = load_kb("data/knowledge_base.json")
    result = backward_chain(kb, "carol", "DOES_NOT_EXIST")
    text = explain(kb, result)
    assert "not in the knowledge base" in text
