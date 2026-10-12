"""Minimal backward-chaining prover (stub engine) for verifying a KB."""

from to_predicates import to_predicates, Var


def _is_var(term):
    return isinstance(term, Var)


def _subst(term, subst):
    while _is_var(term) and term.name in subst:
        term = subst[term.name]
    return term


def _unify(x, y, subst):
    if subst is None:
        return None
    x = _subst(x, subst)
    y = _subst(y, subst)
    if x == y:
        return dict(subst)
    if _is_var(x):
        out = dict(subst)
        out[x.name] = y
        return out
    if _is_var(y):
        out = dict(subst)
        out[y.name] = x
        return out
    return None


def _unify_tuple(goal, pattern, subst):
    if len(goal) != len(pattern):
        return None
    for a, b in zip(goal, pattern):
        subst = _unify(a, b, subst)
        if subst is None:
            return None
    return subst


def _fmt(pred):
    return f"{pred[0]}({', '.join(str(t) for t in pred[1:])})"


_fresh_id = [0]


def _freshen(rule):
    """Return a copy of rule with every variable renamed to a fresh variable.

    Rules share the module-level Var objects (S, C, P). Without freshening,
    a binding made while proving one body literal would leak into a later
    literal that reuses the same variable name. Fresh names per application
    avoid that collision.
    """
    mapping = {}

    def fresh(v):
        if v.name not in mapping:
            _fresh_id[0] += 1
            mapping[v.name] = Var(f"_{v.name}{_fresh_id[0]}")
        return mapping[v.name]

    def term(t):
        return fresh(t) if _is_var(t) else t

    return {
        "head": tuple(term(t) for t in rule["head"]),
        "body": [tuple(term(t) for t in lit) for lit in rule["body"]],
    }


def _prove(goal, subst, facts, rules, state):
    """Return (success, subst). state tracks steps, trace, missing, active path."""
    state["steps"] += 1
    goal = tuple(_subst(t, subst) for t in goal)
    key = tuple(t.name if _is_var(t) else t for t in goal)

    if key in state["active_path"]:
        state["trace"].append(f"  CYCLE {_fmt(goal)}")
        return False, subst

    state["active_path"].append(key)
    state["trace"].append(f"GOAL {_fmt(goal)}")
    try:
        for fact in facts:
            u = _unify_tuple(goal, fact, subst)
            if u is not None:
                state["trace"].append(f"  FACT {_fmt(fact)}")
                return True, u

        for rule in rules:
            rule = _freshen(rule)
            u = _unify_tuple(goal, rule["head"], subst)
            if u is None:
                continue
            state["trace"].append(
                f"  RULE {_fmt(rule['head'])} :- {', '.join(_fmt(b) for b in rule['body'])}"
            )
            cur = u
            ok = True
            for lit in rule["body"]:
                ok, cur = _prove(lit, cur, facts, rules, state)
                if not ok:
                    break
            if ok:
                return True, cur

        if goal and goal[0] == "prereq_satisfied" and len(goal) == 4 and all(not _is_var(t) for t in goal):
            state["missing"].add(goal[3])
        state["trace"].append(f"  FAIL {_fmt(goal)}")
        return False, subst
    finally:
        state["active_path"].pop()


def prove(facts, rules, goal):
    """Prove a single goal against a fact/rule set. Returns a result dict."""
    state = {"steps": 0, "trace": [], "missing": set(), "active_path": []}
    ok, _ = _prove(goal, {}, facts, rules, state)
    return {
        "eligible": ok,
        "missing_prerequisites": sorted(state["missing"]),
        "trace": state["trace"],
        "inference_steps": state["steps"],
    }


def backward_chain(kb, student_id, course_id):
    """Answer eligible(student_id, course_id) and return a result dict."""
    pred = to_predicates(kb)
    result = prove(pred["facts"], pred["rules"], ("eligible", student_id, course_id))
    result["student_id"] = student_id
    result["course_id"] = course_id
    return result
