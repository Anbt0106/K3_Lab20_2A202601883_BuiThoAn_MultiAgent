"""Writer agent."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult, SourceDocument
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient


class WriterAgent(BaseAgent):
    """Produces final answer from research and analysis notes."""

    name = "writer"

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Synthesize a cited answer from analysis and source documents."""

        context = state.analysis_notes or state.research_notes
        if not context or not state.sources:
            state.errors.append("writer: missing analysis/research context or sources")
            state.add_trace_event("writer.error", {"error": "missing writing context"})
            return state
        try:
            response = self.llm_client.complete(
                system_prompt=(
                    "You are a careful research writer. Answer clearly for the requested "
                    "audience, use only the supplied evidence, and do not invent citations."
                ),
                user_prompt=(
                    f"Audience: {state.request.audience}\n"
                    f"Question: {state.request.query}\n"
                    f"Analysis:\n{context}\n"
                    "Write the final answer body."
                ),
            )
        except Exception as exc:
            state.errors.append(f"writer.llm: {exc}")
            state.add_trace_event("writer.error", {"error": str(exc)})
            return state

        citations = "\n".join(
            f"[{index}] {source.title} ({_source_reference(source)})"
            for index, source in enumerate(state.sources, start=1)
        )
        state.final_answer = f"{response.content.rstrip()}\n\nSources:\n{citations}"
        state.agent_results.append(
            AgentResult(
                agent=AgentName.WRITER,
                content=state.final_answer,
                metadata={
                    "input_tokens": response.input_tokens,
                    "output_tokens": response.output_tokens,
                    "cost_usd": response.cost_usd,
                    "num_citations": len(state.sources),
                },
            )
        )
        state.add_trace_event(
            "writer.done",
            {
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "cost_usd": response.cost_usd,
                "num_citations": len(state.sources),
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
