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
