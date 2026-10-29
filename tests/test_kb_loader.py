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


def test_validate_rejects_unknown_expression_key():
    kb = {
        "courses": {
            "A": {"prerequisite": {"orr": ["B"]}, "corequisites": []},
            "B": {"prerequisite": None, "corequisites": []},
        },
        "students": {},
    }
    assert any("unknown key 'orr'" in e for e in validate_kb(kb))


def test_validate_rejects_empty_course_id():
    kb = {"courses": {"": {"prerequisite": None, "corequisites": []}}, "students": {}}
    assert any("course id must not be empty" in e for e in validate_kb(kb))


def test_validate_rejects_empty_student_id():
    kb = {
        "courses": {"A": {"prerequisite": None, "corequisites": []}},
        "students": {"": {"completed": [], "taking": [], "waivers": []}},
    }
    assert any("student id must not be empty" in e for e in validate_kb(kb))


def test_validate_rejects_self_corequisite():
    kb = {"courses": {"A": {"prerequisite": None, "corequisites": ["A"]}}, "students": {}}
    assert any("itself as a corequisite" in e for e in validate_kb(kb))


def test_validate_rejects_duplicate_corequisite():
    kb = {
        "courses": {
            "A": {"prerequisite": None, "corequisites": ["B", "B"]},
            "B": {"prerequisite": None, "corequisites": []},
        },
        "students": {},
    }
    assert any("more than once" in e for e in validate_kb(kb))


def test_save_and_load_roundtrip(tmp_path):
    kb = {"courses": {"A": {"prerequisite": None, "corequisites": []}}, "students": {}}
    p = tmp_path / "kb.json"
    save_kb(kb, str(p))
    assert load_kb(str(p)) == kb


def test_detect_prereq_cycles_finds_cycle():
    kb = {
        "courses": {
            "A": {"prerequisite": "B", "corequisites": []},
            "B": {"prerequisite": "A", "corequisites": []},
        },
        "students": {},
    }
    cycles = detect_prereq_cycles(kb)
    assert any(set(c) == {"A", "B"} for c in cycles)


def test_demo_kb_is_acyclic():
    kb = load_kb(DEMO)
    assert detect_prereq_cycles(kb) == []


def test_detect_prereq_cycles_none_when_acyclic():
    kb = {
        "courses": {
            "A": {"prerequisite": None, "corequisites": []},
            "B": {"prerequisite": "A", "corequisites": []},
        },
        "students": {},
    }
    assert detect_prereq_cycles(kb) == []
