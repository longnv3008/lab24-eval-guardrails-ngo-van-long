# LLM Judge Bias Report

## Setup

- **Judge model:** GPT-4o-mini (temperature=0.0)
- **Method:** Pairwise comparison, swap-and-average (each pair evaluated twice with order swapped)
- **Comparison:** v1 (naive baseline — first retrieved context) vs v2 (production RAG with reranker)
- **Test set:** 30 questions from testset_v1.csv (first 30)

---

## Cohen's Kappa: Human vs Judge

| Sample | Human labels (10 pairs) | Judge labels (10 pairs) | Agreement |
|---|---|---|---|
| Matches | B,B,B,B,tie,B,tie,A,B,B | tie,B,tie,B,B,tie,B,A,B,tie | 4/10 = 40% |
| Cohen's kappa | **-0.071** | | WORSE than chance |

### Interpretation

Kappa = -0.071 falls in the range **< 0** → "Worse than chance — systematic judge error."

```
Kappa scale:
< 0.00 → WORSE than chance        ← CURRENT: -0.071
0.00–0.20 → Slight agreement
0.20–0.40 → Fair agreement
0.40–0.60 → Moderate agreement
0.60–0.80 → Substantial (production-ready)
> 0.80 → Almost perfect
```

### Root Cause Analysis (kappa < 0.6)

**Why does the judge disagree systematically with human reviewers?**

1. **Different criteria weighting:**
   - Human reviewers prioritized: **specific citation accuracy** (line numbers like `[40]`, exact VND amounts)
   - LLM judge prioritized: **answer completeness and fluency** → tends to prefer longer, more comprehensive answers even without specific numbers

2. **Domain knowledge gap:**
   - Human reviewers know that `52.133.830 đồng [40a]` is the correct answer for tax queries
   - The judge doesn't have domain knowledge of Vietnamese tax forms — it can't verify whether a cited line number is correct

3. **Tie vs Agreement bias:**
   - Judge chose "tie" in 4/10 cases where human chose B or A with high confidence
   - This suggests judge uncertainty correlates with human certainty (opposite of expected pattern)

**Evidence:**
- Query 0: Human=B (high confidence, B gives exact amount). Judge=tie (couldn't distinguish accuracy levels without domain knowledge)
- Query 4: Human=tie. Judge=B (judge saw B was longer, preferred it despite equal factual accuracy)
- Query 5: Human=B. Judge=tie (both gave correct number; judge didn't check line reference precision)

**Mitigation strategies:**
1. **Add domain-specific rubric** to judge prompt: "In Vietnamese tax/legal documents, an answer that cites exact line numbers (e.g., [40], [25]) is more reliable than one without citations."
2. **Chain-of-thought verification:** Ask judge to first check factual correctness against the contexts, then determine winner
3. **Ensemble judging:** Use 3 models (GPT-4o-mini, Claude Haiku, Gemini Flash), take majority vote — reduces single-model bias

---

## Bias 1: Position Bias

Measures whether the judge prefers the answer listed in position A (first) regardless of content.

```python
# Result from kappa_analysis.py
# A wins as first-listed: 11/30 = 36.7%
# Expected: ~50% if no position bias
```

| Condition | A wins | B wins | Tie |
|---|---|---|---|
| Run 1 (A=v1 listed first) | 36.7% | 46.7% | 16.7% |
| Run 2 (A=v2 listed first, before flip) | ~40% | ~43% | ~17% |

**Finding:** A win rate is 36.7% when listed first — **below** 50%, not above. This indicates a **reverse position bias** (judge slightly prefers the second-listed answer). Likely because the second answer has more context from reading the first one and the judge naturally defers to what was presented last.

**Severity:** Mild (36.7% vs 50% baseline, 13.3% swing). Swap-and-average mitigates this adequately.

---

## Bias 2: Length Bias

Measures whether the judge prefers the longer answer regardless of content quality.

```python
# Result from kappa_analysis.py
# B wins when B is longer: 14/30 = 46.7%
# Expected: ~50% if no length bias
```

| Length condition | B longer (len_diff > 0) | B wins in this subset |
|---|---|---|
| B longer than A | 30/30 cases (v2 always more verbose) | 46.7% (14/30) |
| Length-adjusted | - | - |

**Finding:** B wins 46.7% when B is longer — near random (close to 50% baseline). **Length bias is not significant** in this dataset. Both v1 and v2 are synthetic answers of similar length in the test data.

However, in production pairwise comparison (comparing real model outputs), length bias has been documented as a significant issue (Zheng et al., 2023 — "Judging LLM-as-a-Judge"). **Mitigation recommendation:** Truncate both answers to 300 characters before judging in production deployment.

---

## Summary

| Bias | Measured | Threshold | Status |
|---|---|---|---|
| Position bias | 36.7% A-first win rate | >55% = problematic | Low (reverse direction) |
| Length bias | 46.7% B-longer win rate | >60% = problematic | Not detected |
| Judge-human agreement (kappa) | -0.071 | ≥0.60 = production-ready | Below threshold |

## Bias Chart

See `bias_analysis.png` for visual summary of position and length bias measurements.

## Recommended Actions Before Production Deployment

1. **Redesign judge prompt** with domain-specific rubric for Vietnamese tax/legal documents
2. **Add citation-checking instruction:** "Verify whether cited line numbers [XX] appear in the provided context"
3. **Expand human label set:** Label 50 pairs (not 10) for more reliable kappa estimate
4. **Ensemble judging:** Use 3 models to reduce single-model systematic errors
5. **Current recommendation:** Use judge for monitoring trends only (not binary pass/fail decisions) until kappa reaches ≥0.6
