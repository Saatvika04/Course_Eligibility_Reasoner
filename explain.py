"""Plain-English explanation of a course-eligibility verdict."""


def explain(kb, result):
    """Return a multi-line, human-readable justification for an engine result."""
    student_id = result["student_id"]
    course_id = result["course_id"]
    course = kb.get("courses", {}).get(course_id)
    student = kb.get("students", {}).get(student_id)

    if course is None:
        return f"{course_id} is not in the knowledge base, so it has no prerequisites to reason about."
    if student is None:
        return f"{student_id} has no recorded courses, so eligibility for {course_id} cannot be established."

    completed = set(student.get("completed", []))
    taking = set(student.get("taking", []))
    waivers = {(w["course"], w["prerequisite"]) for w in student.get("waivers", [])}

    verdict = "ELIGIBLE" if result["eligible"] else "NOT ELIGIBLE"
    lines = [f"{student_id} is {verdict} for {course_id}."]
    lines += _explain_prereq(course.get("prerequisite"), completed, taking, waivers, course_id)
    lines += _explain_coreqs(course.get("corequisites", []), taking)
    return "\n".join(lines)


def _satisfied(course_id, leaf, completed, waivers):
    return leaf in completed or (course_id, leaf) in waivers


def _explain_prereq(expr, completed, taking, waivers, course_id, indent="  "):
    if expr is None:
        return [indent + "Prerequisite: none required."]
    if isinstance(expr, str):
        if _satisfied(course_id, expr, completed, waivers):
            return [indent + f"Prerequisite {expr}: satisfied."]
        return [indent + f"Prerequisite {expr}: MISSING (not completed, no waiver)."]
    op = "and" if "and" in expr else "or"
    joiner = "all of" if op == "and" else "any of"
    lines = [indent + f"Prerequisite ({joiner}):"]
    for child in expr[op]:
        lines += _explain_prereq(child, completed, taking, waivers, course_id, indent + "  ")
    return lines


def _explain_coreqs(coreqs, taking):
    lines = []
    for q in coreqs:
        if q in taking:
            lines.append(f"  Corequisite {q}: satisfied (currently taking).")
        else:
            lines.append(f"  Corequisite {q}: MISSING (not currently taking).")
    return lines
