"""Show the existing backward_prove active-path cycle guard on recursive rules.

This is a low-level predicate-rule demonstration. Domain prerequisite cycles
are also reported by cli.py, but under the project's semantics a prerequisite
is satisfied by completion/waiver rather than recursively proving eligibility.
"""

from reasoning_engine import backward_prove
from to_predicates import Var


def main():
    student = Var("S")
    rules = [
        {"head": ("eligible_demo", student), "body": [("requires_demo", student)]},
        {"head": ("requires_demo", student), "body": [("eligible_demo", student)]},
    ]
    proof = backward_prove([], rules, ("eligible_demo", "bob"))
    print("Backward-chaining cycle-guard demonstration")
    print("Goal: eligible_demo(bob)")
    for line in proof["trace"]:
        print(f"  {line}")
    print(f"Proved: {proof['proved']}")
    print(f"Inference steps: {proof['inference_steps']}")
    print(f"Rules examined: {proof['rules_examined']}")
    if not any(line.startswith("CYCLE") for line in proof["trace"]):
        raise SystemExit("ERROR: expected a cycle marker in the proof trace")
    print("Cycle detected; recursion terminated correctly.")


if __name__ == "__main__":
    main()
