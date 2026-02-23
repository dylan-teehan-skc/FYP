"""FastAPI MCP tool server for the NovaTech Electronics demo."""

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

from logger import get_logger, init_logging
from state import StateManager
from tools import TOOLS, execute_tool

init_logging()
log = get_logger("mcp-server")

app = FastAPI(title="NovaTech MCP Tool Server")
state = StateManager()


class ToolCallRequest(BaseModel):
    name: str
    arguments: dict


@app.get("/tools/list")
def list_tools():
    log.info("tools_listed", count=len(TOOLS))
    return {"tools": TOOLS}


@app.post("/tools/call")
def call_tool(request: ToolCallRequest):
    log.info("tool_call", tool=request.name)
    result = execute_tool(request.name, request.arguments, state)
    if "error" in result:
        log.warning("tool_error", tool=request.name, error=result["error"])
    else:
        log.info("tool_success", tool=request.name)
    return result


@app.post("/reset")
def reset_state():
    state.reset()
    log.info("state_reset")
    return {"status": "reset", "message": "All state restored to initial values"}


def run():
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    run()
