"""Analyst agent."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient


class AnalystAgent(BaseAgent):
    """Turns research notes into structured insights."""

    name = "analyst"

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Use the LLM to extract claims and assess the collected evidence."""

        if not state.sources or not state.research_notes:
            state.errors.append("analyst: missing research sources or notes")
            state.add_trace_event("analyst.error", {"error": "missing research context"})
            return state
        try:
            response = self.llm_client.complete(
                system_prompt=(
                    "You are an evidence analyst. Extract key claims, compare viewpoints, "
                    "flag weak evidence, and be explicit about uncertainty."
                ),
                user_prompt=(
                    f"Question: {state.request.query}\n"
                    f"Research notes:\n{state.research_notes}\n"
                    "Return structured analysis for a writer."
                ),
            )
        except Exception as exc:
            state.errors.append(f"analyst.llm: {exc}")
            state.add_trace_event("analyst.error", {"error": str(exc)})
            return state

        state.analysis_notes = response.content
        state.agent_results.append(
            AgentResult(
                agent=AgentName.ANALYST,
                content=response.content,
                metadata={
                    "input_tokens": response.input_tokens,
                    "output_tokens": response.output_tokens,
                    "cost_usd": response.cost_usd,
                },
            )
        )
        state.add_trace_event(
            "analyst.done",
            {
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "cost_usd": response.cost_usd,
            },
        )
        return state
