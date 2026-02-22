"""FastAPI MCP tool server for the NovaTech Electronics demo."""

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

from state import StateManager
from tools import TOOLS, execute_tool

app = FastAPI(title="NovaTech MCP Tool Server")
state = StateManager()


class ToolCallRequest(BaseModel):
    name: str
    arguments: dict


@app.get("/tools/list")
def list_tools():
    return {"tools": TOOLS}


@app.post("/tools/call")
def call_tool(request: ToolCallRequest):
    return execute_tool(request.name, request.arguments, state)


@app.post("/reset")
def reset_state():
    state.reset()
    return {"status": "reset", "message": "All state restored to initial values"}


def run():
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    run()
