# Bằng chứng Trace

Benchmark multi-agent đã tạo trace local cho từng lần chạy:

- `trace_02.json`: GraphRAG query, route `researcher → analyst → writer → done`.
- `trace_04.json`: customer-support query, route `researcher → analyst → writer → done`.
- `trace_06.json`: production-guardrails query, route `researcher → analyst → writer → done`.

Mỗi trace ghi lại provider nguồn, lịch sử route, token usage, chi phí, citation và lỗi.
Provider đã được xác minh trong các lần chạy này là `tavily`.

## Cách chạy lại

```powershell
$env:PYTHONPATH="src"
python -m multi_agent_research_lab.cli multi-agent `
  --query "When does a multi-agent architecture outperform a single agent?"
```

## Trace trên LangSmith

Project trace của bài lab:

[Mở project `multi-agent-research-lab` trên LangSmith](https://smith.langchain.com/o/ad57570a-c4df-41d6-9b8f-7de1f52b3e1c/projects/p/82754568-0de9-4f01-9aed-a9e995f9b185)

Project này là bằng chứng bên ngoài cho lần chạy multi-agent end-to-end. API key không
được đưa vào artefact hoặc commit lên GitHub.
