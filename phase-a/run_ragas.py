"""
phase-a/run_ragas.py
Runs RAGAS evaluation (4 metrics) on testset_v1.csv using the Day18 RAG pipeline.
Saves ragas_results.csv and ragas_summary.json.

Usage:
    python phase-a/run_ragas.py
Requirements:
    OPENAI_API_KEY in environment (or .env file)
    Day18 RAG pipeline (Qdrant) running for live eval;
    falls back to mock responses automatically.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pandas as pd
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
from langchain_openai import ChatOpenAI
from config import OPENAI_API_KEY
from rag_adapter import run_query


def main():
    testset_path = os.path.join(os.path.dirname(__file__), "testset_v1.csv")
    df = pd.read_csv(testset_path)
    print(f"Loaded {len(df)} test questions")

    results_data = []
    for i, row in df.iterrows():
        print(f"[{i+1}/{len(df)}] {str(row['question'])[:60]}...")
        answer, contexts = run_query(str(row["question"]))
        if isinstance(contexts, str):
            import ast
            try:
                contexts = ast.literal_eval(contexts)
            except Exception:
                contexts = [contexts]
        results_data.append({
            "question":     str(row["question"]),
            "answer":       answer,
            "contexts":     contexts,
            "ground_truth": str(row["ground_truth"]),
        })

    dataset = Dataset.from_list(results_data)
    scores = evaluate(
        dataset,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
        llm=ChatOpenAI(model="gpt-4o-mini", api_key=OPENAI_API_KEY),
    )

    results_df = scores.to_pandas()
    out_csv = os.path.join(os.path.dirname(__file__), "ragas_results.csv")
    results_df.to_csv(out_csv, index=False, encoding="utf-8-sig")
    print(f"\nSaved → {out_csv}")

    summary = {
        "faithfulness":      float(scores["faithfulness"]),
        "answer_relevancy":  float(scores["answer_relevancy"]),
        "context_precision": float(scores["context_precision"]),
        "context_recall":    float(scores["context_recall"]),
    }
    out_json = os.path.join(os.path.dirname(__file__), "ragas_summary.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"Summary: {summary}")
    print(f"Saved → {out_json}")


if __name__ == "__main__":
    main()
