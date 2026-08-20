# Báo cáo Benchmark

| Luồng chạy | Độ trễ (s) | Chi phí (USD) | Chất lượng | Độ phủ citation | Tỷ lệ lỗi | Ghi chú |
|---|---:|---:|---:|---:|---:|---|
| baseline: Research GraphRAG state-of-the-art and write a 500-word summary | 14.77 | 0.0004 | 8.0 | 100% | 0% | provider=tavily; llm_calls=1; self-review |
| multi-agent: Research GraphRAG state-of-the-art and write a 500-word summary | 21.29 | 0.0011 | 8.5 | 100% | 0% | provider=tavily; llm_calls=2; self-review |
| baseline: Compare single-agent and multi-agent workflows for customer support | 17.61 | 0.0005 | 8.0 | 100% | 0% | provider=tavily; llm_calls=1; self-review |
| multi-agent: Compare single-agent and multi-agent workflows for customer support | 19.73 | 0.0009 | 8.5 | 100% | 0% | provider=tavily; llm_calls=2; self-review |
| baseline: Summarize production guardrails for LLM agents | 7.02 | 0.0003 | 8.0 | 100% | 0% | provider=tavily; llm_calls=1; self-review |
| multi-agent: Summarize production guardrails for LLM agents | 22.11 | 0.0010 | 8.5 | 100% | 0% | provider=tavily; llm_calls=2; self-review |

## Ghi chú về điểm chất lượng

Quality là điểm tự đánh giá/peer review tạm thời theo thang 0–10, dựa trên độ rõ ràng
của vai trò, handoff state, guard lỗi, grounding bằng chứng và độ đầy đủ citation.
Nên thay các điểm tạm thời này bằng điểm review chéo chính thức trước khi nộp bài.

## Tình huống lỗi và cách khắc phục

Ở phiên bản đầu, benchmark ghi nhận số LLM call của multi-agent bằng 0 và để trống chi phí,
vì benchmark chỉ nhận diện event tên `llm.complete`, trong khi worker phát ra `analyst.done`
và `writer.done`; trace của worker cũng chưa có `cost_usd`.
Đã khắc phục bằng cách ghi token usage và chi phí vào trace của Analyst/Writer, đồng thời
đếm mọi event có input/output token. Báo cáo mới ghi nhận baseline có một LLM call,
multi-agent có hai LLM call và có chi phí cho cả hai luồng.
