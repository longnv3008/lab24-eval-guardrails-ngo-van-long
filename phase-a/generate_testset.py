"""
phase-a/generate_testset.py
Generates 50 synthetic Q/A pairs using RAGAS TestsetGenerator from Day18 docs.
Saves testset_v1.csv with columns: question, ground_truth, contexts, evolution_type
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from ragas.testset import TestsetGenerator
from ragas.testset.evolutions import simple, reasoning, multi_context
from langchain_community.document_loaders import TextLoader
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from config import DATA_DIR, OPENAI_API_KEY


def main():
    docs = []
    for fname in sorted(os.listdir(DATA_DIR)):
        if fname.endswith(".md"):
            fpath = os.path.join(DATA_DIR, fname)
            loader = TextLoader(fpath, encoding="utf-8")
            loaded = loader.load()
            docs.extend(loaded)
            print(f"  Loaded {fname}: {len(loaded)} doc(s)")
    print(f"Total: {len(docs)} documents")

    generator = TestsetGenerator.from_langchain(
        generator_llm=ChatOpenAI(model="gpt-4o-mini", api_key=OPENAI_API_KEY),
        critic_llm=ChatOpenAI(model="gpt-4o-mini", api_key=OPENAI_API_KEY),
        embeddings=OpenAIEmbeddings(api_key=OPENAI_API_KEY),
    )

    testset = generator.generate_with_langchain_docs(
        documents=docs,
        test_size=50,
        distributions={simple: 0.5, reasoning: 0.25, multi_context: 0.25},
    )

    df = testset.to_pandas()
    # Ensure required columns exist
    for col in ["question", "ground_truth", "contexts", "evolution_type"]:
        if col not in df.columns:
            df[col] = ""

    out = os.path.join(os.path.dirname(__file__), "testset_v1.csv")
    df[["question", "ground_truth", "contexts", "evolution_type"]].to_csv(
        out, index=False, encoding="utf-8-sig"
    )
    print(f"\nSaved {len(df)} rows → {out}")
    print(df["evolution_type"].value_counts().to_string())


if __name__ == "__main__":
    main()
