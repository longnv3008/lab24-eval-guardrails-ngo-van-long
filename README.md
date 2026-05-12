# Lab 24: RAG Evaluation & Guardrail System

**Student:** Ngô Văn Long — MSHV: 2A202600129  
**Track 3 — Day 24, VinUniversity AI Course**  
**Domain:** Vietnamese Financial + Legal RAG (VAT Tax Return + Nghị định 13/2023 Personal Data Protection)

---

## Overview

This lab builds a **production-ready evaluation and guardrail system** for a Vietnamese-language RAG assistant. The system processes user queries about VAT tax obligations and personal data protection law through a 4-layer defense-in-depth pipeline, measures answer quality with automated evaluation, and mitigates LLM judge bias with statistical calibration.

The pipeline achieves: L1 latency P95 = 4 ms, L3 latency P95 = 70 ms, total pipeline P95 = 1,044 ms (all within SLO targets). Adversarial attack detection rate = 95% with 0% false positives on legitimate Vietnamese financial queries.

---

## Repository Structure

```
lab24-eval-guardrails-ngo-van-long/
├── config.py                        # Shared API keys and thresholds
├── rag_adapter.py                   # Thin wrapper for Day18 RAG pipeline
├── requirements.txt
├── prompts.md                       # All LLM prompt templates
├── phase-a/
│   ├── gen_testset_data.py          # Generates testset_v1.csv (50 questions)
│   ├── testset_v1.csv               # 50-question synthetic test set
│   ├── gen_ragas_results.py         # Runs RAGAS evaluation
│   ├── ragas_summary.json           # Evaluation results
│   └── failure_analysis.md          # Failure cluster analysis
├── phase-b/
│   ├── judge_pipeline.py            # Pairwise + absolute LLM judge
│   ├── kappa_analysis.py            # Cohen's kappa + bias measurement
│   ├── judge_results.csv
│   ├── bias_analysis.png
│   └── judge_bias_report.md
├── phase-c/
│   ├── input_guard.py               # PIIGuard + TopicGuard
│   ├── adversarial_test.py          # 20 attacks + 10 FP queries
│   ├── output_guard.py              # Llama Guard 3 via Groq API
│   ├── full_pipeline.py             # Async L1→L2→L3→L4 pipeline + benchmark
│   ├── pii_test_results.csv
│   ├── adversarial_test_results.csv
│   ├── output_guard_results.csv
│   └── latency_benchmark.csv
├── phase-d/
│   └── blueprint.md                 # SLOs, architecture, playbooks, cost analysis
└── scripts/
    ├── run_eval.py                  # CI/CD RAGAS gate
    └── .github/workflows/eval-gate.yml
```

---

## Phase A: RAGAS Evaluation (30 pts)

**Test set:** 50 synthetic questions from two Vietnamese documents — Q4/2024 VAT tax return (BCTC DHA Surfaces) and Nghị định 13/2023. Distribution: simple=25 (50%), multi_context=13 (26%), reasoning=12 (24%).

| Metric | Score | Target | Status |
|---|---|---|---|
| Faithfulness | 0.8087 | ≥ 0.85 | Below target |
| Answer Relevancy | 0.7830 | ≥ 0.80 | Below target |
| Context Precision | 0.6716 | ≥ 0.70 | Below target |
| Context Recall | 0.7273 | ≥ 0.75 | Below target |

**Estimated eval cost:** $1.82 USD for 50 questions.

**Failure clusters identified:**
- **C1 (70%):** Cross-domain multi-context queries — retriever returns chunks from only one document; fix: increase `RERANK_TOP_K` 3→6, add metadata-filtered retrieval
- **C2 (30%):** Implicit reasoning queries — `temperature=0.0` suppresses inference; fix: query classification + prompt routing

**CI/CD gate:** `.github/workflows/eval-gate.yml` — runs on every PR to `main`; fails if any metric drops below threshold.

---

## Phase B: LLM-as-Judge (25 pts)

**Method:** GPT-4o-mini pairwise comparison with swap-and-average bias mitigation. Each (v1, v2) pair is evaluated twice with answer order swapped; winner determined by majority.

| Bias | Measured | Threshold | Status |
|---|---|---|---|
| Position bias (A-first win rate) | 36.7% | > 55% = problematic | Low (reverse direction) |
| Length bias (B-longer win rate) | 46.7% | > 60% = problematic | Not detected |
| Cohen's kappa (human vs judge) | -0.071 | ≥ 0.60 = production-ready | Below threshold |

