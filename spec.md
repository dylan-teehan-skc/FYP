# Self-Optimizing Multi-Agent System

A self-improving multi-agent system that learns optimal workflows through process mining. Multiple agents execute tasks autonomously under orchestrator coordination, logging all actions to PostgreSQL. Process mining algorithms analyze these logs across many runs to identify the fastest paths, which are stored and reused via semantic search for similar future tasks.

**Key Insight**: By running the same task type many times with LLM non-determinism producing varied execution paths, the system accumulates diverse workflow traces. Process mining then discovers which sequences of agent actions and tool calls consistently produce the fastest, cheapest results.

---

## Repository Structure

```
FYP/
├── agent-runtime/       # Multi-agent orchestration (Gemini-powered)
├── mcp-tool-server/     # MCP server exposing tools for agents
├── event-logger/        # Structured event logging library (pip package)
├── analytics-db/        # PostgreSQL + pgvector + process mining
└── demo-harness/        # Experimentation and visualization
```

---

## Event Log Structure

The event log format is critical for process mining. Every action in the system produces an event with this structure:

### Event Schema

```python
@dataclass
class Event:
    # === Process Mining Core Fields ===
    event_id: str           # Unique identifier (UUID)
    workflow_id: str        # Case ID - groups events into a single workflow run
    timestamp: datetime     # When the event occurred (ISO 8601)
    activity: str           # The action performed (e.g., "tool_call:check_ticket_status")

    # === Multi-Agent Tracking ===
    agent_name: str         # Which agent performed this action (e.g., "TriageAgent")
    agent_role: str         # Agent's role (e.g., "triage", "resolver", "escalation")

    # === Tool Call Details ===
    tool_name: str | None   # MCP tool called (null for non-tool events)
    tool_parameters: dict   # Input parameters to the tool
    tool_response: dict     # Response from the tool

    # === LLM Metrics ===
    llm_model: str          # Model used (e.g., "gemini-1.5-pro")
    llm_prompt_tokens: int  # Input tokens consumed
    llm_completion_tokens: int  # Output tokens generated
    llm_reasoning: str      # Agent's reasoning before action (for debugging)

    # === Performance Metrics ===
    duration_ms: float      # How long this action took
    cost_usd: float         # Estimated cost of this action

    # === Outcome ===
    status: str             # "success", "failure", "timeout", "loop_detected"
    error_message: str | None  # Error details if status != success

    # === Workflow Context ===
    step_number: int        # Sequential step within this workflow
    parent_event_id: str | None  # For nested/delegated actions
```

### Activity Naming Convention

Activities follow a structured naming pattern for process mining clarity:

| Activity Pattern | Description | Example |
|-----------------|-------------|---------|
| `workflow:start` | Workflow begins | `workflow:start` |
| `workflow:complete` | Workflow ends successfully | `workflow:complete` |
| `workflow:fail` | Workflow ends in failure | `workflow:fail` |
| `orchestrator:delegate` | Orchestrator assigns task to agent | `orchestrator:delegate` |
| `agent:reason` | Agent performs reasoning step | `agent:reason` |
| `tool_call:{tool_name}` | Agent calls an MCP tool | `tool_call:check_ticket_status` |
| `tool_result:{tool_name}` | Tool returns result | `tool_result:check_ticket_status` |
| `agent:handoff` | Agent passes to another agent | `agent:handoff` |

### Database Table

```sql
CREATE TABLE event_logs (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    activity VARCHAR(255) NOT NULL,

    -- Multi-agent tracking
    agent_name VARCHAR(100) NOT NULL,
    agent_role VARCHAR(50),

    -- Tool call details
    tool_name VARCHAR(100),
    tool_parameters JSONB,
    tool_response JSONB,

    -- LLM metrics
    llm_model VARCHAR(50),
    llm_prompt_tokens INTEGER,
    llm_completion_tokens INTEGER,
    llm_reasoning TEXT,

    -- Performance metrics
    duration_ms FLOAT,
    cost_usd DECIMAL(10, 6),

    -- Outcome
    status VARCHAR(20) NOT NULL,
    error_message TEXT,

    -- Workflow context
    step_number INTEGER NOT NULL,
    parent_event_id UUID REFERENCES event_logs(event_id),

    -- Indexes for process mining queries
    INDEX idx_workflow_id (workflow_id),
    INDEX idx_timestamp (timestamp),
    INDEX idx_activity (activity),
    INDEX idx_agent_name (agent_name)
);
```

