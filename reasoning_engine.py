"""Symbolic forward and backward chaining for the project's predicate KB.

The public functions accept the domain JSON KB and return a stable result
shape. Predicate-level helpers are intentionally public enough for small rule
sets to be tested independently.
"""

from itertools import product

from to_predicates import Var, to_predicates


def _is_var(term):
    return isinstance(term, Var)


def _walk(term, bindings):
    seen = set()
    while _is_var(term) and term in bindings and term not in seen:
        seen.add(term)
        term = bindings[term]
    return term


def _occurs(var, term, bindings):
    return _walk(term, bindings) == var


def unify(left, right, bindings=None):
    """Unify two terms, returning a new substitution or ``None`` on failure."""
    result = dict(bindings or {})
    left, right = _walk(left, result), _walk(right, result)
    if left == right:
        return result
    if _is_var(left):
        if _occurs(left, right, result):
            return None
        result[left] = right
        return result
    if _is_var(right):
        if _occurs(right, left, result):
            return None
        result[right] = left
        return result
    if isinstance(left, tuple) and isinstance(right, tuple) and len(left) == len(right):
        for a, b in zip(left, right):
            result = unify(a, b, result)
            if result is None:
                return None
        return result
    return None


def substitute(term, bindings):
    """Apply a substitution recursively to a term or predicate tuple."""
    term = _walk(term, bindings)
    if isinstance(term, tuple):
        return tuple(substitute(item, bindings) for item in term)
    return term


def _fresh_rule(rule, serial):
    mapping = {}

    def fresh(term):
        if not _is_var(term):
            return term
        if term not in mapping:
            mapping[term] = Var(f"{term.name}__{serial}")
        return mapping[term]

    return {
        "head": tuple(fresh(t) for t in rule["head"]),
        "body": [tuple(fresh(t) for t in pred) for pred in rule["body"]],
    }


def _ground(pred, bindings):
    return substitute(tuple(pred), bindings)


def backward_prove(facts, rules, goal):
    """Prove a predicate goal with depth-first backward chaining.

    Active-path keys are local to the current branch. ``inference_steps`` is
    the number of goals entered, including goals rejected as cycles;
    ``rules_examined`` counts candidate rule heads inspected. Backward
    eligibility results have ``derived_facts=None`` because this algorithm
    does not build a closure.
    """
    state = {"steps": 0, "rules": 0, "trace": [], "active": [], "failed_goals": []}

    def solve(current_goal, bindings):
        state["steps"] += 1
        goal = _ground(current_goal, bindings)
        key = goal
        if key in state["active"]:
            state["trace"].append(f"CYCLE {goal}")
            return []
        state["trace"].append(f"GOAL {goal}")
        answers = []
        for fact in facts:
            merged = unify(goal, tuple(fact), bindings)
            if merged is not None:
                state["trace"].append(f"FACT {fact}")
                answers.append(merged)
        state["active"].append(key)
        try:
            for index, rule in enumerate(rules):
                state["rules"] += 1
                candidate = _fresh_rule(rule, state["rules"])
                merged = unify(goal, candidate["head"], bindings)
                if merged is None:
                    continue
                state["trace"].append(f"RULE {candidate['head']} :- {candidate['body']}")
                partials = [merged]
                for body_goal in candidate["body"]:
                    next_partials = []
                    for partial in partials:
                        next_partials.extend(solve(body_goal, partial))
                    partials = next_partials
                    if not partials:
                        break
                answers.extend(partials)
        finally:
            state["active"].pop()
        if not answers:
            state["trace"].append(f"FAIL {goal}")
            state["failed_goals"].append(goal)
        return answers

    answers = solve(tuple(goal), {})
    return {"proved": bool(answers), "substitutions": answers,
            "trace": state["trace"], "inference_steps": state["steps"],
            "rules_examined": state["rules"], "failed_goals": state["failed_goals"]}


