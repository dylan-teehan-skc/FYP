"""Autonomous agent with reasoning capabilities."""

from typing import Any

from utils.exceptions import LoopDetectedError
from utils.interfaces import MCPClientProtocol, ReasoningEngineProtocol
from utils.logger import get_logger


class Agent:
    """Async autonomous agent that reasons and calls tools."""

    def __init__(
        self,
        name: str,
        role: str,
        reasoning_engine: ReasoningEngineProtocol,
        mcp_client: MCPClientProtocol,
        loop_threshold: int = 3,
        loop_window: int = 5,
    ) -> None:
        self.name = name
        self.role = role
        self.reasoning_engine = reasoning_engine
        self.mcp_client = mcp_client
        self.loop_threshold = loop_threshold
        self.loop_window = loop_window
        self.action_history: list[dict[str, Any]] = []
        self.log = get_logger(f"Agent:{name}")

    async def execute(self, task: str, context: str = "") -> dict[str, Any]:
        """Execute a task and return the result."""
        self.action_history = []
        tools_doc = self.mcp_client.get_tools_documentation()

        self.log.info("task_started", task=task[:100])

        step = 0
        while True:
            if self._is_looping():
                self.log.warning("loop_detected", step=step)
                raise LoopDetectedError(f"Agent {self.name} stuck in loop after {step} steps")

            step += 1

            decision = await self.reasoning_engine.reason(
                task=task,
                context=context,
                tools_doc=tools_doc,
                history=self.action_history,
            )

            action = decision.get("action")
            reasoning = decision.get("reasoning", "")

            self.log.info("step", step=step, reasoning=reasoning[:200])

            if action == "complete":
                self.log.info("task_complete", steps=step)
                return {"success": True, "steps": step, "history": self.action_history}

            if action is None:
                self.log.debug("no_action", step=step)
                continue

            params = decision.get("parameters", {})
            self.log.info("tool_call", action=action, params=params)

            result = await self.mcp_client.call_tool(action, params)

            if result["success"]:
                self.log.info("tool_result", action=action, result=result.get("result"))
            else:
                self.log.warning("tool_error", action=action, error=result.get("error"))

            self.action_history.append({
                "action": action,
                "parameters": params,
                "result": result.get("result") if result["success"] else result.get("error"),
                "success": result["success"],
            })

    def _is_looping(self) -> bool:
        """Check if agent is stuck in a loop."""
        if len(self.action_history) < self.loop_threshold:
            return False

        recent = [h["action"] for h in self.action_history[-self.loop_window:]]
        for action in set(recent):
            if recent.count(action) >= self.loop_threshold:
                return True
        return False
