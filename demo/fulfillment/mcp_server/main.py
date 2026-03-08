"""FastAPI MCP tool server for the order fulfillment demo."""

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

from mcp_server.database import get_connection, reset_db
from mcp_server.schemas import TOOLS
from mcp_server.tools import execute_tool

app = FastAPI(title="Order Fulfillment MCP Tool Server")

# Initialise the database on startup
get_connection()


class ToolCallRequest(BaseModel):
    name: str
    arguments: dict


@app.get("/tools/list")
def list_tools():
    return {"tools": TOOLS}


@app.post("/tools/call")
def call_tool(request: ToolCallRequest):
    result = execute_tool(request.name, request.arguments)
    return result


@app.post("/reset")
def reset_state():
    reset_db()
    return {"status": "reset", "message": "Database restored to initial seed data"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
