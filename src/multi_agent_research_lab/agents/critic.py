"""Citation and answer-completeness checks for the research workflow."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState


class CriticAgent(BaseAgent):
    """Check that the final answer is grounded in the retrieved sources."""

    name = "critic"

    def run(self, state: ResearchState) -> ResearchState:
        """Record citation coverage and an explicit failure when no answer exists."""

        answer = state.final_answer or ""
        if not answer:
            error = "critic: missing final answer"
            state.errors.append(error)
            state.agent_results.append(
                AgentResult(
                    agent=AgentName.CRITIC,
                    content=error,
                    metadata={"status": "failed", "citation_coverage": 0.0},
                )
            )
            state.add_trace_event("critic.error", {"error": error})
            return state

        normalized_answer = answer.casefold()
        cited_sources = sum(
            bool(
                source.title.casefold() in normalized_answer
                or (source.url and source.url.casefold() in normalized_answer)
            )
            for source in state.sources
        )
        total_sources = len(state.sources)
        coverage = cited_sources / total_sources if total_sources else 0.0
        metadata = {
            "status": "passed" if coverage > 0.0 or not state.sources else "warning",
            "cited_sources": cited_sources,
            "total_sources": total_sources,
            "citation_coverage": coverage,
        }
        state.agent_results.append(
            AgentResult(
                agent=AgentName.CRITIC,
                content=(
                    f"Citation coverage: {coverage:.0%} "
                    f"({cited_sources}/{total_sources} sources)."
                ),
                metadata=metadata,
            )
        )
        state.add_trace_event("critic.done", metadata)
        return state
