"""
scripts/run_eval.py — CI/CD gate script.
Reads ragas_summary.json and exits 1 if any metric < threshold.

Usage:
    python scripts/run_eval.py
    python scripts/run_eval.py --threshold faithfulness=0.85 answer_relevancy=0.80
    python scripts/run_eval.py --results path/to/ragas_summary.json
"""
import argparse
import json
import sys
import os

DEFAULTS = {
    "faithfulness":      0.85,
    "answer_relevancy":  0.80,
    "context_precision": 0.70,
    "context_recall":    0.75,
}


def parse_thresholds(args):
    thresholds = dict(DEFAULTS)
    for t in args:
        k, v = t.split("=")
        thresholds[k.strip()] = float(v.strip())
    return thresholds


def main():
    parser = argparse.ArgumentParser(description="RAGAS eval gate for CI/CD")
    parser.add_argument("--threshold", nargs="+", default=[],
                        help="Metric thresholds e.g. faithfulness=0.85")
    parser.add_argument("--results", default="phase-a/ragas_summary.json",
                        help="Path to ragas_summary.json")
    opts = parser.parse_args()

    thresholds = parse_thresholds(opts.threshold)

    if not os.path.exists(opts.results):
        print(f"ERROR: results file not found: {opts.results}")
        sys.exit(1)

    with open(opts.results, encoding="utf-8") as f:
        scores = json.load(f)

    failed = []
    print(f"\n{'Metric':<25} {'Score':>8} {'Threshold':>10} {'Status':>8}")
    print("-" * 55)
    for metric, threshold in thresholds.items():
        score = scores.get(metric, 0.0)
        status = "PASS" if score >= threshold else "FAIL"
        if score < threshold:
            failed.append(f"{metric}: {score:.3f} < {threshold}")
        print(f"{metric:<25} {score:>8.3f} {threshold:>10.3f} {status:>8}")

    print()
    if failed:
        print(f"[GATE FAIL] {len(failed)} metric(s) below threshold:")
        for item in failed:
            print(f"  - {item}")
        sys.exit(1)
    else:
        print("[GATE PASS] All metrics above thresholds.")
        sys.exit(0)


if __name__ == "__main__":
    main()
