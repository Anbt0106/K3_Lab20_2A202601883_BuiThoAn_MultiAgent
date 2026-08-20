"""Researcher agent."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult, SourceDocument
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.search_client import SearchClient


class ResearcherAgent(BaseAgent):
    """Collects sources and creates concise research notes."""

    name = "researcher"

    def __init__(self, search_client: SearchClient | None = None) -> None:
        self.search_client = search_client or SearchClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Populate sources and notes, recording failures in shared state."""

        try:
            documents = self.search_client.search(
                state.request.query, max_results=state.request.max_sources
            )
        except Exception as exc:  # provider errors belong in state for workflow recovery
            state.errors.append(f"researcher.search: {exc}")
            state.add_trace_event("researcher.error", {"error": str(exc)})
            return state

        state.sources = self._deduplicate(documents)
        state.research_notes = "\n".join(
            f"- [{index}] {document.title}: {document.snippet}"
            for index, document in enumerate(state.sources, start=1)
        )
        state.agent_results.append(
            AgentResult(
                agent=AgentName.RESEARCHER,
                content=state.research_notes,
                metadata={"num_sources": len(state.sources)},
            )
        )
        state.add_trace_event("researcher.done", {"num_sources": len(state.sources)})
        return state

    @staticmethod
    def _deduplicate(documents: list[SourceDocument]) -> list[SourceDocument]:
        unique = []
        seen: set[str] = set()
        for document in documents:
            key = document.url or document.title
            if key not in seen:
                seen.add(key)
                unique.append(document)
        return unique