### Example Event Sequence

A single workflow might produce these events:

```
workflow_id: "w-123"

Step 1: workflow:start
        agent_name: "Orchestrator"
        tool_name: null
        timestamp: T+0ms

Step 2: orchestrator:delegate
        agent_name: "Orchestrator"
        tool_name: null
        tool_parameters: {task: "Handle refund", delegate_to: "TriageAgent"}

Step 3: agent:reason
        agent_name: "TriageAgent"
        tool_name: null
        llm_reasoning: "Customer wants refund. Need to check ticket status first."

Step 4: tool_call:check_ticket_status
        agent_name: "TriageAgent"
        tool_name: "check_ticket_status"
        tool_parameters: {ticket_id: "T-456"}
        duration_ms: 230

Step 5: tool_result:check_ticket_status
        agent_name: "TriageAgent"
        tool_name: "check_ticket_status"
        tool_response: {status: "open", type: "refund_request"}

Step 6: agent:reason
        agent_name: "TriageAgent"
        tool_name: null
        llm_reasoning: "Ticket is refund request. Searching knowledge base for refund policy."

Step 7: tool_call:search_knowledge_base
        agent_name: "TriageAgent"
        tool_name: "search_knowledge_base"
        tool_parameters: {query: "refund policy"}
        duration_ms: 180

Step 8: tool_result:search_knowledge_base
        agent_name: "TriageAgent"
        tool_name: "search_knowledge_base"
        tool_response: {articles: [...], top_result: "Refunds processed within 7 days"}

Step 9: tool_call:close_ticket
        agent_name: "TriageAgent"
        tool_name: "close_ticket"
        tool_parameters: {ticket_id: "T-456", resolution_summary: "Refund approved per policy"}
        duration_ms: 150

Step 10: tool_result:close_ticket
         agent_name: "TriageAgent"
         tool_name: "close_ticket"
         tool_response: {success: true, notification_sent: true}

Step 11: workflow:complete
         agent_name: "Orchestrator"
         tool_name: null
         duration_ms: 4500
         cost_usd: 0.0023
         status: "success"
```

---

## Repository 1: `agent-runtime`

**Purpose**: Multi-agent orchestration system with Gemini-powered autonomous agents

### Design Philosophy

**Object-Oriented Architecture**: All components are implemented as classes with clear responsibilities, encapsulation, and well-defined interfaces. This approach:
- Prevents state management issues common in functional approaches
- Makes testing and mocking straightforward
- Enables dependency injection for flexibility
- Keeps related logic cohesive and easy to reason about

**SOLID Principles**: Code must adhere to SOLID:
- **S**ingle Responsibility: Each class has one reason to change (e.g., `Agent` reasons, `MCPClient` communicates)
- **O**pen/Closed: Classes open for extension, closed for modification (e.g., new reasoning strategies via subclassing)
- **L**iskov Substitution: Subtypes substitutable for base types (e.g., any `Agent` subclass works with `Orchestrator`)
- **I**nterface Segregation: Small, focused interfaces (e.g., separate `ToolCaller` and `Reasoner` protocols)
- **D**ependency Inversion: Depend on abstractions, not concretions (e.g., `Agent` depends on `ReasoningEngine` interface)

**Code Style**:
- Write simple, readable code
- Do the intended task without overdoing it
- Write minimal code to achieve the given task at a high standard
- Prioritize readability over cleverness
- No premature optimization or over-engineering
- Only short docstrings at top of files (one line describing what the file does)
- Each component gets its own folder for organization

**Future UI**: The agent-runtime is built as a backend service with the intention of adding a UI frontend in the future. Keep API boundaries clean and response formats UI-friendly.

### Project Structure

```
agent-runtime/
├── pyproject.toml
├── config.json
├── logs/
├── tests/
│   ├── __init__.py
│   ├── conftest.py       # Pytest fixtures (mock clients, sample configs)
│   ├── test_agent.py     # Agent execution and loop detection tests
│   ├── test_config.py    # Pydantic config validation tests
│   └── test_mcp_client.py # MCP client HTTP tests with aioresponses
├── agent/
│   ├── __init__.py
│   └── agent.py
├── orchestrator/
│   ├── __init__.py
│   └── orchestrator.py
├── mcp/
│   ├── __init__.py
│   └── client.py
├── reasoning/
│   ├── __init__.py
│   └── engine.py
├── prompts/
│   ├── __init__.py
│   ├── templates.py      # Prompt loader
│   └── reasoning.txt     # LLM prompts as .txt files (not in source code)
├── mode_selector/
│   ├── __init__.py
│   └── selector.py
└── utils/
    ├── __init__.py
    ├── exceptions.py     # Custom exception hierarchy
    ├── config.py         # Pydantic configuration models
    ├── interfaces.py     # Protocol definitions for DI/testing
    ├── logger.py
    └── timer.py
```

