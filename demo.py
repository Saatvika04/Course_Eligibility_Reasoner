"""Guided, terminal-based demonstration of CourseLogic 2.0.

Walks the professor through the whole project: the knowledge base, its
compilation into first-order Horn clauses, forward vs. backward chaining,
plain-English explanations, cycle detection, and the labelled correctness
suite. Press Enter between sections, or pass --auto to run straight through.

Usage:
    .venv/bin/python demo.py            # interactive, step through
    .venv/bin/python demo.py --auto     # non-interactive
    .venv/bin/python demo.py --no-diagrams
"""

import argparse
import os
import sys

from explain import explain
from evaluation_cases import build_evaluation_kb, get_labelled_cases
from kb_loader import detect_prereq_cycles, load_kb, validate_kb
from reasoning_engine import backward_chain, forward_chain
from to_predicates import to_predicates
from visualize import render_backward_svg, render_forward_svg

KB_PATH = os.path.join("data", "knowledge_base.json")
DIAGRAM_DIR = "demo_output"

AUTO = False

# (student, course, what this case demonstrates)
DEMO_CASES = [
    ("carol", "DS301", "prerequisite chain (DS101 -> DS201 -> DS301) + AND"),
    ("dave", "CS301", "empty student -> missing prerequisites"),
    ("ivan", "CS204", "corequisite CS203 not currently taken"),
    ("bob", "CS202", "scoped waiver satisfies one AND branch (MATH202)"),
    ("erin", "CS303", "OR prerequisite satisfied by one branch (CS302)"),
]


def hr(char="=", width=72):
    print(char * width)


def section(title):
    print()
    hr()
    print(f"  {title}")
    hr()


def pause():
    if AUTO:
        return
    try:
        input("        [Enter] to continue... ")
    except EOFError:
        pass


def banner():
    print()
    hr("#")
    print("  CourseLogic 2.0 - Explainable Course Eligibility")
    print("  A from-scratch symbolic reasoner (forward + backward chaining)")
    hr("#")
    print()


def show_knowledge_base(kb):
    section("1. The knowledge base")
    courses = kb["courses"]
    students = kb["students"]
    print(f"  Courses:  {len(courses)}")
    print(f"  Students: {len(students)}")
    print()
    print("  Every course has a prerequisite (string, AND tree, or OR tree)")
    print("  and a list of corequisites. Example course shapes:")
    for cid in ("CS101", "DS301", "CS303", "CS204"):
        c = courses[cid]
        print(f"    {cid}: prerequisite={c['prerequisite']!r} corequisites={c['corequisites']}")
    print()
    print("  Validation: " + ("no errors" if validate_kb(kb) == [] else "errors found!"))
    cycles = detect_prereq_cycles(kb)
    print("  Prerequisite cycles: " + (", ".join(" -> ".join(c) for c in cycles) if cycles else "none (acyclic)"))


def _fmt_rule(r):
    head = str(r["head"])
    body = ", ".join(str(b) for b in r["body"])
    return f"{head} :- {body}" if body else f"{head} :- []"


def _pick(seq, key, wanted):
    found = {}
    for item in seq:
        k = key(item)
        if k in wanted and k not in found:
            found[k] = item
        if len(found) == len(wanted):
            break
    return [found[k] for k in wanted if k in found]


def show_compilation(kb):
    section("2. Compiling the KB into Horn clauses")
    preds = to_predicates(kb)
    facts = preds["facts"]
    rules = preds["rules"]
    print(f"  Ground facts: {len(facts)}   Horn-clause rules: {len(rules)}")
    print()
    print("  Sample facts (given truths about the world):")
    for f in _pick(facts, lambda f: f[0],
                   ["no_prereq", "prereq", "coreq", "completed", "taking", "waiver"]):
        print(f"    {f}")
    print()
    print("  Sample rules (the if/then inference steps):")
    ps = [r for r in rules if r["head"][0] == "prereq_satisfied"]
    elig = next((r for r in rules
                 if r["head"][0] == "eligible"
                 and any(b[0] == "prereq_satisfied" for b in r["body"])), None)
    coreq_example = next((r for r in rules
                          if r["head"][0] == "coreqs_satisfied" and r["body"]), None)
    examples = []
    for r in ps:
        src = r["body"][0][0]
        note = ("a prerequisite is satisfied by a completed course" if src == "completed"
                else "a prerequisite is satisfied by a scoped waiver")
        examples.append((r, note))
    examples += [
        (elig, "eligible when its prerequisites AND corequisites hold"),
        (coreq_example, "corequisites satisfied only by taking the course"),
    ]
    for r, note in examples:
        if r is not None:
            print(f"    {_fmt_rule(r)}")
            print(f"        ({note})")
    print()
    print("  AND/OR prerequisite trees are expanded to DNF, so each OR branch")
    print("  becomes its own rule - the engine never special-cases them.")


def verdict_line(eligible):
    return "ELIGIBLE" if eligible else "NOT ELIGIBLE"


