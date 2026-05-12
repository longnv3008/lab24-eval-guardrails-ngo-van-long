"""
phase-b/kappa_analysis.py
Computes Cohen's kappa between human labels and LLM judge.
Produces bias_analysis.png with position + length bias charts.
"""
import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import cohen_kappa_score

base = os.path.dirname(__file__)


def kappa_analysis():
    human_df = pd.read_csv(os.path.join(base, "human_labels.csv"))
    judge_df  = pd.read_csv(os.path.join(base, "pairwise_results.csv"))

    human_labels = human_df["human_winner"].tolist()[:10]
    judge_labels  = judge_df["winner_after_swap"].tolist()[:10]

    kappa = cohen_kappa_score(human_labels, judge_labels)

    if kappa < 0:
        interp = "WORSE than chance — systematic judge error"
    elif kappa < 0.2:
        interp = "Slight — unreliable"
    elif kappa < 0.4:
        interp = "Fair — weak"
    elif kappa < 0.6:
        interp = "Moderate — usable for monitoring"
    elif kappa < 0.8:
        interp = "Substantial — production-ready"
    else:
        interp = "Almost perfect"

    print(f"Cohen's kappa: {kappa:.3f}")
    print(f"Interpretation: {interp}")

    if kappa < 0.6:
        print("\n[!] kappa < 0.6 -- root cause analysis:")
        print("  Main driver: length bias (B answers tend to be longer = more detailed)")
        print("  Human prefers specific line-number citations; judge may prefer verbosity")
        print("  Mitigation: truncate answers to 300 chars before judging")

    return kappa, interp


def position_bias(judge_df):
    a_wins_first = (judge_df["run1_winner"] == "A").sum()
    total = len(judge_df)
    rate = a_wins_first / total
    print(f"\nPosition bias: A wins as first-listed: {a_wins_first}/{total} = {rate:.1%}")
    print(f"  Expected ~50% if unbiased. >55% = position bias.")
    return rate


def length_bias(judge_df):
    df = judge_df.copy()
    df["len_a"] = df["answer_a"].str.len()
    df["len_b"] = df["answer_b"].str.len()
    df["len_diff"] = df["len_b"] - df["len_a"]

    b_wins_longer = ((df["winner_after_swap"] == "B") & (df["len_diff"] > 0)).sum()
    b_total_longer = (df["len_diff"] > 0).sum()
    rate = b_wins_longer / b_total_longer if b_total_longer > 0 else 0.0
    print(f"Length bias: B wins when longer: {b_wins_longer}/{b_total_longer} = {rate:.1%}")
    print(f"  Expected ~50% if unbiased. >60% = length bias.")
    return rate


def plot_biases(pos_rate: float, len_rate: float):
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))

    axes[0].bar(["A wins (listed first)", "Fair baseline"],
                [pos_rate * 100, 50], color=["#e74c3c", "#95a5a6"])
    axes[0].set_ylim(0, 100)
    axes[0].set_title("Position Bias\n(A win rate when listed first in run1)")
    axes[0].set_ylabel("Win Rate (%)")
    axes[0].axhline(55, color="orange", linestyle="--", linewidth=1.5, label="Bias threshold (55%)")
    axes[0].legend(fontsize=8)
    for bar, val in zip(axes[0].patches, [pos_rate * 100, 50]):
        axes[0].text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                     f"{val:.1f}%", ha="center", va="bottom", fontsize=9)

    axes[1].bar(["B wins (longer)", "Fair baseline"],
                [len_rate * 100, 50], color=["#3498db", "#95a5a6"])
    axes[1].set_ylim(0, 100)
    axes[1].set_title("Length Bias\n(B win rate when B answer is longer)")
    axes[1].set_ylabel("Win Rate (%)")
    axes[1].axhline(60, color="orange", linestyle="--", linewidth=1.5, label="Bias threshold (60%)")
    axes[1].legend(fontsize=8)
    for bar, val in zip(axes[1].patches, [len_rate * 100, 50]):
        axes[1].text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                     f"{val:.1f}%", ha="center", va="bottom", fontsize=9)

    plt.tight_layout()
    out = os.path.join(base, "bias_analysis.png")
    plt.savefig(out, dpi=120, bbox_inches="tight")
    print(f"\nBias chart saved: {out}")


def main():
    kappa, interp = kappa_analysis()
    judge_df = pd.read_csv(os.path.join(base, "pairwise_results.csv"))
    pos_rate = position_bias(judge_df)
    len_rate  = length_bias(judge_df)
    plot_biases(pos_rate, len_rate)
    print(f"\nSummary: kappa={kappa:.3f} ({interp}), pos_bias={pos_rate:.1%}, len_bias={len_rate:.1%}")


if __name__ == "__main__":
    main()
