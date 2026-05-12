# prompts.md — AI Prompt Log (Lab 24 Academic Integrity)

All prompts used with AI assistants (Claude) during Lab 24 implementation.

---

## Phase A — RAGAS Evaluation

### A.1 — Testset generation strategy
**Prompt:** "Tạo 50 câu hỏi đa dạng từ tài liệu tiếng Việt về tài chính (BCTC, khai thuế GTGT) và pháp luật (Nghị định 13/2023 bảo vệ dữ liệu cá nhân). Phân bố: 50% đơn giản, 25% suy luận, 25% đa ngữ cảnh. Đảm bảo câu hỏi có ground truth rõ ràng từ văn bản."

### A.3 — Failure cluster naming
**Prompt:** "Given these 10 low-scoring RAG responses on Vietnamese financial/legal documents, identify root causes and cluster them into 2-3 distinct failure patterns. Each cluster needs a specific technical proposed fix (not 'improve prompt')."

### A.4 — CI/CD gate design
**Prompt:** "Design a GitHub Actions workflow that runs RAGAS evaluation on every PR to main, blocks merge if metrics fall below thresholds, and uploads the report as an artifact."

---

## Phase B — LLM-as-Judge

### B.1 — Judge prompt design
**Prompt:** "Write an impartial pairwise judge prompt for comparing two RAG answers. Criteria: factual accuracy, relevance, conciseness. Must output valid JSON with 'winner' (A/B/tie) and 'reason'. Include swap-and-average bias mitigation."

### B.3 — Kappa interpretation
**Prompt:** "Given Cohen's kappa = 0.63 between human labels and LLM judge on Vietnamese financial Q&A, interpret this result and identify what biases likely caused disagreements."

### B.4 — Bias analysis methodology
**Prompt:** "Design a quantitative analysis for position bias and length bias in LLM judge outputs. Include Python code using matplotlib for visualization."

---

## Phase C — Guardrails

### C.1 — Vietnamese PII patterns
**Prompt:** "What are the regex patterns for Vietnamese PII: CCCD (citizen ID), phone numbers, tax codes, email addresses? These should be combined with Presidio NER for English entities."

### C.2 — Topic guard fallback message
**Prompt:** "Write a graceful refusal message in Vietnamese for when a query is off-topic for a banking/finance/legal RAG assistant. Should be helpful and redirect the user."

### C.3 — Adversarial test set design
**Prompt:** "Design 20 adversarial inputs to test an input guardrail: 5 DAN variants, 5 role-play attacks, 3 payload splitting, 3 encoding attacks, 4 indirect prompt injection via document context."

### C.4 — Llama Guard integration
**Prompt:** "How to integrate Llama Guard 3 via Groq API for output safety checking without GPU? Need Python code that takes user_input + agent_response, returns is_safe boolean and latency."

---

## Phase D — Blueprint

### D — Production blueprint design
**Prompt:** "Design a production deployment blueprint for a Vietnamese RAG evaluation + guardrail system. Include: 5+ SLOs with alert thresholds, architecture Mermaid diagram with 4 defense layers, 3 incident playbooks with investigation steps and resolution, monthly cost analysis for 100k queries."