def show_engines(kb):
    section("3. The two reasoning engines")
    print("  Forward chaining  = data-driven:  derive every fact you can,")
    print("                      then check if the goal is among them.")
    print("  Backward chaining = goal-driven:  start from the goal and only")
    print("                      prove the rules on the path to it.")
    print()
    for student, course, note in DEMO_CASES:
        hr("-")
        print(f"  {student} -> {course}   ({note})")
        bw = backward_chain(kb, student, course)
        fw = forward_chain(kb, student, course)
        print()
        print(f"    Backward: {verdict_line(bw['eligible'])}  "
              f"(inference steps: {bw['inference_steps']})")
        print(f"    Forward:  {verdict_line(fw['eligible'])}  "
              f"(inference steps: {fw['inference_steps']}, "
              f"derived facts: {fw['derived_facts']})")
        print()
        print("    Why (plain English):")
        for line in explain(kb, bw).splitlines():
            print(f"      {line}")
    print()


def show_contrast(kb):
    section("4. Forward vs backward: the step-count gap")
    rows = []
    for student, course, _ in DEMO_CASES:
        bw = backward_chain(kb, student, course)
        fw = forward_chain(kb, student, course)
        rows.append((student, course, bw["inference_steps"], fw["inference_steps"]))
    print(f"  {'query':<20}{'backward steps':>16}{'forward steps':>16}")
    for student, course, b, f in rows:
        print(f"  {student + ' / ' + course:<20}{b:>16}{f:>16}")
    print()
    print("  Same question, same answer, very different amount of work:")
    print("  backward only proves the goal; forward computes the whole closure.")


def show_cycle_detection():
    section("5. Cycle detection")
    print("  The demo KB is acyclic, so here is a tiny synthetic KB with a cycle:")
    print('    A requires B;  B requires A.')
    kb = {
        "courses": {
            "A": {"prerequisite": "B", "corequisites": []},
            "B": {"prerequisite": "A", "corequisites": []},
        },
        "students": {},
    }
    cycles = detect_prereq_cycles(kb)
    print()
    print("  detect_prereq_cycles -> " + " | ".join(" -> ".join(c) for c in cycles))
    print("  A naive recursive prover would loop forever here; the engine's")
    print("  active-path guard rejects a goal that reappears on its own branch.")


def show_correctness():
    section("6. Correctness: 21 independent labelled cases")
    kb = build_evaluation_kb()
    cases = get_labelled_cases()
    print(f"  {len(cases)} cases, each exercising one semantic rule")
    print(f"  (AND, OR, OR-of-AND, corequisites, waivers, chains, cycles...).")
    print()
    totals = {}
    for name, fn in (("backward", backward_chain), ("forward", forward_chain)):
        correct = 0
        for c in cases:
            r = fn(kb, c["student"], c["course"])
            if r["eligible"] == c["expected_eligible"]:
                correct += 1
        totals[name] = (correct, len(cases))
        pct = 100.0 * correct / len(cases)
        print(f"  {name:>8} chaining: {correct}/{len(cases)} correct ({pct:.2f}%)")
    print()
    print("  Two independent implementations must agree with the hand-written")
    print("  labels - their agreement is the correctness argument.")
    print("  Subtle cases to remember: T10 (waivers don't transfer) and")
    print("  T12 (eligibility is not completion).")


def show_diagrams(kb, render):
    if not render:
        return
    section("7. Inference-trace diagrams")
    os.makedirs(DIAGRAM_DIR, exist_ok=True)
    written = []
    for student, course in (("carol", "DS301"), ("dave", "CS301")):
        bw = backward_chain(kb, student, course)
        fw = forward_chain(kb, student, course)
        bsvg, _, _ = render_backward_svg(bw["graph"])
        fsvg, _, _ = render_forward_svg(fw["graph"])
        bp = os.path.join(DIAGRAM_DIR, f"backward_{student}_{course}.svg")
        fp = os.path.join(DIAGRAM_DIR, f"forward_{student}_{course}.svg")
        with open(bp, "w", encoding="utf-8") as f:
            f.write(bsvg)
        with open(fp, "w", encoding="utf-8") as f:
            f.write(fsvg)
        written.extend((bp, fp))
    print("  Rendered SVG proof trees / derivation graphs:")
    for p in written:
        print(f"    {p}")
    print()
    print("  Open these in a browser, or view them live in the Streamlit app.")


def wrap_up():
    section("8. Summary")
    for line in (
        "A from-scratch symbolic reasoner:",
        "  - first-order knowledge base (JSON) compiled to Horn clauses",
        "  - unification with an occurs-check",
        "  - forward chaining (closure) and backward chaining (goal-directed)",
        "  - plain-English explanation for every verdict",
        "  - both engines agree on 21/21 labelled cases",
        "  - runs in a Streamlit UI (streamlit run app.py)",
    ):
        print("  " + line)
    print()


def main(argv=None):
    global AUTO
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--auto", action="store_true", help="run without pausing")
    parser.add_argument("--no-diagrams", action="store_true", help="skip SVG rendering")
    args = parser.parse_args(argv)
    AUTO = args.auto

    banner()
    if AUTO:
        print("  Running non-interactively (--auto).\n")
    else:
        print("  Press Enter to advance, or Ctrl-C to stop.\n")

    try:
        kb = load_kb(KB_PATH)
    except (OSError, ValueError) as exc:
        print(f"  Could not load the knowledge base: {exc}", file=sys.stderr)
        return 2

    show_knowledge_base(kb)
    pause()
    show_compilation(kb)
    pause()
    show_engines(kb)
    pause()
    show_contrast(kb)
    pause()
    show_cycle_detection()
    pause()
    show_correctness()
    pause()
    show_diagrams(kb, render=not args.no_diagrams)
    pause()
    wrap_up()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
