"""Load, validate, and save knowledge-base JSON files."""

import json


def load_kb(path):
    """Load and validate a knowledge base from a JSON file.

    Raises ValueError if the file is missing required fields or contains
    invalid references. Returns the parsed dict on success.
    """
    with open(path, "r", encoding="utf-8") as f:
        kb = json.load(f)
    errors = validate_kb(kb)
    if errors:
        raise ValueError("invalid knowledge base:\n- " + "\n- ".join(errors))
    return kb


def save_kb(kb, path):
    """Write a knowledge base to a JSON file (indented, stable key order)."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(kb, f, indent=2, ensure_ascii=False)
        f.write("\n")


def validate_kb(kb):
    """Return a list of human-readable errors; empty list means valid."""
    errors = []
    if not isinstance(kb, dict):
        return ["knowledge base must be a JSON object"]
    courses = kb.get("courses")
    students = kb.get("students")
    if not isinstance(courses, dict):
        errors.append("'courses' must be an object mapping course id -> course")
    if not isinstance(students, dict):
        errors.append("'students' must be an object mapping student id -> student")
    if not isinstance(courses, dict) or not isinstance(students, dict):
        return errors

    course_ids = set(courses.keys())

    for cid in courses:
        if cid == "":
            errors.append("course id must not be empty")
    for sid in students:
        if sid == "":
            errors.append("student id must not be empty")

    for cid, course in courses.items():
        if not isinstance(course, dict):
            errors.append(f"course '{cid}' must be an object")
            continue
        errors.extend(_validate_expr(course.get("prerequisite"), course_ids, f"course '{cid}' prerequisite"))
        coreqs = course.get("corequisites", [])
        if not isinstance(coreqs, list):
            errors.append(f"course '{cid}' corequisites must be a list")
        else:
            seen = set()
            for q in coreqs:
                if not isinstance(q, str):
                    errors.append(f"course '{cid}' corequisite must be a course id string")
                elif q not in course_ids:
                    errors.append(f"course '{cid}' corequisite '{q}' is unknown")
                elif q == cid:
                    errors.append(f"course '{cid}' lists itself as a corequisite")
                elif q in seen:
                    errors.append(f"course '{cid}' lists corequisite '{q}' more than once")
                else:
                    seen.add(q)

    for sid, student in students.items():
        if not isinstance(student, dict):
            errors.append(f"student '{sid}' must be an object")
            continue
        for field in ("completed", "taking"):
            lst = student.get(field, [])
            if not isinstance(lst, list):
                errors.append(f"student '{sid}' {field} must be a list")
                continue
            for c in lst:
                if not isinstance(c, str):
                    errors.append(f"student '{sid}' {field} must contain course id strings")
                elif c not in course_ids:
                    errors.append(f"student '{sid}' {field} references unknown course '{c}'")
        waivers = student.get("waivers", [])
        if not isinstance(waivers, list):
            errors.append(f"student '{sid}' waivers must be a list")
            continue
        for w in waivers:
            if not isinstance(w, dict):
                errors.append(f"student '{sid}' has a non-object waiver")
                continue
            target = w.get("course")
            prereq = w.get("prerequisite")
            if not isinstance(target, str) or target not in course_ids:
                errors.append(f"student '{sid}' waiver target '{target}' is unknown")
            if not isinstance(prereq, str) or prereq not in course_ids:
                errors.append(f"student '{sid}' waiver prerequisite '{prereq}' is unknown")

    return errors


def _validate_expr(expr, course_ids, path):
    """Validate a prerequisite expression; return a list of errors."""
    errors = []
    if expr is None:
        return errors
    if isinstance(expr, str):
        if expr not in course_ids:
            errors.append(f"{path} references unknown course '{expr}'")
        return errors
    if isinstance(expr, dict):
        keys = list(expr)
        if len(keys) != 1 or keys[0] not in ("and", "or"):
            unknown = [k for k in keys if k not in ("and", "or")]
            if unknown:
                errors.append(f"{path} has unknown key '{unknown[0]}'; expected only 'and' or 'or'")
            else:
                errors.append(f"{path} must contain exactly one 'and' or 'or' key")
            return errors
        op = keys[0]
        children = expr[op]
        if not isinstance(children, list) or len(children) == 0:
            errors.append(f"{path} '{op}' must be a non-empty list")
            return errors
        for i, child in enumerate(children):
            errors.extend(_validate_expr(child, course_ids, f"{path} {op}[{i}]"))
        return errors
    errors.append(f"{path} must be null, a course id string, or an 'and'/'or' object")
    return errors


def _leaves(expr):
    """Return the set of course ids referenced by a prerequisite expression."""
    if expr is None:
        return set()
    if isinstance(expr, str):
        return {expr}
    out = set()
    for child in expr.get("and", expr.get("or", [])):
        out |= _leaves(child)
    return out


def detect_prereq_cycles(kb):
    """Return a list of prerequisite cycles, each a list of course ids.

    A cycle is a loop in the prerequisite graph, e.g. A requires B and B
    requires A. Each cycle is reported as a list starting and ending at the
    same course. Assumes kb is already validated.
    """
    courses = kb["courses"]
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {cid: WHITE for cid in courses}
    cycles = []
    stack = []

    def dfs(cid):
        color[cid] = GRAY
        stack.append(cid)
        for p in sorted(_leaves(courses[cid]["prerequisite"])):
            if p not in color:
                continue
            if color[p] == GRAY:
                idx = stack.index(p)
                cycles.append(stack[idx:] + [p])
            elif color[p] == WHITE:
                dfs(p)
        stack.pop()
        color[cid] = BLACK

    for cid in courses:
        if color[cid] == WHITE:
            dfs(cid)
    return cycles
