"""
phase-a/failure_cluster.py
Identifies bottom-10 questions by average score across 4 RAGAS metrics.
Prints cluster analysis table.
"""
import os
import pandas as pd

METRICS = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]


def main():
    df = pd.read_csv(os.path.join(os.path.dirname(__file__), "ragas_results.csv"))
    df["avg_score"] = df[METRICS].mean(axis=1)
    bottom10 = df.nsmallest(10, "avg_score")
    print("Bottom 10 questions by average RAGAS score:")
    print(bottom10[["question", "evolution_type", "faithfulness",
                     "answer_relevancy", "context_precision",
                     "context_recall", "avg_score"]].to_string(index=False))

    print("\nScore by evolution type:")
    print(df.groupby("evolution_type")[METRICS + ["avg_score"]].mean().round(3).to_string())


if __name__ == "__main__":
    main()
