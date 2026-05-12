"""
phase-c/input_guard.py
InputGuard: two-layer PII detection (VN regex + Presidio NER) and topic scope validator.

Classes:
  PIIGuard   — scrubs PII from input text
  TopicGuard — validates query is within allowed domain (financial/legal)

Run as script to test PII detection on 10 test inputs.
"""
import re
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# ─── VN PII Patterns ─────────────────────────────────────────────────────────

VN_PII = {
    "CCCD":     r"\b\d{12}\b",
    "PHONE_VN": r"(?<!\d)(\+84|0)\d{9,10}(?!\d)",
    "TAX_CODE": r"\b\d{10}(-\d{3})?\b",
    "EMAIL":    r"\b[\w.\-+]+@[\w.\-]+\.[a-zA-Z]{2,}\b",
}


# ─── PII Guard ────────────────────────────────────────────────────────────────

class PIIGuard:
    def __init__(self):
        try:
            from presidio_analyzer import AnalyzerEngine
            from presidio_anonymizer import AnonymizerEngine
            self._analyzer   = AnalyzerEngine()
            self._anonymizer = AnonymizerEngine()
            self._presidio_ok = True
        except Exception as e:
            print(f"  [WARN] Presidio unavailable: {e}. Using regex-only mode.")
            self._presidio_ok = False

    def scrub_vn(self, text: str) -> str:
        """Layer 1: Vietnamese-specific regex patterns."""
        for label, pattern in VN_PII.items():
            text = re.sub(pattern, f"[{label}]", text)
        return text

    # Only redact structured PII entities; PERSON/ORG/LOC produce too many false
    # positives on Vietnamese text (e.g., "Thue GTGT" → PERSON).
    _SAFE_ENTITIES = {
        "EMAIL_ADDRESS", "PHONE_NUMBER", "CREDIT_CARD",
        "US_SSN", "US_BANK_NUMBER", "IBAN_CODE", "IP_ADDRESS",
        "URL", "MEDICAL_LICENSE",
    }

    def scrub_ner(self, text: str) -> str:
        """Layer 2: Presidio NER — only structured PII (no PERSON/ORG to avoid FP on VN text)."""
        if not self._presidio_ok or not text.strip():
            return text
        try:
            results = self._analyzer.analyze(text=text, language="en")
            filtered = [r for r in results if r.entity_type in self._SAFE_ENTITIES]
            if filtered:
                return self._anonymizer.anonymize(text=text, analyzer_results=filtered).text
        except Exception:
            pass
        return text

    def sanitize(self, text: str) -> tuple[str, float]:
        """Full pipeline. Returns (sanitized_text, latency_ms)."""
        t0 = time.perf_counter()
        if not text:
            return text, (time.perf_counter() - t0) * 1000
        out = self.scrub_ner(self.scrub_vn(text))
        return out, (time.perf_counter() - t0) * 1000


# ─── Topic Guard ──────────────────────────────────────────────────────────────