**Note**: Prompts are kept separate from reasoning logic (SOLID - Single Responsibility). The `prompts/` folder contains all LLM prompt templates as `.txt` files with XML tags and examples, making them easy to modify without touching source code.

### Configuration (`utils/config.py`)

Configuration uses Pydantic v2 models with validation:

```python
class AppConfig(BaseModel):
    llm: LLMConfig
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    agent: AgentConfig = Field(default_factory=AgentConfig)
    mcp: MCPConfig
    mode_selector: ModeSelectorConfig = Field(default_factory=ModeSelectorConfig)

class MCPConfig(BaseModel):
    server_url: str
    timeout_seconds: int = Field(default=30, gt=0)
    max_retries: int = Field(default=3, ge=0)

    @field_validator("server_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("server_url must start with http:// or https://")
        return v
```

### Configuration (config.json)

```json
{
  "llm": {
    "model": "gemini/gemini-2.5-flash-lite"
  },
  "logging": {
    "level": "INFO",
    "console": {
      "enabled": true,
      "renderer": "pretty"
    },
    "file": {
      "enabled": true,
      "level": "DEBUG",
      "path": "logs/agent_runtime.log",
      "rotation": {
        "enabled": true,
        "max_bytes": 10485760,
        "backup_count": 5
      }
    }
  },
  "agent": {
    "loop_detection_window": 5,
    "loop_detection_threshold": 3
  },
  "mcp": {
    "server_url": "http://localhost:8000",
    "timeout_seconds": 30,
    "max_retries": 3,
    "retry_delay_seconds": 2
  },
  "mode_selector": {
    "similarity_threshold": 0.90,
    "min_executions": 10,
    "min_success_rate": 0.85
  }
}
```

**Note**: The LLM model uses LiteLLM format (`provider/model`). No arbitrary `max_steps` limit - agents run until goal completion or loop detection.

### Utilities

#### Logger (`utils/logger.py`)

Structured logging using `structlog` with:
- Pretty console output for development
- JSON file output for production/analysis
- Automatic context binding (workflow_id, agent_name)
- Log rotation support

#### ASCII Block Timer (`utils/timer.py`)

Visual profiling utility that displays timing as ASCII blocks:

```
┌─────────────────────────────────────────────────────────┐
│ WORKFLOW TIMING: w-123                                  │
├─────────────────────────────────────────────────────────┤
│ orchestrator:delegate   ██                        120ms │
│ agent:reason            ████████                  450ms │
│ tool:check_ticket       ███                       230ms │
│ agent:reason            ██████                    380ms │
│ tool:search_kb          ████                      180ms │
│ tool:close_ticket       ███                       150ms │
├─────────────────────────────────────────────────────────┤
│ TOTAL                                            1510ms │
└─────────────────────────────────────────────────────────┘
```

### Key Components

| Class | Responsibility |
|-------|----------------|
| `Agent` | Individual autonomous agent with reasoning capabilities |
| `Orchestrator` | Coordinates multiple agents, delegates tasks, tracks workflow state |
| `MCPClient` | Async client for communicating with MCP tool servers (aiohttp) |
| `ModeSelector` | Decides exploration vs guided execution based on semantic search |
| `ReasoningEngine` | Async LLM integration via LiteLLM (acompletion) for agent decision-making |

### Async Architecture

All I/O operations are fully async using `asyncio`:

```python
# Entry point
async def main() -> None:
    config = load_config()  # Pydantic validation
    mcp_client = MCPClient(server_url=config.mcp.server_url)

    if not await mcp_client.connect():  # aiohttp
        return

    try:
        result = await orchestrator.execute(task)
    finally:
        await mcp_client.close()

if __name__ == "__main__":
    asyncio.run(main())
```

**Key async patterns**:
- `MCPClient` uses `aiohttp.ClientSession` for HTTP calls
- `ReasoningEngine` uses `litellm.acompletion()` for LLM calls
- `Agent.execute()` awaits both reasoning and tool calls
- Proper resource cleanup with `async with` and `finally` blocks

