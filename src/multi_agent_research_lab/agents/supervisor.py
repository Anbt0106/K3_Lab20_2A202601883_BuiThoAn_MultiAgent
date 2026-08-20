"""Supervisor / router for the multi-agent workflow."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.config import Settings, get_settings
from multi_agent_research_lab.core.state import ResearchState


class SupervisorAgent(BaseAgent):
    """Decides which worker should run next and when to stop."""

    name = "supervisor"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def run(self, state: ResearchState) -> ResearchState:
        """Choose the next worker from the fields still missing in ``state``."""

        if state.iteration >= self.settings.max_iterations or state.final_answer or state.errors:
            route = "done"
        elif not state.sources:
            route = "researcher"
        elif not state.analysis_notes:
            route = "analyst"
        elif not state.final_answer:
            route = "writer"
        else:
            route = "done"

        state.record_route(route)
        state.add_trace_event(
            "supervisor.route",
            {"next": route, "iteration": state.iteration},
        )
        return state
