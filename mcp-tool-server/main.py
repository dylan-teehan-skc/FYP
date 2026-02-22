"""MCP Tool Server."""

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

from tools import TOOLS, execute_tool

app = FastAPI(title="MCP Tool Server")


class ToolCallRequest(BaseModel):
    name: str
    arguments: dict


@app.get("/tools/list")
def list_tools():
    """Return list of available tools."""
    return {"tools": TOOLS}


@app.post("/tools/call")
def call_tool(request: ToolCallRequest):
    """Execute a tool and return result."""
    result = execute_tool(request.name, request.arguments)
    return result


def run():
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    run()
