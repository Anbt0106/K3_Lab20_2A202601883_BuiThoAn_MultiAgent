"""Reusable, provider-consistent benchmark orchestration."""

from collections.abc import Callable, Sequence

from multi_agent_research_lab.core.schemas import BenchmarkMetrics
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.evaluation.benchmark import run_benchmark

Runner = Callable[[str], ResearchState]


def _provider(state: ResearchState) -> str:
    providers = {
        str(source.metadata.get("provider"))
        for source in state.sources
        if source.metadata.get("provider")
    }
    return ",".join(sorted(providers)) or "none"


def run_comparison(
    queries: Sequence[str],
    baseline_runner: Runner,
    multi_agent_runner: Runner,
) -> list[tuple[ResearchState, BenchmarkMetrics]]:
    """Run both architectures on the same query set and annotate metrics."""

    results: list[tuple[ResearchState, BenchmarkMetrics]] = []
    for query in queries:
        for name, runner in (("baseline", baseline_runner), ("multi-agent", multi_agent_runner)):
            state, metrics = run_benchmark(f"{name}: {query}", query, runner)
            provider = _provider(state)
            llm_calls = sum(
                isinstance(event.get("payload"), dict)
                and (
                    "input_tokens" in event["payload"]
                    or "output_tokens" in event["payload"]
                )
                for event in state.trace
            )
            metrics.notes = "; ".join(
                item
                for item in (metrics.notes, f"provider={provider}", f"llm_calls={llm_calls}")
                if item
            )
            results.append((state, metrics))
    return results