### Protocol Interfaces (`utils/interfaces.py`)

Protocols enable dependency injection and testability:

```python
class ReasoningEngineProtocol(Protocol):
    async def reason(self, task: str, context: str, tools_doc: str,
                     history: list[dict] | None = None) -> dict[str, Any]: ...

class MCPClientProtocol(Protocol):
    async def connect(self) -> bool: ...
    async def call_tool(self, tool_name: str, parameters: dict) -> dict[str, Any]: ...
    def get_tools_documentation(self) -> str: ...
    async def close(self) -> None: ...

class AgentProtocol(Protocol):
    name: str
    role: str
    async def execute(self, task: str, context: str = "") -> dict[str, Any]: ...
```

### Custom Exceptions (`utils/exceptions.py`)

Typed exception hierarchy for precise error handling:

```python
class AgentRuntimeError(Exception): ...      # Base for all errors
class ConfigurationError(AgentRuntimeError): ...  # Config validation
class MCPConnectionError(AgentRuntimeError): ...  # Server unreachable
class MCPToolError(AgentRuntimeError): ...        # Tool not found
class ReasoningError(AgentRuntimeError): ...      # LLM API errors
class LoopDetectedError(AgentRuntimeError): ...   # Agent stuck
class PromptLoadError(AgentRuntimeError): ...     # Template not found
```

### Agent Prompt Structure (`prompts/reasoning.txt`)

The agent prompt uses XML tags and includes:

| Section | Purpose |
|---------|---------|
| `<role>` | Defines agent as autonomous tool executor |
| `<goal>` | Current task to accomplish |
| `<context>` | Additional context if provided |
| `<execution_history>` | Previous actions and results |
| `<available_tools>` | Tools the agent can call |
| `<core_principles>` | Behavioral guidelines |
| `<execution_approach>` | Step-by-step methodology |
| `<parameter_inference>` | How to derive tool parameters |
| `<response_format>` | JSON output format |

**Core Principles**:
- **Always Try Before Concluding**: Never assume info unavailable without trying tools
- **History is Your Only Memory**: Only trust recorded actions
- **Never Repeat Successful Actions**: Check history before executing
- **One Action at a Time**: Single tool per response
- **Explore Before Giving Up**: Try alternatives before concluding impossible
- **Complete Means Complete**: Only mark complete when all subtasks done

### ReasoningEngine JSON Parsing

The `ReasoningEngine` includes robust JSON extraction that handles:
- Markdown code blocks (` ```json ... ``` `)
- Prose before/after JSON (extracts first `{` to last `}`)
- Retries on parse failure

### Orchestrator Role

The orchestrator does **not** dictate exact steps. Instead it:
- Receives incoming tasks
- Delegates to appropriate agents based on task type
- Tracks workflow state across agent handoffs
- Logs orchestration events (delegate, handoff, complete)
- Monitors for loop detection (agents stuck repeating actions)

Agents make their own decisions about which tools to call and in what order. This produces **path diversity** across runs.

### Dependencies

```toml
[project]
dependencies = [
    "litellm>=1.0.0",
    "aiohttp>=3.9.0",      # Async HTTP client (replaced requests)
    "pydantic>=2.5.0",
    "python-dotenv>=1.0.0",
    "structlog>=24.1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.1.0",
    "aioresponses>=0.7.6",  # Mock aiohttp for testing
    "ruff>=0.1.0",
    "mypy>=1.7.0",
]
```

**Notes**:
- Uses LiteLLM for multi-provider LLM support (Gemini, OpenAI, Anthropic, etc.)
- All HTTP operations use `aiohttp` (async) instead of `requests` (blocking)
- No direct database access - logs events via `event-logger` library

---

## Repository 2: `mcp-tool-server`

**Purpose**: Model Context Protocol server exposing tools for agents to call

### Key Components

- MCP server implementation (JSON-RPC 2.0 spec)
- Tool definitions with input/output schemas
- Business logic for customer support tools
- API integrations (mock or real)

### Tools Exposed

| Tool | Description |
|------|-------------|
| `check_ticket_status` | Retrieve current status of a support ticket |
| `get_order_details` | Get details of a customer order including items, total, and payment status |
| `check_refund_eligibility` | Check if an order is eligible for refund based on policy |
| `process_refund` | Process a refund for an eligible order |
| `send_customer_message` | Send a message to the customer via email |
| `close_ticket` | Mark ticket as resolved with resolution summary |
| `get_customer_history` | Retrieve past orders and tickets for a customer |
| `search_knowledge_base` | Search internal documentation for policies and procedures |

