"""Shared configuration for Lab 24."""
import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GROQ_API_KEY   = os.getenv("GROQ_API_KEY", "")
COHERE_API_KEY = os.getenv("COHERE_API_KEY", "")

DAY18_ROOT = os.path.join(os.path.dirname(__file__), "..", "Day18-Track3-Production-RAG")
DATA_DIR   = os.path.join(DAY18_ROOT, "data")

THRESHOLDS = {
    "faithfulness":      0.85,
    "answer_relevancy":  0.80,
    "context_precision": 0.70,
    "context_recall":    0.75,
}

JUDGE_MODEL = "gpt-4o-mini"
EMBED_MODEL  = "text-embedding-3-small"
