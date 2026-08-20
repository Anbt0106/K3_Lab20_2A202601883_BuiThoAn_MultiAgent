"""LangGraph workflow for the multi-agent research system."""

from typing import Any

from langgraph.graph import END, START, StateGraph

from multi_agent_research_lab.agents import (
    AnalystAgent,
    ResearcherAgent,
    SupervisorAgent,
    WriterAgent,
)
from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.config import Settings, get_settings
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.search_client import SearchClient


class MultiAgentWorkflow:
    """Builds and runs the multi-agent graph.

    Keep orchestration here; keep agent internals in `agents/`.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        agents: dict[str, BaseAgent] | None = None,
        search_client: SearchClient | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.search_client = search_client or SearchClient(settings=self.settings)
        self.supervisor = SupervisorAgent(settings=self.settings)
        self.agents = agents or {
            "researcher": ResearcherAgent(search_client=self.search_client),
            "analyst": AnalystAgent(),
            "writer": WriterAgent(),
        }

    def build(self) -> Any:
        """Create and wire the Supervisor → worker LangGraph."""

        graph = StateGraph(ResearchState)
        graph.add_node("supervisor", self.supervisor.run)
        for name, agent in self.agents.items():
            graph.add_node(name, agent.run)

        graph.add_edge(START, "supervisor")
        graph.add_conditional_edges(
            "supervisor",
            lambda state: state.route_history[-1],
            {
                "researcher": "researcher",
                "analyst": "analyst",
                "writer": "writer",
                "done": END,
            },
        )
        for name in self.agents:
            graph.add_edge(name, "supervisor")
        return graph.compile()

    def run(self, state: ResearchState) -> ResearchState:
        """Execute the compiled graph and return a validated ``ResearchState``."""

        result = self.build().invoke(state)
        if isinstance(result, ResearchState):
            return result
        return ResearchState.model_validate(result)
