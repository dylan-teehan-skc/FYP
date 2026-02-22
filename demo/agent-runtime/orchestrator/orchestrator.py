"""Orchestrator for coordinating multiple agents."""

import uuid
from typing import Any

from utils.exceptions import LoopDetectedError
from utils.interfaces import AgentProtocol
from utils.logger import bind_context, clear_context, get_logger
from utils.timer import BlockTimer


class Orchestrator:
    """Coordinates multiple agents to complete workflows."""

    def __init__(self) -> None:
        self.agents: dict[str, AgentProtocol] = {}
        self.log = get_logger("Orchestrator")

    def register_agent(self, agent: AgentProtocol) -> None:
        """Register an agent with the orchestrator."""
        self.agents[agent.name] = agent
        self.log.info("agent_registered", agent=agent.name, role=agent.role)

    async def execute(self, task: str, agent_name: str | None = None) -> dict[str, Any]:
        """Execute a workflow with the specified or first available agent."""
        workflow_id = str(uuid.uuid4())[:8]
        timer = BlockTimer(workflow_id)
        bind_context(workflow_id=workflow_id)

        self.log.info("workflow_start", task=task[:50])
        timer.start("workflow")

        if agent_name and agent_name in self.agents:
            agent = self.agents[agent_name]
        elif self.agents:
            agent = list(self.agents.values())[0]
        else:
            self.log.error("no_agents_available")
            return {"success": False, "error": "No agents registered"}

        bind_context(agent_name=agent.name)
        self.log.info("agent_selected", agent=agent.name)

        timer.start(f"agent:{agent.name}")
        try:
            result = await agent.execute(task)
        except LoopDetectedError as e:
            result = {"success": False, "error": str(e)}
        timer.stop()

        timer.stop()
        result["workflow_id"] = workflow_id
        result["timing"] = timer.render()

        if result["success"]:
            self.log.info("workflow_complete", steps=result.get("steps"))
        else:
            self.log.error("workflow_failed", error=result.get("error"))

        clear_context()
        return result
