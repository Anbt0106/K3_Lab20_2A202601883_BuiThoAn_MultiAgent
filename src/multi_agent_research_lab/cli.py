"""Command-line entrypoint for the lab starter."""

from pathlib import Path
from time import perf_counter
from typing import Annotated

import typer
import yaml  # type: ignore[import-untyped]
from pydantic import ValidationError
from rich.console import Console
from rich.panel import Panel

from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.errors import StudentTodoError
from multi_agent_research_lab.core.schemas import ResearchQuery, SourceDocument
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.evaluation.benchmark_runner import run_comparison
from multi_agent_research_lab.evaluation.report import render_markdown_report
from multi_agent_research_lab.graph.workflow import MultiAgentWorkflow
from multi_agent_research_lab.observability.logging import configure_logging
from multi_agent_research_lab.observability.tracing import write_trace_json
from multi_agent_research_lab.services.llm_client import LLMClient
from multi_agent_research_lab.services.search_client import SearchClient

app = typer.Typer(help="Multi-Agent Research Lab starter CLI")
console = Console()


def _init() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)


def _parse_query(query: str) -> ResearchQuery:
    try:
        return ResearchQuery(query=query)
    except ValidationError as exc:
        console.print(
            Panel.fit(
                f"Invalid query: {exc.errors()[0]['msg']}",
                title="Input Error",
                style="red",
            )
        )
        raise typer.Exit(code=1) from exc


def run_baseline(
    request: ResearchQuery,
    llm_client: LLMClient | None = None,
    search_client: SearchClient | None = None,
) -> ResearchState:
    """Search once, then run one LLM call using the shared search path."""

    state = ResearchState(request=request)
    client = llm_client or LLMClient()
    searcher = search_client or SearchClient()
    search_started = perf_counter()
    try:
        state.sources = searcher.search(request.query, max_results=request.max_sources)
    except Exception as exc:
        state.errors.append(f"baseline.search: {exc}")
    state.research_notes = "\n".join(
        f"- [{index}] {source.title}: {source.snippet}"
        for index, source in enumerate(state.sources, start=1)
    )
    state.add_trace_event(
        "baseline.search",
        {
            "provider": state.sources[0].metadata.get("provider") if state.sources else "none",
            "num_sources": len(state.sources),
            "latency_seconds": perf_counter() - search_started,
        },
    )
    started = perf_counter()
    response = client.complete(
        system_prompt=(
            "You are a research assistant. Answer the user's question clearly and accurately "
            "for the requested audience. State uncertainty when evidence is incomplete."
        ),
        user_prompt=(
            f"Audience: {request.audience}\n"
            f"Question: {request.query}\n\n"
            f"Research context:\n{state.research_notes or 'No sources available.'}\n\n"
            "Return a concise answer grounded in the research context."
        ),
    )
    latency = perf_counter() - started
    citations = "\n".join(
        f"[{index}] {source.title} ({_source_reference(source)})"
        for index, source in enumerate(state.sources, start=1)
    )
    state.final_answer = (
        f"{response.content.rstrip()}\n\nSources:\n{citations}"
        if citations
        else response.content
    )
    state.add_trace_event(
        "baseline.complete",
        {
            "latency_seconds": latency,
            "input_tokens": response.input_tokens,
            "output_tokens": response.output_tokens,
            "cost_usd": response.cost_usd,
        },
    )
    return state


def _source_reference(source: SourceDocument) -> str:
    return str(
        source.url
        or source.metadata.get("document_id")
        or source.metadata.get("article_id")
        or "offline-source"
    )


@app.command()
def baseline(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")],
) -> None:
    """Run the single-agent baseline with one LLM call."""

    _init()
    state = run_baseline(_parse_query(query))
    console.print(Panel.fit(state.final_answer or "", title="Single-Agent Baseline"))
    console.print_json(data=state.model_dump_json())


@app.command("multi-agent")
def multi_agent(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")],
) -> None:
    """Run the multi-agent workflow skeleton."""

    _init()
    state = ResearchState(request=_parse_query(query))
    workflow = MultiAgentWorkflow()
    try:
        result = workflow.run(state)
    except StudentTodoError as exc:
        console.print(Panel.fit(str(exc), title="Expected TODO", style="yellow"))
        raise typer.Exit(code=2) from exc
    console.print(result.model_dump_json(indent=2))


@app.command()
def benchmark(
    config_path: Annotated[
        Path, typer.Option("--config", help="YAML config containing benchmark.queries")
    ] = Path("configs/lab_default.yaml"),
    output_dir: Annotated[
        Path, typer.Option("--output-dir", help="Directory for report and JSON traces")
    ] = Path("reports"),
) -> None:
    """Compare baseline and multi-agent on the same configured queries."""

    _init()
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    queries = config.get("benchmark", {}).get("queries", [])
    if not queries:
        raise typer.BadParameter("benchmark.queries must contain at least one query")

    settings = get_settings()
    search_client = SearchClient(settings=settings)
    baseline_llm = LLMClient()
    workflow = MultiAgentWorkflow(settings=settings, search_client=search_client)

    def baseline_runner(query: str) -> ResearchState:
        return run_baseline(
            ResearchQuery(query=query), llm_client=baseline_llm, search_client=search_client
        )

    def multi_agent_runner(query: str) -> ResearchState:
        return workflow.run(ResearchState(request=ResearchQuery(query=query)))

    results = run_comparison(queries, baseline_runner, multi_agent_runner)
    output_dir.mkdir(parents=True, exist_ok=True)
    for index, (state, _) in enumerate(results, start=1):
        write_trace_json(state, output_dir / f"trace_{index:02d}.json")
    report = render_markdown_report([metrics for _, metrics in results])
    (output_dir / "benchmark_report.md").write_text(report, encoding="utf-8")
    console.print(report)


if __name__ == "__main__":
    app()