class TopicGuard:
    """Validates query is within allowed domain using keyword + optional embedding similarity."""

    ALLOWED_TOPICS = [
        "thue gtgt tai chinh ke toan bao cao tai chinh",
        "bao ve du lieu ca nhan nghi dinh phap luat",
        "doanh nghiep cong ty kinh doanh",
    ]
    KEYWORDS = [
        # Vietnamese with diacritics
        "thuế", "gtgt", "tài chính", "kế toán", "doanh thu", "khai thuế",
        "dữ liệu", "nghị định", "cá nhân", "công ty", "doanh nghiệp",
        # Romanized Vietnamese (no diacritics)
        "thue", "tai chinh", "ke toan", "du lieu", "nghi dinh",
        "ca nhan", "cong ty", "doanh nghiep", "khau tru", "bao cao",
        "tu lieu", "doanh thu", "hang hoa", "chu the",
        # English
        "tax", "vat", "financial", "company", "data", "decree",
    ]
    REFUSE_MSG = (
        "Xin lỗi, tôi chỉ có thể hỗ trợ các câu hỏi về tài chính (thuế GTGT, "
        "kế toán) và bảo vệ dữ liệu cá nhân theo Nghị định 13/2023. "
        "Vui lòng đặt câu hỏi liên quan đến các chủ đề này. "
        "Ví dụ: 'Thuế GTGT phải nộp là bao nhiêu?' hoặc "
        "'Điều kiện chuyển giao dữ liệu ra nước ngoài là gì?'"
    )

    def __init__(self):
        self._embed = None
        self._topic_vecs = None
        try:
            import numpy as np
            from langchain_openai import OpenAIEmbeddings
            from config import OPENAI_API_KEY
            if OPENAI_API_KEY:
                self._embed = OpenAIEmbeddings(api_key=OPENAI_API_KEY)
                import numpy as np
                self._np = np
                self._topic_vecs = [
                    np.array(self._embed.embed_query(t)) for t in self.ALLOWED_TOPICS
                ]
        except Exception:
            pass

    def check(self, text: str) -> tuple[bool, str]:
        """Returns (is_on_topic, reason_or_refuse_message)."""
        if not text.strip():
            return False, "Empty input"

        # Injection keyword quick-reject before topic check
        injection_patterns = [
            "ignore", "jailbreak", "dan", "override", "forget",
            "disregard", "pretend", "roleplay", "evil ai", "no restriction",
            "base64", "rot13", "system prompt",
        ]
        text_lower = text.lower()
        for pat in injection_patterns:
            if pat in text_lower:
                return False, f"Potential prompt injection detected: '{pat}'"

        # Keyword match (fast, no API call)
        if any(kw in text_lower for kw in self.KEYWORDS):
            return True, "On topic (keyword match)"

        # Embedding similarity (if available)
        if self._embed is not None:
            try:
                import numpy as np
                q_vec = np.array(self._embed.embed_query(text))
                sims = [
                    float(np.dot(q_vec, tv) / (np.linalg.norm(q_vec) * np.linalg.norm(tv) + 1e-9))
                    for tv in self._topic_vecs
                ]
                best = max(sims)
                if best >= 0.55:
                    return True, f"On topic (similarity={best:.2f})"
            except Exception:
                pass

        return False, self.REFUSE_MSG


# ─── Test Runner ──────────────────────────────────────────────────────────────

def run_pii_tests():
    import pandas as pd

    guard = PIIGuard()

    test_cases = [
        # (input_text, has_pii)
        ("Hi, I'm John Smith from Microsoft. Email: john@ms.com", True),
        ("Call me at +1-555-1234 or visit 123 Main Street NYC", True),
        ("So CCCD cua toi la 012345678901", True),
        ("Lien he qua 0987654321 hoac tax 0123456789-001", True),
        ("Customer Nguyen Van A CCCD 098765432101 phone 0912345678", True),
        ("", False),
        ("Just a normal question about VAT returns", False),
        ("A" * 5000, False),
        ("Ly Van Binh o 123 Le Loi TP.HCM", False),
        ("tax_code:0123456789-001 cccd:012345678901", True),
    ]

    rows = []
    latencies = []
    for inp, has_pii in test_cases:
        sanitized, lat = guard.sanitize(inp)
        pii_found = (inp.strip() != "" and inp != sanitized)
        correct = (has_pii == pii_found) or (not has_pii and not pii_found)
        rows.append({
            "input":      inp[:80],
            "output":     sanitized[:80],
            "has_pii":    has_pii,
            "pii_found":  pii_found,
            "correct":    correct,
            "latency_ms": round(lat, 2),
        })
        latencies.append(lat)
        status = "OK" if correct else "MISS"
        print(f"[{status}] [{lat:5.1f}ms] {inp[:50]!r}")

    df = pd.DataFrame(rows)
    out = os.path.join(os.path.dirname(__file__), "pii_test_results.csv")
    df.to_csv(out, index=False, encoding="utf-8-sig")

    import numpy as np
    recall = df[df["has_pii"]]["pii_found"].mean()
    p95 = np.percentile(latencies, 95)
    print(f"\nPII recall (detection rate): {recall:.0%}")
    print(f"Latency P95: {p95:.1f}ms (target: <50ms)")
    print(f"Saved: {out}")


if __name__ == "__main__":
    run_pii_tests()
