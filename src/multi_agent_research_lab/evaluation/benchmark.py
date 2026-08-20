"""Metrics for comparing single-agent and multi-agent runs."""

from collections.abc import Callable
from time import perf_counter

from multi_agent_research_lab.core.schemas import BenchmarkMetrics
from multi_agent_research_lab.core.state import ResearchState

Runner = Callable[[str], ResearchState]
QualityScorer = Callable[[ResearchState], float]


def compute_citation_coverage(state: ResearchState) -> float:
    """Return the fraction of sources mentioned in the final answer."""

    if not state.sources or not state.final_answer:
        return 0.0
    answer = state.final_answer.casefold()
    cited = sum(
        1
        for source in state.sources
        if source.title.casefold() in answer
        or (source.url is not None and source.url.casefold() in answer)
    )
    return cited / len(state.sources)


def _trace_cost(state: ResearchState) -> float | None:
    costs = [
        event["payload"].get("cost_usd")
        for event in state.trace
        if isinstance(event.get("payload"), dict)
        and event["payload"].get("cost_usd") is not None
    ]
    return sum(float(cost) for cost in costs) if costs else None


def run_benchmark(
    run_name: str,
    query: str,
    runner: Runner,
    quality_scorer: QualityScorer | None = None,
) -> tuple[ResearchState, BenchmarkMetrics]:
    """Run one query and collect comparable latency, cost, quality and failure metrics."""

    started = perf_counter()
    state = runner(query)
    latency = perf_counter() - started
    notes = "; ".join(state.errors)
    metrics = BenchmarkMetrics(
        run_name=run_name,
        latency_seconds=latency,
        estimated_cost_usd=_trace_cost(state),
        quality_score=quality_scorer(state) if quality_scorer else None,
        citation_coverage=compute_citation_coverage(state),
        failure_rate=1.0 if state.errors else 0.0,
        notes=notes,
    )
    return state, metrics
