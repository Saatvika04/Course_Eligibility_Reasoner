"""Independent, labelled cases for evaluating the existing reasoning engine.

The expected verdicts below are specified from the project KB semantics, not
from the engine's output. All cases use one shared, validated knowledge base.
"""

from copy import deepcopy


_CASE_KB = {
    "courses": {
        "INTRO": {"prerequisite": None, "corequisites": []},
        "BASE": {"prerequisite": None, "corequisites": []},
        "SINGLE": {"prerequisite": "BASE", "corequisites": []},
        "AND_A": {"prerequisite": None, "corequisites": []},
        "AND_B": {"prerequisite": None, "corequisites": []},
        "AND_TARGET": {"prerequisite": {"and": ["AND_A", "AND_B"]}, "corequisites": []},
        "OR_A": {"prerequisite": None, "corequisites": []},
        "OR_B": {"prerequisite": None, "corequisites": []},
        "OR_TARGET": {"prerequisite": {"or": ["OR_A", "OR_B"]}, "corequisites": []},
        "OR_MISSING_A": {"prerequisite": None, "corequisites": []},
        "OR_MISSING_B": {"prerequisite": None, "corequisites": []},
        "OR_MISSING_TARGET": {"prerequisite": {"or": ["OR_MISSING_A", "OR_MISSING_B"]}, "corequisites": []},
        "COREQ_Q": {"prerequisite": None, "corequisites": []},
        "COREQ_TARGET": {"prerequisite": None, "corequisites": ["COREQ_Q"]},
        "COREQ_M": {"prerequisite": None, "corequisites": []},
        "COREQ_MISSING_TARGET": {"prerequisite": None, "corequisites": ["COREQ_M"]},
        "WAIVER_PREREQ": {"prerequisite": None, "corequisites": []},
        "WAIVER_TARGET": {"prerequisite": "WAIVER_PREREQ", "corequisites": []},
        "WAIVER_OTHER_TARGET": {"prerequisite": "WAIVER_PREREQ", "corequisites": []},
        "CHAIN_BASE": {"prerequisite": None, "corequisites": []},
        "CHAIN_MID": {"prerequisite": "CHAIN_BASE", "corequisites": []},
        "CHAIN_TOP": {"prerequisite": "CHAIN_MID", "corequisites": []},
        "CYCLE_A": {"prerequisite": "CYCLE_B", "corequisites": []},
        "CYCLE_B": {"prerequisite": "CYCLE_A", "corequisites": []},
    },
    "students": {
        "case_student": {
            "completed": ["BASE", "AND_A", "AND_B", "OR_A", "CHAIN_BASE", "CHAIN_MID"],
            "taking": ["COREQ_Q"],
            "waivers": [{"course": "WAIVER_TARGET", "prerequisite": "WAIVER_PREREQ"}],
        },
        "partial_student": {
            "completed": ["AND_A"],
            "taking": [],
            "waivers": [],
        },
        "chain_student": {
            "completed": ["CHAIN_BASE"],
            "taking": [],
            "waivers": [],
        },
    },
}

# id, purpose/scenario, student, course, independently labelled expected verdict
LABELLED_CASES = [
    {"id": "T01", "scenario": "course without prerequisites", "student": "case_student", "course": "INTRO", "expected_eligible": True},
    {"id": "T02", "scenario": "single prerequisite satisfied", "student": "case_student", "course": "SINGLE", "expected_eligible": True},
    {"id": "T03", "scenario": "AND prerequisites all satisfied", "student": "case_student", "course": "AND_TARGET", "expected_eligible": True},
    {"id": "T04", "scenario": "AND prerequisite missing", "student": "partial_student", "course": "AND_TARGET", "expected_eligible": False},
    {"id": "T05", "scenario": "OR prerequisite satisfied by one branch", "student": "case_student", "course": "OR_TARGET", "expected_eligible": True},
    {"id": "T06", "scenario": "both OR branches missing", "student": "case_student", "course": "OR_MISSING_TARGET", "expected_eligible": False},
    {"id": "T07", "scenario": "corequisite is being taken", "student": "case_student", "course": "COREQ_TARGET", "expected_eligible": True},
    {"id": "T08", "scenario": "corequisite not being taken", "student": "case_student", "course": "COREQ_MISSING_TARGET", "expected_eligible": False},
    {"id": "T09", "scenario": "target-specific waiver applies", "student": "case_student", "course": "WAIVER_TARGET", "expected_eligible": True},
    {"id": "T10", "scenario": "waiver does not transfer to another target course", "student": "case_student", "course": "WAIVER_OTHER_TARGET", "expected_eligible": False},
    {"id": "T11", "scenario": "middle course in a prerequisite chain", "student": "chain_student", "course": "CHAIN_MID", "expected_eligible": True},
    {"id": "T12", "scenario": "eligibility is not the same as completion", "student": "chain_student", "course": "CHAIN_TOP", "expected_eligible": False},
    {"id": "T13", "scenario": "completed intermediate prerequisite", "student": "case_student", "course": "CHAIN_TOP", "expected_eligible": True},
    {"id": "T14", "scenario": "cyclic prerequisite component with no completed dependency", "student": "case_student", "course": "CYCLE_A", "expected_eligible": False},
    {"id": "T15", "scenario": "unseen student-course pair with no prerequisites", "student": "new_student", "course": "INTRO", "expected_eligible": True},
    {"id": "T16", "scenario": "unknown course query", "student": "case_student", "course": "COURSE_DOES_NOT_EXIST", "expected_eligible": False},
]


def build_evaluation_kb():
    """Return a fresh copy so test runs cannot mutate the labelled fixture."""
    return deepcopy(_CASE_KB)


def get_labelled_cases():
    """Return a fresh list of independent expected-verdict labels."""
    return deepcopy(LABELLED_CASES)