### Tool Schemas

```json
{
  "tools": [
    {
      "name": "check_ticket_status",
      "description": "Retrieve current status of a support ticket",
      "input_schema": {
        "type": "object",
        "properties": {
          "ticket_id": {"type": "string"}
        },
        "required": ["ticket_id"]
      }
    },
    {
      "name": "get_order_details",
      "description": "Get details of a customer order including items, total, and payment status",
      "input_schema": {
        "type": "object",
        "properties": {
          "order_id": {"type": "string"}
        },
        "required": ["order_id"]
      }
    },
    {
      "name": "check_refund_eligibility",
      "description": "Check if an order is eligible for refund based on policy",
      "input_schema": {
        "type": "object",
        "properties": {
          "order_id": {"type": "string"}
        },
        "required": ["order_id"]
      }
    },
    {
      "name": "process_refund",
      "description": "Process a refund for an eligible order",
      "input_schema": {
        "type": "object",
        "properties": {
          "order_id": {"type": "string"},
          "amount": {"type": "number"},
          "reason": {"type": "string"}
        },
        "required": ["order_id", "amount", "reason"]
      }
    },
    {
      "name": "send_customer_message",
      "description": "Send a message to the customer via email",
      "input_schema": {
        "type": "object",
        "properties": {
          "customer_id": {"type": "string"},
          "subject": {"type": "string"},
          "message": {"type": "string"}
        },
        "required": ["customer_id", "subject", "message"]
      }
    },
    {
      "name": "close_ticket",
      "description": "Mark ticket as resolved with a resolution summary",
      "input_schema": {
        "type": "object",
        "properties": {
          "ticket_id": {"type": "string"},
          "resolution_summary": {"type": "string"}
        },
        "required": ["ticket_id", "resolution_summary"]
      }
    },
    {
      "name": "get_customer_history",
      "description": "Retrieve past orders and tickets for a customer",
      "input_schema": {
        "type": "object",
        "properties": {
          "customer_id": {"type": "string"}
        },
        "required": ["customer_id"]
      }
    },
    {
      "name": "search_knowledge_base",
      "description": "Search internal documentation for policies and procedures",
      "input_schema": {
        "type": "object",
        "properties": {
          "query": {"type": "string"}
        },
        "required": ["query"]
      }
    }
  ]
}
```

### Dependencies

```
fastapi==0.104.1
uvicorn==0.24.0
pydantic==2.5.0
```

**Note**: No database access - stateless tool execution only

---

## Repository 3: `event-logger`

**Purpose**: Structured event logging library (installed as pip package in `agent-runtime`)

### Key Components

| Class | Responsibility |
|-------|----------------|
| `EventLogger` | Main logging interface |
| `Event` | Structured event dataclass (see Event Log Structure above) |
| Connection pool | Database connection management |
| Batch writer | Async batch writing for performance |

### Installation

```bash
pip install git+https://github.com/your-org/event-logger.git
```

### Usage

```python
from event_logger import EventLogger, Event

logger = EventLogger(db_url="postgresql://localhost/agents")

# Log a tool call event
event = Event(
    workflow_id="w-123",
    activity="tool_call:check_ticket_status",
    agent_name="TriageAgent",
    agent_role="triage",
    tool_name="check_ticket_status",
    tool_parameters={"ticket_id": "T-12345"},
    tool_response={"status": "open"},
    llm_model="gemini-1.5-pro",
    llm_prompt_tokens=1500,
    llm_completion_tokens=200,
    llm_reasoning="Customer issue unclear, checking ticket status first",
    duration_ms=245.3,
    cost_usd=0.0003,
    status="success",
    step_number=4
)

logger.log(event)
```

### Dependencies

```
psycopg2-binary==2.9.9
sqlalchemy==2.0.23
pydantic==2.5.0
```

**Note**: Direct database write access - writes to `event_logs` table

---

## Repository 4: `analytics-db`

**Purpose**: PostgreSQL database with pgvector + semantic search + workflow optimization

### Structure

```
analytics-db/
├── migrations/
│   ├── 001_initial_schema.sql
│   ├── 002_add_pgvector.sql
│   └── 003_workflow_graphs.sql
├── semantic_search.py
├── process_mining.py
├── pathfinding.py
├── background_jobs.py
└── docker-compose.yml
```

