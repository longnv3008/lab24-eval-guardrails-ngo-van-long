# Test Set Review Notes — testset_v1.csv

Manual review of 10 questions (rows 0, 5, 10, 15, 20, 25, 30, 35, 40, 45).

## Review Table

| # | Row | Question (excerpt) | Type | Review Assessment | Action |
|---|---|---|---|---|---|
| 1 | 0 | "Thuế GTGT phải nộp trong kỳ (dòng 40)..." | simple | Câu hỏi rõ ràng; ground truth chính xác từ dòng [40] tờ khai | Keep |
| 2 | 5 | "Tổng giá trị hàng hóa dịch vụ mua vào..." | simple | Câu hỏi tốt; số liệu rõ ràng | Keep |
| 3 | 10 | "Hàng hóa nhập khẩu trong kỳ có giá trị..." | simple | Câu hỏi hợp lệ; ground truth "0 đồng" chính xác | Keep |
| 4 | 15 | "Hàng hóa bán ra không chịu thuế GTGT..." | simple | Ground truth "0 đồng" đúng; câu hỏi phân biệt rõ loại hàng | Keep |
| 5 | 20 | "Tên hoạt động sản xuất kinh doanh..." | simple | Câu hỏi đơn giản nhưng hữu ích cho test retrieval cơ bản | Keep |
| 6 | 25 | "Tại sao thuế GTGT còn khấu trừ kỳ trước..." | reasoning | **Ground truth quá ngắn — chỉ có phép tính, thiếu giải thích** | **EDITED** |
| 7 | 30 | "Giới hạn 72 giờ báo cáo sự cố quan trọng..." | reasoning | Câu hỏi yêu cầu suy luận logic; ground truth tốt | Keep |
| 8 | 35 | "Tại sao điều chỉnh thuế GTGT [37] và [38]..." | reasoning | Câu hỏi hay; ground truth kết hợp tờ khai lần đầu với điều chỉnh | Keep |
| 9 | 40 | "So sánh tỷ lệ thuế GTGT đầu ra và đầu vào..." | multi_context | Ground truth tốt; kết hợp hai dòng khác nhau trong tờ khai | Keep |
| 10 | 45 | "Mối liên hệ giữa mã số thuế... và dữ liệu cá nhân..." | multi_context | **Câu hỏi quá trừu tượng; cần làm rõ ngữ cảnh Nghị định** | **EDITED** |

## Edited Questions

### Row 25 (Reasoning):

**Original ground truth:**
> "Thuế phát sinh kỳ này 129.511.633 lớn hơn khấu trừ 77.377.803 nên số phải nộp là 52.133.830 đồng"

**Edited ground truth:**
> "Thuế GTGT phát sinh trong kỳ là 129.511.633 đồng, lớn hơn số còn được khấu trừ từ kỳ trước là 77.377.803 đồng. Do đó số thuế GTGT thực phải nộp = 129.511.633 - 77.377.803 = 52.133.830 đồng. Phần chênh lệch này phản ánh nghĩa vụ thuế thực tế của doanh nghiệp."

**Reason:** Ground truth ban đầu chỉ nêu phép tính mà không giải thích logic. Ground truth mới cung cấp đầy đủ ngữ cảnh để RAG có thể đánh giá faithfulness chính xác hơn.

### Row 45 (Multi-context):

**Original question:**
> "Mối liên hệ giữa mã số thuế 0106769437 và dữ liệu cá nhân theo Nghị định 13/2023?"

**Edited question:**
> "Theo Nghị định 13/2023, mã số thuế 0106769437 của công ty DHA có thể được coi là dữ liệu cá nhân không, và nếu có thì nghĩa vụ bảo vệ là gì?"

**Reason:** Câu hỏi gốc quá mơ hồ. Câu hỏi mới cụ thể hóa: đặt mã số thuế trong ngữ cảnh Nghị định 13/2023 và yêu cầu phân tích pháp lý rõ ràng hơn.

## Distribution Check

```
evolution_type
simple           25  (50.0%) ✓ target 50%
multi_context    13  (26.0%) ✓ target 25%
reasoning        12  (24.0%) ✓ target 25%
Total:           50
```

## Quality Assessment

- **Coverage:** Test set bao gồm cả hai document: BCTC/tờ khai thuế GTGT (Q1-Q25 phần lớn) và Nghị định 13/2023 (Q16-Q19 và nhiều multi-context)
- **Diversity:** Simple questions test retrieval; reasoning tests inference; multi-context tests cross-document synthesis
- **Language:** Tất cả câu hỏi bằng tiếng Việt, phù hợp với domain
- **Ground truth quality:** Sau khi edit, ground truth rõ ràng và có thể verify từ documents
- **Edge cases:** Có câu hỏi với answer "0 đồng" (để test xem RAG có trả về 0 chính xác không)
