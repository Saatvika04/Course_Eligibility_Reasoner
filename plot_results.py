"""Generate reproducible benchmark plots from benchmark_results.csv."""

import argparse
import csv
import os
from collections import defaultdict
from statistics import median


def generate_plots(csv_path="results/benchmark_results.csv", out_dir="results"):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise RuntimeError("matplotlib is required for plots; run: python -m pip install matplotlib") from exc

    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Benchmark CSV not found: {csv_path}. Run `python evaluate.py --mode benchmark` first.")

    grouped = defaultdict(list)
    with open(csv_path, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            grouped[(int(row["rule_count"]), row["algorithm"])].append(row)
    if not grouped:
        raise ValueError(f"No benchmark rows found in {csv_path}")

    rule_counts = sorted({key[0] for key in grouped})
    algorithms = sorted({key[1] for key in grouped})
    metrics = [
        ("elapsed_ms", "Median execution time (ms)", "runtime", True),
        ("inference_steps", "Inference steps (engine-defined count)", "steps", True),
        ("rules_examined", "Rules examined (engine-defined count)", "rules_examined", False),
    ]
    os.makedirs(out_dir, exist_ok=True)
    outputs = []
    for field, ylabel, suffix, log_scale in metrics:
        fig, ax = plt.subplots(figsize=(8, 5))
        for algorithm in algorithms:
            values = []
            x = []
            for size in rule_counts:
                rows = grouped.get((size, algorithm), [])
                if rows:
                    x.append(size)
                    values.append(median(float(row[field]) for row in rows))
            if x:
                ax.plot(x, values, marker="o", label=algorithm.title())
        ax.set_xlabel("Number of predicate rules in benchmark KB")
        ax.set_ylabel(ylabel)
        ax.set_title(f"Course Eligibility Reasoner: {ylabel}")
        if log_scale:
            ax.set_yscale("log")
            ax.set_ylabel(ylabel + " (log scale)")
        ax.grid(True, alpha=0.3, which="both")
        ax.legend()
        fig.tight_layout()
        path = os.path.join(out_dir, f"benchmark_{suffix}.png")
        fig.savefig(path, dpi=160)
        plt.close(fig)
        outputs.append(path)
    return outputs


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", default="results/benchmark_results.csv")
    parser.add_argument("--out-dir", default="results")
    args = parser.parse_args(argv)
    for path in generate_plots(args.csv, args.out_dir):
        print(f"Wrote plot: {path}")


if __name__ == "__main__":
    main()