### Key Components

| Component | Responsibility |
|-----------|----------------|
| `SemanticSearch` | Vector search for similar past workflows |
| `ProcessMiningEngine` | PM4Py integration for discovering workflow patterns |
| `WorkflowOptimizer` | Finds fastest paths through discovered process models |
| `BackgroundJobs` | Periodic analysis of accumulated event logs |

### Process Mining Pipeline

```
1. Collect Events
   └─ event_logs table accumulates actions from many workflow runs

2. Extract Traces (per workflow_id)
   └─ Group events by workflow_id, order by timestamp
   └─ Each trace = sequence of activities for one run

3. Apply Process Mining (PM4Py)
   └─ Inductive Miner / Heuristic Miner discovers process model
   └─ Model shows all observed paths through the workflow

4. Annotate with Metrics
   └─ For each edge in process model, calculate:
      - Average duration_ms
      - Average cost_usd
      - Frequency (how often this path was taken)
      - Success rate

5. Find Optimal Path
   └─ Dijkstra's algorithm with edge weights = duration or cost
   └─ Returns: fastest sequence of activities

6. Store for Reuse
   └─ workflow_graphs: discovered process model
   └─ workflow_embeddings: task description → optimal path mapping
```

### Dependencies

```
psycopg2-binary==2.9.9
pgvector==0.2.4
pm4py==2.7.11
litellm>=1.0.0
sqlalchemy==2.0.23
```

**Note**: Reads from `event_logs`, writes to `workflow_graphs` and `workflow_embeddings`. Uses LiteLLM for embedding generation.

---

## Repository 5: `demo-harness`

**Purpose**: End-to-end demonstration and experimentation

### Key Components

| Component | Responsibility |
|-----------|----------------|
| Task generator | Creates test scenarios |
| Experiment runner | Runs N workflows, collects metrics |
| Results visualizer | Generates graphs for analysis |
| Config manager | Configuration management |

### Dependencies

```
agent-runtime           # Local dependency
matplotlib==3.8.2
pandas==2.1.4
jupyter==1.0.0
```

---

## Two Execution Modes

### Exploration Mode

- Agents make autonomous decisions using LLM reasoning
- No constraints on which tools to call or in what order
- Path diversity emerges naturally from LLM non-determinism
- All actions logged for later analysis
- **Goal**: Accumulate diverse workflow traces

### Guided Mode

- Semantic search finds similar past tasks
- If match found with high confidence + success rate:
  - Retrieve optimal path from `workflow_graphs`
  - Constrain agent to follow discovered sequence
- Agents still use LLM reasoning, but tool choices are guided
- **Goal**: Execute faster using learned knowledge

### Mode Selection Logic

```python
class ModeSelector:
    SIMILARITY_THRESHOLD = 0.90
    MIN_EXECUTIONS = 10
    MIN_SUCCESS_RATE = 0.85

    def select_mode(self, task_description: str) -> tuple[str, OptimalPath | None]:
        # Search for similar past tasks
        matches = self.semantic_search.find_similar(task_description)

        if not matches:
            return ("exploration", None)

        best_match = matches[0]

        # Check if we have enough confidence to guide
        if (best_match.similarity >= self.SIMILARITY_THRESHOLD and
            best_match.execution_count >= self.MIN_EXECUTIONS and
            best_match.success_rate >= self.MIN_SUCCESS_RATE):

            optimal_path = self.get_optimal_path(best_match.workflow_type)
            return ("guided", optimal_path)

        # Not enough confidence yet - keep exploring
        return ("exploration", None)
```

---

## Data Flow

