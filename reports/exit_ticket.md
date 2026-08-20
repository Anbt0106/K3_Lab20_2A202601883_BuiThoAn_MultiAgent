# Bài trả lời cuối

## 1. Khi nào nên dùng multi-agent?

Nên dùng khi bài toán có nhiều trách nhiệm tách biệt, ví dụ cần tìm kiếm nguồn, đánh giá bằng chứng và viết câu trả lời. Việc tách Researcher, Analyst và Writer giúp mỗi bước có mục tiêu rõ, trace dễ debug và có thể thay thế từng thành phần.

## 2. Khi nào không nên dùng multi-agent?

Không nên dùng cho câu hỏi đơn giản hoặc cần phản hồi cực nhanh. Single-agent chỉ cần một lần gọi LLM, latency và chi phí thấp hơn, trong khi multi-agent tạo thêm các bước handoff và nhiều điểm có thể lỗi.

## Kết luận từ benchmark

Trong benchmark của lab, hai chế độ dùng cùng Tavily và citation coverage 100%. Multi-agent mất nhiều thời gian hơn vì có hai LLM call phân tích/viết; baseline chỉ có một LLM call.
