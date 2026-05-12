# Failure Cluster Analysis

Generated from `ragas_results.csv` — 50 questions evaluated with RAGAS 4 metrics.

## Score Summary by Question Type

| Type | Faithfulness | Answer Relevancy | Context Precision | Context Recall | Avg |
|---|---|---|---|---|---|
| simple | 0.893 | 0.869 | 0.796 | 0.823 | 0.844 |
| reasoning | 0.770 | 0.755 | 0.636 | 0.653 | 0.692 |
| multi_context | 0.683 | 0.644 | 0.527 | 0.613 | 0.614 |
| **Overall** | **0.809** | **0.783** | **0.672** | **0.727** | **0.748** |

## Bottom 10 Questions

| # | Question (truncated 70 chars) | Type | F | AR | CP | CR | Avg | Cluster |
|---|---|---|---|---|---|---|---|---|
| 1 | So sánh tỷ lệ thuế GTGT đầu ra và đầu vào của DHA... | multi_context | 0.651 | 0.557 | 0.404 | 0.472 | 0.521 | C1 |
| 2 | Nghĩa vụ của DHA vừa là người nộp thuế vừa là tổ... | multi_context | 0.578 | 0.473 | 0.462 | 0.673 | 0.547 | C1 |
| 3 | Hai nghĩa vụ phải thực hiện đồng thời nếu DHA bị... | multi_context | 0.574 | 0.657 | 0.528 | 0.433 | 0.548 | C1 |
| 4 | Quy trình nào cần theo nếu DHA muốn chia sẻ dữ... | multi_context | 0.598 | 0.665 | 0.558 | 0.484 | 0.577 | C1 |
| 5 | Sự minh bạch trong xử lý dữ liệu và kê khai thuế... | multi_context | 0.755 | 0.546 | 0.381 | 0.628 | 0.577 | C1 |
| 6 | Mối liên hệ giữa mã số thuế... và dữ liệu cá nhân... | multi_context | 0.706 | 0.503 | 0.542 | 0.616 | 0.592 | C1 |
| 7 | Điều gì xảy ra nếu DHA không tuân thủ cả nghĩa... | multi_context | 0.563 | 0.727 | 0.671 | 0.471 | 0.608 | C1 |
| 8 | Hậu quả nào xảy ra nếu công ty khai sai thuế GTGT... | reasoning | 0.638 | 0.678 | 0.586 | 0.598 | 0.625 | C2 |
| 9 | Kỳ tính thuế Q4/2024 trùng với giai đoạn nào... | multi_context | 0.653 | 0.719 | 0.582 | 0.561 | 0.629 | C2 |
| 10 | Tổng nghĩa vụ tài chính và chi phí bảo vệ... | multi_context | 0.671 | 0.677 | 0.556 | 0.669 | 0.643 | C2 |

## Clusters Identified

### Cluster C1: Cross-domain Multi-Context Failures (7/10)

**Pattern:** Questions requiring simultaneous retrieval and synthesis of information from **both** the BCTC/VAT return document AND Nghị định 13/2023. The retriever returns high-relevance chunks from only one document, leaving the other domain entirely absent from the context window.

**Hallmark:** `context_precision` is the lowest metric (avg 0.50) — meaning the retrieved contexts frequently **don't** contain the evidence needed to answer cross-domain questions.

**Examples:**
- "So sánh tỷ lệ thuế GTGT đầu ra và đầu vào của DHA..." (needs BCTC [25] + [35])
- "Nghĩa vụ của DHA vừa là người nộp thuế vừa là tổ chức xử lý dữ liệu..." (needs BCTC + Nghị định)
- "Sự minh bạch trong xử lý dữ liệu và kê khai thuế có điểm chung..." (needs Nghị định minh bạch + tờ khai cam đoan)

**Root cause:** The hybrid BM25+dense search scores anchor to one semantic cluster. When a question mentions "thuế GTGT" and "dữ liệu cá nhân", BM25 keyword overlap gives higher score to the tax document, so only tax chunks are retrieved. The Nghị định 13 context is missing entirely.

**Proposed fixes (specific and technical):**
1. **Query decomposition:** Split cross-domain questions into 2 sub-queries ("... về thuế GTGT?" + "... về dữ liệu cá nhân?"), retrieve top-3 for each independently, merge and deduplicate before LLM generation.
2. **Metadata-filtered retrieval:** Tag each chunk with `domain: [tax | data_protection]`. For queries containing both domain keywords, run two separate searches with domain filters and concatenate results.
3. **Increase `RERANK_TOP_K` from 3 → 6:** Give the reranker more candidates to surface cross-document evidence. At top_k=3, cross-domain chunks rarely appear.

---

### Cluster C2: Implicit Consequence / Cross-temporal Reasoning Failures (3/10)

**Pattern:** Questions asking about **consequences** (e.g., "what happens if X violates rule Y?") or **temporal relationships** (e.g., "Q4/2024 trùng với giai đoạn nào trong vòng đời dữ liệu?"). These require implicit inference that the documents never explicitly state.

**Hallmark:** `faithfulness` drops to 0.62–0.67 — the LLM fills in reasoning steps that aren't grounded in retrieved text, creating hallucinated but plausible-sounding consequences.

**Examples:**
- "Hậu quả nào xảy ra nếu công ty khai sai thuế GTGT đầu vào?" (consequence not stated in doc)
- "Kỳ tính thuế Q4/2024 trùng với giai đoạn nào trong vòng đời quản lý dữ liệu?" (temporal mapping)
- "Tổng nghĩa vụ tài chính và chi phí bảo vệ dữ liệu" (cost aggregation across sources)

**Root cause:** The system prompt instructs `temperature=0.0` and "trả lời dựa trên context được cung cấp". For consequence questions, the model correctly refuses to fabricate, but then either (a) produces incomplete answers (low AR) or (b) cautiously hedges with boilerplate (low faithfulness to any specific claim).

**Proposed fixes:**
1. **Query classification + prompt routing:** Classify incoming questions as `factual_lookup | consequence | temporal_reasoning` before retrieval. Route consequence/temporal queries to a chain-of-thought prompt: "Based on the facts in context, reason step-by-step about the likely consequences."
2. **Augment corpus with consequence tables:** Add a structured FAQ document that explicitly states legal consequences (e.g., "Vi phạm NĐ13 → xử phạt theo Điều X → mức phạt Y") so the retriever can find grounded answers.
3. **ReAct-style generation:** For reasoning queries, run a 2-step pipeline: (1) retrieve relevant facts, (2) run a separate "reasoning" LLM pass that explicitly chains the facts into a conclusion.

## Key Takeaways

1. **Context Precision is the primary bottleneck** (avg 0.672 vs target 0.70) — the retriever quality is the main driver of overall RAG performance.
2. **Multi-context questions dominate failures** — 7/10 bottom questions are `multi_context`, all from the cross-domain category.
3. **Simple questions perform well** (avg 0.844) — the pipeline is reliable for single-fact lookups within one document.
4. **Recommended priority:** Fix the retriever (C1) before the prompt (C2), as C1 affects 70% of failures.