```
User Input ("Handle ticket T-12345")
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│                      agent-runtime                           │
│                                                              │
│  ┌─────────────┐                                            │
│  │ ModeSelector│──── queries ────▶ analytics-db             │
│  └──────┬──────┘                   (semantic search)        │
│         │                                                    │
│         ▼ exploration or guided                              │
│  ┌─────────────┐                                            │
│  │ Orchestrator│                                            │
│  └──────┬──────┘                                            │
│         │ delegates                                          │
│         ▼                                                    │
│  ┌─────────────┐    tool calls    ┌──────────────────────┐  │
│  │   Agents    │─────────────────▶│   mcp-tool-server    │  │
│  │ (Triage,    │◀─────────────────│   (tool execution)   │  │
│  │  Resolver,  │    responses     └──────────────────────┘  │
│  │  Escalation)│                                            │
│  └──────┬──────┘                                            │
│         │                                                    │
│         │ logs every action                                  │
│         ▼                                                    │
│  ┌─────────────┐                                            │
│  │event-logger │────────────▶ PostgreSQL (event_logs)       │
│  └─────────────┘                                            │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ periodic analysis
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      analytics-db                            │
│                                                              │
│  ┌────────────────┐    ┌─────────────────┐                  │
│  │ Process Mining │───▶│ Workflow Graphs │                  │
│  │ (PM4Py)        │    │ (optimal paths) │                  │
│  └────────────────┘    └─────────────────┘                  │
│           │                     │                            │
│           ▼                     ▼                            │
│  ┌────────────────┐    ┌─────────────────┐                  │
│  │ Pathfinding    │    │ Semantic Index  │                  │
│  │ (Dijkstra)     │    │ (pgvector)      │                  │
│  └────────────────┘    └─────────────────┘                  │
└─────────────────────────────────────────────────────────────┘
```

---

## Deployment (Docker Compose)

```
┌────────────────────────────────────┐
│  agent-runtime                     │
│  Python 3.11                       │
│  Env: GEMINI_API_KEY, MCP_URL, DB  │
└────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────┐
│  mcp-tool-server                   │
│  FastAPI + Uvicorn                 │
│  Port: 8000                        │
└────────────────────────────────────┘

┌────────────────────────────────────┐
│  postgres-pgvector                 │
│  PostgreSQL 16 + pgvector          │
│  Port: 5432                        │
│  Volume: ./data                    │
└────────────────────────────────────┘

┌────────────────────────────────────┐
│  analytics-worker                  │
│  Background analysis jobs          │
│  Connects to PostgreSQL            │
└────────────────────────────────────┘
```

---

## Configuration

### agent-runtime/.env

```env
GEMINI_API_KEY=your_key_here
MCP_SERVER_URL=http://mcp-tool-server:8000
DB_URL=postgresql://user:pass@postgres:5432/agents
```

**Note**: LiteLLM automatically uses `GEMINI_API_KEY` for Gemini models. For other providers, set the appropriate key (e.g., `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`).

### mcp-tool-server/.env

```env
PORT=8000
TOOL_TIMEOUT=30
MOCK_MODE=false
```

### analytics-db/.env

```env
DB_URL=postgresql://user:pass@postgres:5432/agents
GEMINI_API_KEY=your_key_here
PROCESS_MINING_INTERVAL=10
MIN_WORKFLOWS_FOR_ANALYSIS=10
SIMILARITY_THRESHOLD=0.85
```

**Note**: Uses Gemini for generating embeddings for semantic search.

---

## Pitfalls & Mitigations

### 1. LLM Hallucinating Tool Names

**Problem**: LLM invents tools that don't exist

**Mitigation**:
- Strict prompt formatting with explicit tool list
- Retry logic with constraints on failure
- Runtime validation before MCP calls

### 1b. LLM Invalid JSON Output

**Problem**: LLM returns prose before/after JSON, or wraps JSON in markdown code blocks

**Mitigation**:
- Robust JSON extraction in `ReasoningEngine._clean_json()`
- First tries extracting from ` ```json ``` ` blocks
- Falls back to finding first `{` and last `}` to extract JSON object
- Automatic retry on parse failure

### 2. Invalid Parameter Formats

**Problem**: Wrong data types or missing required fields

**Mitigation**:
- Pydantic validation against JSON schemas
- Clear error messages for retry

### 3. Circular Reasoning Loops

**Problem**: Agent calls same tool repeatedly without progress

**Mitigation**:
```python
class Agent:
    def execute_action(self, action):
        recent_actions = self.action_history[-5:]
        if recent_actions.count(action["action"]) >= 3:
            raise LoopDetectedError("Agent stuck in loop")
```

### 4. Infinite Loops

**Problem**: Agent gets stuck repeating the same actions without progress

**Mitigation**:
- Loop detection: If the same action appears 3+ times in the last 5 actions, terminate
- Agents run until goal completion with no arbitrary step limit
- Clear prompt instructions: "Never Repeat Successful Actions" principle
- Prompt includes "Complete Means Complete" to prevent premature completion

### 5. MCP Server Downtime

**Problem**: MCP server unreachable

**Mitigation**:
- Retry logic with exponential backoff
- `MAX_RETRIES = 3`, `RETRY_DELAY = 2s`

### 6. Semantic Search Returns Irrelevant Workflows

