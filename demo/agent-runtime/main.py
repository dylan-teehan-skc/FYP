"""Entry point for agent-runtime."""

import asyncio
import logging
import os
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
logging.getLogger("LiteLLM").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)
logging.getLogger("aiohttp").setLevel(logging.WARNING)

from dotenv import load_dotenv  # noqa: E402

from agent.agent import Agent  # noqa: E402
from mcp.client import MCPClient  # noqa: E402
from orchestrator.orchestrator import Orchestrator  # noqa: E402
from reasoning.engine import ReasoningEngine  # noqa: E402
from utils.config import AppConfig  # noqa: E402
from utils.exceptions import ConfigurationError  # noqa: E402
from utils.logger import get_logger, init_logging  # noqa: E402


def load_config() -> AppConfig:
    """Load and validate configuration from config.json."""
    config_path = Path(__file__).parent / "config.json"
    try:
        return AppConfig.model_validate_json(config_path.read_text())
    except FileNotFoundError as e:
        raise ConfigurationError(f"Config file not found: {config_path}") from e
    except Exception as e:
        raise ConfigurationError(f"Invalid configuration: {e}") from e


async def main() -> None:
    """Run the agent-runtime."""
    load_dotenv()

    config = load_config()
    init_logging(config.logging)
    log = get_logger("main")

    mcp_url = os.getenv("MCP_SERVER_URL", config.mcp.server_url)

    reasoning_engine = ReasoningEngine(model=config.llm.model)
    mcp_client = MCPClient(
        server_url=mcp_url,
        timeout=config.mcp.timeout_seconds,
        max_retries=config.mcp.max_retries,
    )

    if not await mcp_client.connect():
        log.error("Failed to connect to MCP server")
        return

    try:
        agent = Agent(
            name="SupportAgent",
            role="customer_support",
            reasoning_engine=reasoning_engine,
            mcp_client=mcp_client,
            loop_threshold=config.agent.loop_detection_threshold,
            loop_window=config.agent.loop_detection_window,
        )

        orchestrator = Orchestrator()
        orchestrator.register_agent(agent)

        task = (
            "Handle support ticket T-12345: process the refund "
            "if eligible, notify the customer, and close the ticket"
        )
        result = await orchestrator.execute(task)

        log.info(
            "workflow_result",
            success=result["success"],
            steps=result.get("steps"),
            workflow_id=result.get("workflow_id"),
        )
        if result.get("timing"):
            log.debug("timing", timing=result["timing"])
    finally:
        await mcp_client.close()


if __name__ == "__main__":
    asyncio.run(main())
