"""FastAPI MCP tool server for risk and compliance."""

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

from mcp_server.database import get_connection
from risk_server.schemas import TOOLS
from risk_server.tools import execute_tool

app = FastAPI(title="Risk & Compliance MCP Tool Server")

get_connection()


class ToolCallRequest(BaseModel):
    name: str
    arguments: dict


@app.get("/tools/list")
def list_tools():
    return {"tools": TOOLS}


@app.post("/tools/call")
def call_tool(request: ToolCallRequest):
    return execute_tool(request.name, request.arguments)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8004)
