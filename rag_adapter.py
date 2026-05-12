"""
rag_adapter.py — Thin wrapper around Day18 RAG pipeline.
Falls back to mock responses when Qdrant/embeddings are unavailable.
"""
import sys
import os
import json
import random

DAY18_ROOT = os.path.join(os.path.dirname(__file__), "..", "Day18-Track3-Production-RAG")
sys.path.insert(0, DAY18_ROOT)

_search = None
_reranker = None
_pipeline_available = None

# Realistic mock answers based on the Vietnamese documents
_MOCK_RESPONSES = [
    (
        "Thuế GTGT phải nộp trong kỳ là 52.133.830 đồng theo tờ khai 01/GTGT.",
        ["Thuế GTGT phát sinh trong kỳ [36] 129.511.633. Thuế GTGT phải nộp [40] 52.133.830."],
    ),
    (
        "Thuế GTGT đầu vào được khấu trừ kỳ này là 215.163.767 đồng.",
        ["Thuế GTGT của hàng hóa, dịch vụ mua vào được khấu trừ kỳ này 215.163.767 [25]."],
    ),
    (
        "Tổng doanh thu và thuế GTGT của hàng hóa, dịch vụ bán ra là 3.703.655.610 đồng [34].",
        ["Tổng doanh thu và thuế GTGT của hàng hóa, dịch vụ bán ra [34] 3.703.655.610 [35] 344.675.400."],
    ),
    (
        "Theo Nghị định 13/2023, xử lý dữ liệu cá nhân phải tuân thủ: hợp pháp, minh bạch, mục đích cụ thể, giới hạn lưu trữ.",
        ["Xu ly du lieu ca nhan phai tuan thu cac nguyen tac: hop phap, minh bach, muc dich cu the, gioi han luu tru."],
    ),
    (
        "Sự cố rò rỉ dữ liệu phải được báo cáo trong vòng 72 giờ kể từ khi phát hiện (theo mock Nghị định 13).",
        ["To chuc xu ly du lieu co nghia vu bao cao co quan quan ly khi xay ra su co lam ro ri, mat du lieu ca nhan (mock: trong vong 72 gio ke tu khi phat hien)."],
    ),
    (
        "Chuyển giao dữ liệu cá nhân ra nước ngoài cần: đánh giá tác động, hợp đồng, biện pháp bảo đảm.",
        ["Chuyen giao du lieu ca nhan ra nuoc ngoai can tuan thu dieu kien theo Nghi dinh va huong dan lien nganh (mock: can danh gia tac dong, hop dong, bien phap bao dam)."],
    ),
    (
        "Hàng hóa, dịch vụ bán ra chịu thuế suất 10% có giá trị 3.703.685.610 đồng [32].",
        ["Hang hoa, dich vu ban ra chiu thue suat 10% 3.703.685.610 [32] 344.675.400 [33]."],
    ),
    (
        "Thuế GTGT còn được khấu trừ kỳ trước chuyển sang là 77.377.803 đồng [22].",
        ["Thuế giá trị gia tăng còn được khấu trừ kỳ trước chuyển sang 77.377.803 [22]."],
    ),
    (
        "Công ty CÓ PHẦN DHA SURFACES có mã số thuế 0106769437.",
        ["[04] Tên người nộp thuế: CÔNG TY CÓ PHẦN DHA SURFACES. [05] Mã số thuế: 0106769437."],
    ),
    (
        "Kỳ tính thuế là Quý 4 năm 2024 theo tờ khai 01/GTGT.",
        ["[016] Kỳ tính thuế: Quý 4 năm 2024."],
    ),
]


def _check_pipeline():
    global _pipeline_available
    if _pipeline_available is not None:
        return _pipeline_available
    try:
        import qdrant_client
        from src.pipeline import build_pipeline
        _pipeline_available = True
    except Exception:
        _pipeline_available = False
    return _pipeline_available


def _ensure_pipeline():
    global _search, _reranker
    if _search is None:
        from src.pipeline import build_pipeline
        _search, _reranker = build_pipeline()


def run_query(question: str) -> tuple[str, list[str]]:
    """Returns (answer, contexts). Falls back to mock if pipeline unavailable."""
    if _check_pipeline():
        try:
            _ensure_pipeline()
            from src.pipeline import run_query as _rq
            return _rq(question, _search, _reranker)
        except Exception as e:
            print(f"  [WARN] Pipeline error ({e}), using mock response")

    # Mock fallback — rotate through realistic answers
    mock = random.choice(_MOCK_RESPONSES)
    return mock[0], mock[1]
