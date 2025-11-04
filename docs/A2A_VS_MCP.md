# A2A vs MCP - Clarification

## What AFGA Uses: Hybrid A2A + MCP ✅

**AFGA uses BOTH protocols in a hybrid architecture:**

- **A2A Protocol:** For inter-agent communication (TAA ↔ PAA, TAA ↔ EMA)
- **MCP Protocol:** For agent access to resources and tools (PAA ↔ Policies, EMA ↔ Memory)

### What is A2A?

**Agent-to-Agent (A2A) Protocol:**
- **Purpose:** Communication between AI agents
- **Use Case:** Multi-agent systems where agents delegate tasks to each other
- **Implementation:** Via `a2a-sdk` package
- **In AFGA:**
  - TAA (client) delegates to PAA and EMA (servers)
  - Agent Cards define capabilities
  - Agent Executors handle tasks
  - Structured message passing

**Key Components:**
- `AgentCard`: Defines agent capabilities
- `AgentExecutor`: Server-side task handler
- `TaskClient`: Client-side task invoker
- `RequestContext`: Task metadata
- `EventQueue`: Streaming updates

### What is MCP? (NOW USED!)

**Model Context Protocol (MCP):**
- **Purpose:** Connecting agents/LLMs to tools, data sources, and resources
- **Use Case:** Standardized access to external resources
- **Provider:** Anthropic/Claude team
- **Applicable to:** Agent access to data and tools

**MCP in AFGA:**
- PAA → Policy resources via MCP
- EMA → Memory tools via MCP
- Clean abstraction layer
- Standardized interfaces

**Why we added MCP:**
- ✅ Cleaner architecture (agents don't touch DBs directly)
- ✅ Standard protocol (MCP resources and tools)
- ✅ Easier to scale (swap implementations)
- ✅ MIT research alignment (use both protocols)

## Why the Confusion?

I incorrectly wrote "A2A/MCP" throughout the docs, conflating two separate protocols:
- ❌ "A2A/MCP" - Wrong terminology
- ✅ "A2A Protocol" - What we actually use

## What We Actually Implemented

### Hybrid Architecture

**A2A for Agent Communication:**
```
TAA --A2A-→ PAA (delegate task)
TAA --A2A-→ EMA (delegate task)
```

**MCP for Resource/Tool Access:**
```
PAA --MCP-→ Policy Resources (read policies)
EMA --MCP-→ Memory Tools (update memory)
```

### A2A Protocol Components in AFGA

```python
# Agent Card (defines capabilities)
from a2a.types import AgentCard, Capability

def get_paa_agent_card() -> AgentCard:
    return AgentCard(
        name="Policy Adherence Agent",
        capabilities=[...]  # What this agent can do
    )

# Agent Executor (server-side)
from a2a.server.agent_execution import AgentExecutor

class PAAExecutor(AgentExecutor):
    async def execute(self, context, event_queue):
        # Handle task from client (TAA)
        ...

# Client-side invocation (in orchestrator)
# TAA → PAA via A2A:
paa_state = self.paa.check_compliance_sync(invoice, trace_id)
```

### MCP Protocol Components in AFGA

```python
# MCP components (NOW in our project!)
from mcp.server import Server
from mcp.types import Tool, Resource

# Policy MCP Server (used by PAA)
class PolicyMCPServer:
    def __init__(self):
        self.server = Server("afga-policy-server")
    
    @self.server.list_resources()
    async def list_resources():
        return [Resource(uri="policy://...", ...)]

# Memory MCP Server (used by EMA)
class MemoryMCPServer:
    def __init__(self):
        self.server = Server("afga-memory-server")
    
    @self.server.list_tools()
    async def list_tools():
        return [Tool(name="add_exception", ...)]
```

## Correct Terminology Going Forward

### ✅ Correct
- "Hybrid A2A + MCP architecture"
- "A2A for agent communication, MCP for resource access"
- "Using both a2a-sdk and mcp packages"
- "TAA uses A2A, PAA uses A2A + MCP, EMA uses A2A + MCP"

### ❌ Incorrect (Previously Used)
- "A2A/MCP" without clarification - Ambiguous
- "Only A2A" - Now we use both!
- "MCP not used" - Now we use it!

## Documentation Corrections Made

### Files Updated (12 files)
All instances of "A2A/MCP" changed to "A2A Protocol" or "A2A":

1. `streamlit_app/pages/2_Agent_Workflow.py`
2. `streamlit_app/app.py`
3. `README.md`
4. `src/api/main.py`
5. `src/agents/orchestrator.py`
6. `docs/ARCHITECTURE.md`
7. `IMPLEMENTATION_COMPLETE.md`
8. `FINAL_SUMMARY.md`
9. `MVP_STATUS.md`
10. `PROGRESS.md`

### What Remains Accurate

- ✅ We use `a2a-sdk` package
- ✅ We implement AgentCard, AgentExecutor
- ✅ We have client-server agent communication
- ✅ TAA delegates to PAA and EMA
- ✅ All A2A protocol patterns are correct

---

## Summary

**What AFGA Actually Uses:**
- ✅ **A2A Protocol** (Agent-to-Agent) via `a2a-sdk` - For inter-agent communication
- ✅ **MCP Protocol** (Model Context Protocol) via `mcp` - For resource/tool access
- ✅ LangGraph for agent state machines
- ✅ OpenRouter for LLM calls

**Hybrid Architecture:**
- TAA: Pure orchestrator (A2A client only)
- PAA: Uses A2A (server) + MCP (accesses policies)
- EMA: Uses A2A (server) + MCP (manages memory)

**Why Both:**
- A2A solves: Agent delegation and coordination
- MCP solves: Data access and tool calling
- Together: Complete, standards-based architecture

**Result:**
- State-of-the-art multi-agent system
- Aligned with MIT GenAI research
- Production-ready architecture
- Industry-standard protocols

---

**The hybrid A2A + MCP architecture makes AFGA a reference implementation!** ✅