def forward_prove(facts, rules, position_domains=None):
    """Compute a least fixed point by repeatedly matching rule bodies.

    ``position_domains`` optionally constrains otherwise-unbound head
    variables by predicate argument position; it keeps universal rules over
    the KB's finite values from deriving irrelevant cross-domain tuples.
    Here ``inference_steps`` counts body-to-fact unification attempts,
    ``rules_examined`` counts each rule once per closure pass, and
    ``derived_facts`` counts unique facts added beyond the input facts.
    """
    position_domains = position_domains or {}
    known = list(dict.fromkeys(tuple(f) for f in facts))
    known_set = set(known)
    # Datalog rules may contain universally quantified head variables which
    # do not occur in the body (the project's completion rule has this form).
    # Ground those variables over the finite constants in the current KB.
    constants = list(dict.fromkeys(term for fact in known for term in fact[1:]
                                   if not _is_var(term)))
    trace = [f"FACT {fact}" for fact in known]
    steps = rules_examined = 0
    serial = 0
    while True:
        additions = []
        for rule in rules:
            rules_examined += 1
            serial += 1
            candidate = _fresh_rule(rule, serial)
            partials = [{}]
            for body_goal in candidate["body"]:
                matched = []
                for partial in partials:
                    for fact in known:
                        steps += 1
                        binding = unify(body_goal, fact, partial)
                        if binding is not None:
                            matched.append(binding)
                partials = matched
                if not partials:
                    break
            for binding in partials:
                unresolved = []
                variable_domains = {}
                for position, term in enumerate(candidate["head"]):
                    term = _walk(term, binding)
                    if _is_var(term) and term not in unresolved:
                        unresolved.append(term)
                        restricted = position_domains.get(candidate["head"][0], {}).get(position)
                        variable_domains[term] = list(restricted) if restricted is not None else constants
                assignments = (product(*(variable_domains[var] for var in unresolved))
                               if unresolved else [()])
                for values in assignments:
                    completed_binding = dict(binding)
                    completed_binding.update(zip(unresolved, values))
                    derived = _ground(candidate["head"], completed_binding)
                    if derived not in known_set:
                        known_set.add(derived)
                        additions.append(derived)
                        trace.append(f"DERIVE {derived} by {candidate['head']} :- {candidate['body']}")
        if not additions:
            break
        known.extend(additions)
    return {"facts": known, "trace": trace, "inference_steps": steps,
            "rules_examined": rules_examined, "derived_facts": len(known) - len(set(tuple(f) for f in facts))}


def _result(kb, student_id, course_id, eligible, missing, trace, steps, rules_examined, derived_facts=None):
    course = kb.get("courses", {}).get(course_id, {})
    student = kb.get("students", {}).get(student_id, {})
    taking = set(student.get("taking", []))
    missing_corequisites = sorted(q for q in course.get("corequisites", []) if q not in taking)
    return {"eligible": eligible, "student_id": student_id, "course_id": course_id,
            "missing_prerequisites": sorted(missing),
            "missing_corequisites": missing_corequisites,
            "trace": trace, "inference_steps": steps, "rules_examined": rules_examined,
            "derived_facts": derived_facts}


def backward_chain(kb, student_id, course_id):
    """Determine eligibility using goal-directed backward chaining."""
    predicates = to_predicates(kb)
    proof = backward_prove(predicates["facts"], predicates["rules"],
                           ("eligible", student_id, course_id))
    missing = set()
    if not proof["proved"]:
        for goal in proof["failed_goals"]:
            if len(goal) == 4 and goal[0] == "prereq_satisfied":
                missing.add(goal[3])
    return _result(kb, student_id, course_id, proof["proved"], missing,
                   proof["trace"], proof["inference_steps"], proof["rules_examined"])


def forward_chain(kb, student_id, course_id):
    """Determine eligibility by saturating facts with forward rule applications."""
    predicates = to_predicates(kb)
    students = [student_id]
    courses = list(kb.get("courses", {}))
    domains = {
        "eligible": {1: students, 2: courses},
        "coreqs_satisfied": {1: students, 2: courses},
        "prereq_satisfied": {2: courses},
    }
    closure = forward_prove(predicates["facts"], predicates["rules"], domains)
    target = ("eligible", student_id, course_id)
    eligible = target in closure["facts"]
    missing = set()
    if not eligible:
        student = kb.get("students", {}).get(student_id, {})
        course = kb.get("courses", {}).get(course_id, {})
        completed = set(student.get("completed", []))
        waivers = {(w["course"], w["prerequisite"]) for w in student.get("waivers", [])}

        def leaves(expr):
            if isinstance(expr, str):
                return {expr}
            if isinstance(expr, dict):
                children = expr.get("and", expr.get("or", []))
                sets = [leaves(child) for child in children]
                return set.union(*sets) if sets else set()
            return set()
        candidates = leaves(course.get("prerequisite"))
        missing = {p for p in candidates if p not in completed and (course_id, p) not in waivers}
        trace = closure["trace"] + [f"NO DERIVED FACT {target}"]
    else:
        trace = closure["trace"] + [f"PROVED {target}"]
    return _result(kb, student_id, course_id, eligible, missing, trace,
                   closure["inference_steps"], closure["rules_examined"], closure["derived_facts"])
