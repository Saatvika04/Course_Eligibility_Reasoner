"""Generate deterministic synthetic knowledge bases at a requested rule count."""

import argparse
import os
import random

from kb_loader import save_kb


def generate_kb(n, seed=0):
    """Return a synthetic knowledge base with n courses (one rule each).

    Prerequisites always reference earlier courses, so the resulting graph is
    acyclic. The same (n, seed) always produces identical data.
    """
    rng = random.Random(seed)
    courses = {}
    for i in range(n):
        cid = f"C{i:03d}"
        courses[cid] = {
            "prerequisite": _choose_prereq(rng, i),
            "corequisites": _choose_coreqs(rng, i),
        }
    students = _generate_students(rng, n)
    return {
        "courses": courses,
        "students": students,
        "seed": seed,
        "requested_rule_count": n,
    }


def _choose_prereq(rng, i):
    if i == 0:
        return None
    earlier = [f"C{j:03d}" for j in range(i)]
    r = rng.random()
    if r < 0.15:
        return None
    if r < 0.55 or i < 2:
        return rng.choice(earlier)
    if r < 0.80:
        a, b = rng.sample(earlier, 2)
        return {"and": [a, b]}
    a, b = rng.sample(earlier, 2)
    return {"or": [a, b]}


def _choose_coreqs(rng, i):
    if i >= 1 and rng.random() < 0.2:
        return [f"C{rng.randrange(i):03d}"]
    return []


def _generate_students(rng, n):
    ids = [f"C{i:03d}" for i in range(n)]
    students = {}
    for s in range(5):
        k = rng.randint(0, min(n, 10))
        completed = rng.sample(ids, k) if k else []
        taking = [rng.choice(ids)] if rng.random() < 0.5 else []
        waivers = []
        for _ in range(rng.randint(0, 2)):
            waivers.append({
                "course": rng.choice(ids),
                "prerequisite": rng.choice(ids),
            })
        students[f"student{s}"] = {
            "completed": completed,
            "taking": taking,
            "waivers": waivers,
        }
    return students


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate a synthetic course-eligibility KB.")
    parser.add_argument("n", type=int, help="number of courses (rules)")
    parser.add_argument("--seed", type=int, default=0, help="random seed (default 0)")
    parser.add_argument("--out-dir", default="data/generated", help="output directory")
    args = parser.parse_args(argv)

    kb = generate_kb(args.n, seed=args.seed)
    os.makedirs(args.out_dir, exist_ok=True)
    path = os.path.join(args.out_dir, f"kb_{args.n}_seed{args.seed}.json")
    save_kb(kb, path)
    print(f"wrote {args.n} rules (seed={args.seed}) to {path}")


if __name__ == "__main__":
    main()
