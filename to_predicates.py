"""Expand a validated knowledge base into ground facts and Horn-clause rules."""


class Var:
    """A logical variable used in rule heads and bodies."""

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.name

    def __eq__(self, other):
        return isinstance(other, Var) and other.name == self.name

    def __hash__(self):
        return hash(("Var", self.name))


S = Var("S")
C = Var("C")
P = Var("P")


def _to_dnf(expr):
    """Convert a prerequisite expression to disjunctive normal form.

    Returns a list of clauses; each clause is a list of leaf course ids that
    must ALL be satisfied. OR becomes multiple clauses; AND flattens into a
    single clause via the cartesian product of its children's clauses.
    """
    if isinstance(expr, str):
        return [[expr]]
    if "and" in expr:
        parts = [_to_dnf(child) for child in expr["and"]]
        clauses = [[]]
        for part in parts:
            clauses = [c + d for c in clauses for d in part]
        return clauses
    if "or" in expr:
        clauses = []
        for child in expr["or"]:
            clauses.extend(_to_dnf(child))
        return clauses
    return []  # unreachable for validated KBs


def to_predicates(kb):
    """Return {"facts": [...], "rules": [...]} for a validated knowledge base.

    Facts are tuples of constant strings, e.g. ("completed", "bob", "CS101").
    Rules are dicts {"head": (...), "body": [...]}; variables are Var objects.
    """
    facts = []
    rules = []
    courses = kb["courses"]
    students = kb["students"]

    for cid, course in courses.items():
        prereq = course["prerequisite"]
        coreqs = course.get("corequisites", [])

        for q in coreqs:
            facts.append(("coreq", cid, q))

        # corequisites satisfied only if every corequisite is being taken.
        rules.append({
            "head": ("coreqs_satisfied", S, cid),
            "body": [("taking", S, q) for q in coreqs],
        })

        if prereq is None:
            facts.append(("no_prereq", cid))
            rules.append({
                "head": ("eligible", S, cid),
                "body": [("no_prereq", cid), ("coreqs_satisfied", S, cid)],
            })
        elif isinstance(prereq, str):
            facts.append(("prereq", cid, prereq))
            rules.append({
                "head": ("eligible", S, cid),
                "body": [
                    ("prereq", cid, prereq),
                    ("prereq_satisfied", S, cid, prereq),
                    ("coreqs_satisfied", S, cid),
                ],
            })
        else:
            for clause in _to_dnf(prereq):
                body = [("prereq_satisfied", S, cid, p) for p in clause]
                body.append(("coreqs_satisfied", S, cid))
                rules.append({"head": ("eligible", S, cid), "body": body})

    # Global rules: how a single prerequisite is satisfied.
    rules.append({"head": ("prereq_satisfied", S, C, P), "body": [("waiver", S, C, P)]})
    rules.append({"head": ("prereq_satisfied", S, C, P), "body": [("completed", S, P)]})

    for sid, student in students.items():
        for c in student.get("completed", []):
            facts.append(("completed", sid, c))
        for c in student.get("taking", []):
            facts.append(("taking", sid, c))
        for w in student.get("waivers", []):
            facts.append(("waiver", sid, w["course"], w["prerequisite"]))

    return {"facts": facts, "rules": rules}