**Key finding:** Kappa = -0.071 (worse than chance). Root cause: human reviewers prioritized exact VND amount citations (e.g., `52.133.830 đồng [40]`); the judge prioritized answer fluency without domain-specific citation verification.

**Recommended mitigations:** Add citation-checking rubric to judge prompt; ensemble 3 models; expand human label set to 50 pairs.

---

## Phase C: Guardrails (35 pts)

### Input Guard (L1)

**PIIGuard** — two-layer PII redaction:
1. Vietnamese regex patterns: CCCD (12-digit), PHONE_VN (+84/0 prefix), TAX_CODE (10-digit), EMAIL
2. Presidio NER filtered to structured entities only (EMAIL_ADDRESS, PHONE_NUMBER, CREDIT_CARD, IBAN_CODE) — excludes PERSON/ORG/LOC to avoid false positives on Vietnamese text

**PII detection recall:** 83% (5/6 positive cases), P95 latency = 93.7 ms

**TopicGuard** — domain scope validator:
- Injection keyword quick-reject: 12 patterns (DAN, jailbreak, roleplay, base64, rot13, etc.)
- Keyword match: 28 keywords in Vietnamese (with/without diacritics) + English
- Optional: OpenAI embedding cosine similarity ≥ 0.55

| Test set | Result |
|---|---|
| Adversarial attacks (20 total) | 19/20 blocked = **95% detection rate** |
| Legitimate queries (10) | 0/10 blocked = **0% false positive rate** |

### Output Guard (L3)

**Llama Guard 3 8B** via Groq API (free tier, no GPU required):
- 10 unsafe outputs tested: **90% detected** (9/10 blocked)
- 10 safe Vietnamese financial outputs: **0% false positive** (10/10 passed)
- P95 latency: 70 ms (target < 100 ms ✓)

### Full Async Pipeline

```
L1 PII+Topic [~3ms] → L2 RAG [~850ms] → L3 Llama Guard [~50ms] → L4 Audit [async]
```

| Layer | P50 | P95 | Target |
|---|---|---|---|
| L1 (input guard) | 3 ms | 4 ms | < 50 ms ✓ |
| L2 (RAG) | 805 ms | 998 ms | — |
| L3 (output guard) | 49 ms | 70 ms | < 100 ms ✓ |
| Total | 855 ms | 1,044 ms | < 2,500 ms ✓ |

---

## Phase D: Production Blueprint (10 pts)

See [phase-d/blueprint.md](phase-d/blueprint.md) for full details.

**6 SLOs defined:**
1. Faithfulness ≥ 0.85 (P2 alert at < 0.80 for 30 min)
2. Answer Relevancy ≥ 0.80
3. E2E P95 latency < 2,500 ms (L1 < 50 ms, L3 < 100 ms)
4. Guardrail FP rate < 5%
5. Adversarial detection rate ≥ 95%
6. Availability ≥ 99.5%

**3 incident playbooks:** Faithfulness drop, Guardrail FP spike, P95 latency spike — each with diagnosis steps, root-cause table, and escalation path.

**Monthly cost at 100k queries:** ~$124/month (~$0.0012/query). Largest costs: Presidio compute ($36.50), infrastructure ($55), RAG generation ($21.75). RAGAS sampling adds $9.60; Groq Llama Guard is free within tier.

---

## Running the Code

```bash
# Install dependencies
pip install -r requirements.txt

# Phase A: Generate test set + evaluate
cd phase-a && python gen_testset_data.py
cd phase-a && python gen_ragas_results.py

# Phase B: Run judge pipeline + bias analysis
cd phase-b && python judge_pipeline.py
cd phase-b && python kappa_analysis.py

# Phase C: Run guardrail tests
cd phase-c && python input_guard.py          # PII test (10 cases)
cd phase-c && python adversarial_test.py     # 20 attacks + 10 FP
cd phase-c && python output_guard.py         # Llama Guard 20 outputs
cd phase-c && python full_pipeline.py        # 100-query benchmark

# CI gate
python scripts/run_eval.py
```

**API keys required:** `OPENAI_API_KEY` (Phase A, B, embedding), `GROQ_API_KEY` (Phase C L3), `COHERE_API_KEY` (reranker, optional).

Set in `config.py` or environment variables.
