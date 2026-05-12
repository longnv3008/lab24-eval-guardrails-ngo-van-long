"""
phase-b/judge_pipeline.py
Pairwise swap-and-average judge + absolute 4-dimension scorer.
Run this script to generate pairwise_results.csv and absolute_scores.csv.

Compares v1 (basic RAG — top context only) vs v2 (production RAG with reranker).
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pandas as pd
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from config import OPENAI_API_KEY, JUDGE_MODEL
from rag_adapter import run_query

PAIRWISE_PROMPT = PromptTemplate.from_template("""
You are an impartial evaluator. Compare two answers to the same question.

Question: {question}

Answer A: {answer_a}

Answer B: {answer_b}

Rate based on:
- Factual accuracy (does it match known facts from Vietnamese financial/legal documents?)
- Relevance to the specific question asked
- Conciseness (no unnecessary padding or off-topic content)

Output JSON only (no markdown fences):
{{"winner": "A" or "B" or "tie", "reason": "one sentence max"}}
""")

ABSOLUTE_PROMPT = PromptTemplate.from_template("""
Score the following answer on 4 dimensions (each 1-5 scale):
1. accuracy (1=many errors, 5=fully accurate)
2. relevance (1=off-topic, 5=directly answers the question)
3. conciseness (1=verbose/padded, 5=appropriately brief)
4. helpfulness (1=confusing/unclear, 5=immediately actionable)

Question: {question}
Answer: {answer}

Output JSON only (no markdown fences):
{{"accuracy": int, "relevance": int, "conciseness": int, "helpfulness": int}}
""")


def _parse(text: str) -> dict:
    text = text.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"winner": "tie", "reason": "parse error",
                "accuracy": 3, "relevance": 3, "conciseness": 3, "helpfulness": 3}


def pairwise_judge(question: str, ans_a: str, ans_b: str, llm) -> dict:
    """Swap-and-average: run judge twice with swapped order, flip winner on run2."""
    def _call(a, b):
        p = PAIRWISE_PROMPT.format(question=question, answer_a=a, answer_b=b)
        return _parse(llm.invoke(p).content)

    r1 = _call(ans_a, ans_b)
    r2 = _call(ans_b, ans_a)

    # Flip r2 because A and B were swapped
    if r2.get("winner") == "A":
        r2["winner"] = "B"
    elif r2.get("winner") == "B":
        r2["winner"] = "A"

    final = r1["winner"] if r1["winner"] == r2["winner"] else "tie"
    return {
        "run1_winner": r1["winner"],
        "run1_reason": r1.get("reason", ""),
        "run2_winner": r2["winner"],
        "run2_reason": r2.get("reason", ""),
        "winner_after_swap": final,
    }


def absolute_score(question: str, answer: str, llm) -> dict:
    p = ABSOLUTE_PROMPT.format(question=question, answer=answer)
    parsed = _parse(llm.invoke(p).content)
    dims = ["accuracy", "relevance", "conciseness", "helpfulness"]
    parsed["overall"] = round(sum(parsed.get(d, 3) for d in dims) / 4, 2)
    return parsed


def build_pairs(questions: list[str]):
    """v1 = first retrieved context only; v2 = full RAG pipeline with reranker."""
    pairs = []
    for q in questions:
        answer_v2, contexts = run_query(q)
        # v1: use only the first context chunk as the naive baseline answer
        answer_v1 = contexts[0][:400] if contexts else "Khong tim thay thong tin."
        pairs.append({"question": q, "answer_a": answer_v1, "answer_b": answer_v2})
    return pairs


def main():
    testset = pd.read_csv(
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "phase-a", "testset_v1.csv")
    )
    questions = testset["question"].tolist()[:30]

    llm = ChatOpenAI(model=JUDGE_MODEL, api_key=OPENAI_API_KEY, temperature=0.0)
    pairs = build_pairs(questions)

    pairwise_rows, absolute_rows = [], []
    for i, pair in enumerate(pairs):
        print(f"[{i+1}/30] judging...")
        q, a, b = pair["question"], pair["answer_a"], pair["answer_b"]

        pw = pairwise_judge(q, a, b, llm)
        pairwise_rows.append({
            "question": q, "answer_a": a[:200], "answer_b": b[:200], **pw
        })

        ab_a = absolute_score(q, a, llm)
        ab_b = absolute_score(q, b, llm)
        absolute_rows.append({"question": q, "version": "v1", **ab_a})
        absolute_rows.append({"question": q, "version": "v2", **ab_b})

    base = os.path.dirname(__file__)
    pd.DataFrame(pairwise_rows).to_csv(
        os.path.join(base, "pairwise_results.csv"), index=False, encoding="utf-8-sig"
    )
    pd.DataFrame(absolute_rows).to_csv(
        os.path.join(base, "absolute_scores.csv"), index=False, encoding="utf-8-sig"
    )
    print("Saved pairwise_results.csv and absolute_scores.csv")


if __name__ == "__main__":
    main()