**Problem**: Vector similarity doesn't capture semantics well

**Mitigation**:
- High similarity threshold: `0.90`
- Require minimum execution count: `10`
- Require success rate: `> 0.85`

### 7. Database Connection Pool Exhaustion

**Problem**: High-frequency logging overwhelms connections

**Mitigation**:
- Connection pooling (`pool_size=20`, `max_overflow=10`)
- Batch writes (`batch_size=100`)

### 8. Process Mining on Sparse Data

**Problem**: PM4Py needs minimum event density

**Mitigation**:
- Minimum workflows: `10`
- Minimum events per workflow: `3`

### 9. Pathfinding on Disconnected Graph

**Problem**: Dijkstra fails on unreachable nodes

**Mitigation**:
- Check connectivity before pathfinding
- Raise `DisconnectedGraphError` with clear message

### 10. Embedding Drift Over Time

**Problem**: Model updates change vector space

**Mitigation**:
- Store `model_version` with each embedding
- Only compare embeddings from same model version

---

## Testing Strategy

### Unit Tests

| Repository | Coverage |
|------------|----------|
| agent-runtime | Agent execution, loop detection, config validation, MCP client HTTP |
| mcp-tool-server | Each tool's business logic |
| event-logger | Event serialization, batch writing, schema validation |
| analytics-db | Semantic search, pathfinding, process mining |

### agent-runtime Test Suite

```bash
# Run all tests
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ --cov=. --cov-report=term-missing
```

**Test fixtures** (`tests/conftest.py`):

```python
@pytest.fixture
def mock_mcp_client() -> AsyncMock:
    """Mock MCP client with predefined tools."""
    client = AsyncMock()
    client.connect = AsyncMock(return_value=True)
    client.get_tools_documentation = lambda: "Available tools: ..."
    return client

@pytest.fixture
def mock_reasoning_engine() -> AsyncMock:
    """Mock reasoning engine for testing agents."""
    return AsyncMock()

@pytest.fixture
def sample_config() -> AppConfig:
    """Valid AppConfig for testing."""
    return AppConfig(
        llm=LLMConfig(model="gpt-4"),
        mcp=MCPConfig(server_url="http://localhost:8000"),
    )
```

**Key test classes**:
- `TestAgent` - Execution flow, tool calls, loop detection
- `TestLoopDetection` - Algorithm edge cases
- `TestMCPClient` - HTTP mocking with `aioresponses`
- `TestAppConfig` - Pydantic validation

### Integration Tests

- End-to-end workflow execution
- MCP communication
- Event log integrity (all actions captured with correct agent_name)
- Process mining on synthetic event data

### Experiment Harness

```python
class ExperimentRunner:
    def run_exploration_phase(self, num_runs=50):
        """Run workflows in exploration mode to accumulate diverse traces"""
        for i in range(num_runs):
            task = self.generate_test_task()
            metrics = self.runtime.execute(task, mode="exploration")
            self.results.append(metrics)

    def trigger_analysis(self):
        """Run process mining on accumulated logs"""
        self.analytics.run_process_mining()
        self.analytics.compute_optimal_paths()

    def run_guided_phase(self, num_runs=50):
        """Run workflows using learned optimal paths"""
        for i in range(num_runs):
            task = self.generate_test_task()
            metrics = self.runtime.execute(task, mode="auto")  # Will select guided
            self.results.append(metrics)

    def compare_results(self):
        """Generate comparison metrics"""
        exploration_metrics = self.results[:50]
        guided_metrics = self.results[50:]

        print(f"Exploration avg duration: {avg(e.duration_ms for e in exploration_metrics)}ms")
        print(f"Guided avg duration: {avg(g.duration_ms for g in guided_metrics)}ms")
        print(f"Exploration avg cost: ${avg(e.cost_usd for e in exploration_metrics)}")
        print(f"Guided avg cost: ${avg(g.cost_usd for g in guided_metrics)}")
```

---

## Success Criteria

- [ ] Agents successfully call MCP tools without hallucinating endpoints
- [ ] Event logging captures all workflow actions with correct `agent_name`
- [ ] Process mining discovers meaningful patterns from logs
- [ ] Semantic search returns relevant workflows (>85% precision)
- [ ] Guided mode shows measurable improvement over exploration (duration, cost, API calls)
- [ ] System handles failures gracefully (retries, fallbacks)
- [ ] Reduced total LLM API calls in guided mode vs exploration
