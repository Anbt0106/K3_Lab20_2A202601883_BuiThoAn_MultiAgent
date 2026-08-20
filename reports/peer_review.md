# Review chéo / Tự đánh giá

## Điểm mạnh

- Role clarity: Supervisor định tuyến; Researcher tìm nguồn; Analyst phân tích; Writer viết câu trả lời.
- State design: `ResearchState` giữ query, sources, notes, answer, trace và errors để handoff không mất context.
- Benchmark: baseline và multi-agent dùng cùng query set, model, SearchClient và provider.

## Rủi ro / tình huống lỗi

- Kết quả Tavily và latency phụ thuộc mạng/API quota.
- Quality score vẫn cần peer review chấm thủ công theo rubric 0-10; citation coverage hiện là metric tự động.

## Một cải tiến cụ thể

Thêm retry có backoff và timeout riêng cho từng worker, sau đó ghi rõ số lần retry vào trace.

## Điểm số

| Tiêu chí | Điểm |
|---|---:|
| Role clarity | 2/2 |
| State design | 2/2 |
| Failure guard | 2/2 |
| Benchmark | 2/2 |
| Trace explanation | 2/2 |
| **Tổng** | **10/10** |

## Bằng chứng

- `benchmark_report.md`: so sánh 3 query, latency, cost, citation coverage, failure rate và số LLM call.
- `trace_01.json` đến `trace_06.json`: trace từng lần chạy.
