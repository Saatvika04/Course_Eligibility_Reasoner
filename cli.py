"""Command-line eligibility query using the project's existing reasoning engine."""

import argparse
import os
import sys

from kb_loader import detect_prereq_cycles, load_kb
from reasoning_engine import backward_chain, forward_chain

ALGORITHMS = {
    "forward": forward_chain,
    "backward": backward_chain,
}


def show_result(result, algorithm, kb=None, show_trace=True, trace_limit=100):
    verdict = "ELIGIBLE" if result["eligible"] else "NOT ELIGIBLE"
    print("\n" + "=" * 68)
    print(f"Course eligibility: {verdict}")
    print(f"Student: {result['student_id']}    Course: {result['course_id']}")
    print(f"Algorithm: {algorithm.title()}")
    missing = result.get("missing_prerequisites") or []
    print("Missing prerequisites (engine result): " + (", ".join(missing) if missing else "None reported"))
    missing_corequisites = []
    if kb is not None and result.get("course_id") in kb.get("courses", {}):
        course = kb["courses"][result["course_id"]]
        student = kb.get("students", {}).get(result.get("student_id"), {})
        taking = set(student.get("taking", []))
        missing_corequisites = [q for q in course.get("corequisites", []) if q not in taking]
    print("Missing corequisites (not currently taken): " +
          (", ".join(missing_corequisites) if missing_corequisites else "None"))
    print("Inference steps: " + str(result.get("inference_steps", "N/A")))
    print("Rules examined: " + str(result.get("rules_examined", "N/A")))
    derived = result.get("derived_facts")
    print("Derived facts: " + ("N/A for backward chaining" if derived is None else str(derived)))
    if show_trace:
        trace = result.get("trace") or []
        print("\nReasoning trace:")
        if not trace:
            print("  (No trace was returned by the engine.)")
        else:
            for line in trace[:trace_limit]:
                print(f"  {line}")
            if len(trace) > trace_limit:
                print(f"  ... {len(trace) - trace_limit} additional trace lines omitted")
    print("=" * 68)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("student", help="student identifier, e.g. bob")
    parser.add_argument("course", help="course identifier, e.g. CS301")
    parser.add_argument("--algorithm", choices=("forward", "backward", "both"), default="both")
    parser.add_argument("--kb", default=os.path.join("data", "knowledge_base.json"),
                        help="path to knowledge-base JSON (default: data/knowledge_base.json)")
    parser.add_argument("--no-trace", action="store_true", help="hide the reasoning trace")
    parser.add_argument("--trace-limit", type=int, default=100, help="maximum trace lines per result")
    args = parser.parse_args(argv)
    if args.trace_limit < 1:
        parser.error("--trace-limit must be at least 1")
    try:
        kb = load_kb(args.kb)
    except (OSError, ValueError) as exc:
        print(f"Could not load knowledge base: {exc}", file=sys.stderr)
        return 2

    if args.course not in kb.get("courses", {}):
        print(f"Note: course '{args.course}' is not in the knowledge base; verdicts are expected to be NOT ELIGIBLE.")
    if args.student not in kb.get("students", {}):
        print(f"Note: student '{args.student}' has no stored facts in this knowledge base.")

    # Report a relevant structural prerequisite cycle in the KB. This diagnostic
    # is separate from the eligibility result, whose prerequisite semantics are
    # based on completed courses (not recursively inferred eligibility).
    if args.course in kb.get("courses", {}):
        relevant_cycles = [cycle for cycle in detect_prereq_cycles(kb) if args.course in cycle]
        for cycle in relevant_cycles:
            print("Knowledge-base prerequisite cycle detected: " + " -> ".join(cycle))

    algorithms = ALGORITHMS if args.algorithm == "both" else {args.algorithm: ALGORITHMS[args.algorithm]}
    for algorithm, engine_fn in algorithms.items():
        try:
            result = engine_fn(kb, args.student, args.course)
            show_result(result, algorithm, kb=kb, show_trace=not args.no_trace, trace_limit=args.trace_limit)
        except Exception as exc:  # keep one bad engine result from hiding the other algorithm's output
            print(f"{algorithm.title()} chaining failed: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
