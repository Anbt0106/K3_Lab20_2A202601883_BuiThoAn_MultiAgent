# Design Template

## Bài toán

Xây dựng research assistant nhận một câu hỏi kỹ thuật, tìm kiếm nguồn đáng tin cậy,
tổng hợp bằng chứng và tạo câu trả lời có trích dẫn. Hệ thống cần hỗ trợ hai kiến trúc
để so sánh công bằng: một single-agent gọi LLM một lần và một multi-agent workflow
gồm Supervisor, Researcher, Analyst và Writer.

## Vì sao dùng multi-agent?

Single-agent phù hợp với câu hỏi đơn giản nhưng khó tách biệt các trách nhiệm tìm kiếm,
đánh giá bằng chứng và viết. Multi-agent được dùng khi bài toán có nhiều bước phụ thuộc
nhau, cần trace rõ từng bước và muốn kiểm soát chất lượng qua các handoff. Tuy nhiên,
multi-agent có thêm latency, chi phí và điểm lỗi nên không mặc định tốt hơn single-agent.

## Vai trò các agent

| Agent | Responsibility | Input | Output | Failure mode |
|---|---|---|---|---|
| Supervisor | Đọc state và chọn bước tiếp theo | `ResearchState` | Route tới researcher/analyst/writer hoặc dừng | Max iterations; dừng khi có lỗi hoặc đã có answer |
| Researcher | Tìm và chuẩn hóa nguồn | Query, `max_sources`, `SearchClient` | `sources`, `research_notes` | Tavily → offline corpus → mock; bắt lỗi search |
| Analyst | Phân tích claim và độ tin cậy bằng chứng | Query, sources, research notes | `analysis_notes` | Không gọi khi thiếu nguồn; ghi lỗi vào state |
| Writer | Viết câu trả lời cuối có citation | Query, analysis/research notes, sources | `final_answer` | Không viết khi thiếu context; citation theo cùng format |

## State dùng chung

`ResearchState` là nguồn sự thật duy nhất được truyền qua workflow:

- `request`: câu hỏi, audience và giới hạn số nguồn.
- `iteration`, `route_history`: chống vòng lặp vô hạn và giải thích routing.
- `sources`: danh sách `SourceDocument` dùng chung cho baseline và multi-agent.
- `research_notes`: bằng chứng thô sau bước search.
- `analysis_notes`: phân tích của Analyst để Writer sử dụng.
- `final_answer`: câu trả lời cuối kèm citation.
- `agent_results`: output có cấu trúc của từng worker.
- `trace`: tên bước, token usage, cost, provider và metadata thời gian.
- `errors`: lỗi có thể quan sát được thay vì làm mất toàn bộ context.

## Chính sách routing

Graph multi-agent:

```text
START → Supervisor
          ├─ chưa có sources → Researcher → Supervisor
          ├─ chưa có analysis → Analyst → Supervisor
          ├─ chưa có final_answer → Writer → Supervisor
          └─ đủ kết quả hoặc lỗi/max iterations → END
```

Single-agent dùng cùng `SearchClient` trước, sau đó gọi LLM đúng một lần để viết câu trả lời.

## Cơ chế bảo vệ

- Max iterations: 6 lần theo `Settings.max_iterations`.
- Timeout: 60 giây theo cấu hình lab; latency được đo cho từng benchmark run.
- Retry: lỗi provider được ghi vào state; search có fallback theo thứ tự Tavily → offline → mock.
- Fallback: offline corpus của thầy được dùng khi Tavily lỗi/rỗng; mock là fallback cuối cùng.
- Validation: Pydantic kiểm tra `ResearchQuery`, `SourceDocument`, `ResearchState` và `BenchmarkMetrics`.
- Citation guard: Writer chỉ tham chiếu các source có trong shared state.

## Kế hoạch benchmark

### Bộ câu hỏi

1. `Research GraphRAG state-of-the-art and write a 500-word summary`
2. `Compare single-agent and multi-agent workflows for customer support`
3. `Summarize production guardrails for LLM agents`

### Các chỉ số

| Metric | Cách đo | Kết quả kỳ vọng |
|---|---|---|
| Latency | Wall-clock time cho từng query | Single-agent thường nhanh hơn |
| Cost | Tổng `cost_usd` từ trace LLM | Single-agent thường rẻ hơn |
| Quality | Peer review rubric 0-10 | So sánh cùng query và cùng model |
| Citation coverage | Tỷ lệ source xuất hiện trong answer | Hai mode dùng cùng citation format |
| Failure rate | Query có lỗi / tổng query | Cả hai phải ghi lỗi và fallback rõ ràng |
| Search provider | Metadata `provider` của source | Hai mode phải dùng cùng provider |
| LLM calls | Đếm event có token usage | Baseline = 1; multi-agent = 2 trong workflow hiện tại |

### Kết quả kỳ vọng

Benchmark hiện tại cho thấy cả hai mode dùng Tavily và citation coverage 100% trên
3 query. Multi-agent có latency và cost cao hơn vì thực hiện hai lần gọi LLM (Analyst
và Writer), còn baseline chỉ thực hiện một lần gọi LLM.
