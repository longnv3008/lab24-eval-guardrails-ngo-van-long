"""
phase-c/full_pipeline.py
Full async guardrail stack:
  L1 (PII + topic injection check) → L2 (RAG pipeline) → L3 (Llama Guard) → L4 (async audit)

Also includes latency benchmark over 100 queries.
"""
import sys, os, asyncio, time, json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import importlib.util
import pandas as pd
import numpy as np


def _load_local(name, relpath):
    path = os.path.join(os.path.dirname(__file__), relpath)
    spec = importlib.util.spec_from_file_location(name, path)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ig = _load_local("input_guard",  "input_guard.py")
og = _load_local("output_guard", "output_guard.py")

pii_guard   = ig.PIIGuard()
topic_guard = ig.TopicGuard()
out_guard   = og.OutputGuard()

REFUSE_MSG = (
    "Xin loi, toi khong the xu ly yeu cau nay. "
    "Vui long dat cau hoi ve tai chinh hoac bao ve du lieu ca nhan."
)

_audit_log: list[dict] = []


async def _audit_async(user_input: str, answer: str, timings: dict, blocked: bool):
    _audit_log.append({
        "ts":      time.time(),
        "input":   user_input[:100],
        "answer":  answer[:100],
        "timings": timings,
        "blocked": blocked,
    })


async def guarded_pipeline(user_input: str) -> tuple[str, dict]:
    """Full guardrail pipeline. Returns (answer, latency_breakdown_ms)."""
    timings: dict[str, float] = {}

    # L1: Input guards (sync, fast)
    t0 = time.perf_counter()
    sanitized, _ = pii_guard.sanitize(user_input)
    topic_ok, topic_reason = topic_guard.check(sanitized)
    timings["L1_ms"] = round((time.perf_counter() - t0) * 1000, 1)

    if not topic_ok:
        asyncio.create_task(_audit_async(user_input, REFUSE_MSG, timings, True))
        return REFUSE_MSG, timings

    # L2: RAG pipeline
    t0 = time.perf_counter()
    try:
        from rag_adapter import run_query
        answer, _ = run_query(sanitized)
    except Exception as e:
        answer = f"RAG unavailable: {e}"
    timings["L2_ms"] = round((time.perf_counter() - t0) * 1000, 1)

    # L3: Output guard (async-compatible, sync here)
    t0 = time.perf_counter()
    is_safe, _, _ = out_guard.check(sanitized, answer)
    timings["L3_ms"] = round((time.perf_counter() - t0) * 1000, 1)

    if not is_safe:
        asyncio.create_task(_audit_async(user_input, REFUSE_MSG, timings, True))
        return REFUSE_MSG, timings

    # L4: Fire-and-forget audit
    asyncio.create_task(_audit_async(user_input, answer, timings, False))
    return answer, timings


async def run_benchmark(queries: list[str]) -> pd.DataFrame:
    rows = []
    for i, q in enumerate(queries):
        t_total = time.perf_counter()
        answer, timings = await guarded_pipeline(q)
        total_ms = round((time.perf_counter() - t_total) * 1000, 1)
        rows.append({
            "query_idx": i,
            "query":     q[:60],
            "answer":    answer[:80],
            **timings,
            "total_ms":  total_ms,
        })
        if (i + 1) % 10 == 0:
            print(f"  [{i+1}/100] avg_total={sum(r['total_ms'] for r in rows)/len(rows):.0f}ms")
    return pd.DataFrame(rows)


def main():
    # Load 50 testset questions; duplicate to 100
    testset_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                "phase-a", "testset_v1.csv")
    testset = pd.read_csv(testset_path)
    queries = (testset["question"].tolist() * 2)[:100]

    print(f"Running benchmark on {len(queries)} queries...")
    df = asyncio.run(run_benchmark(queries))

    out = os.path.join(os.path.dirname(__file__), "latency_benchmark.csv")
    df.to_csv(out, index=False, encoding="utf-8-sig")

    print("\n=== Latency Summary (ms) ===")
    print(f"{'Layer':<12} {'P50':>8} {'P95':>8} {'P99':>8} {'Target':>10}")
    print("-" * 48)
    for layer, target in [("L1_ms", "<50ms"), ("L2_ms", "-"), ("L3_ms", "<100ms"), ("total_ms", "<2500ms")]:
        if layer in df.columns:
            vals = df[layer].dropna()
            p50 = np.percentile(vals, 50)
            p95 = np.percentile(vals, 95)
            p99 = np.percentile(vals, 99)
            print(f"{layer:<12} {p50:>8.0f} {p95:>8.0f} {p99:>8.0f} {target:>10}")

    print(f"\nSaved: {out}")
    print(f"Total audit events: {len(_audit_log)}")


if __name__ == "__main__":
    main()
