# A2A vs MCP - Clarification

## What AFGA Uses: A2A Protocol ✅

**AFGA uses the A2A (Agent-to-Agent) Protocol ONLY.**

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

### What is MCP? (NOT USED)

**Model Context Protocol (MCP):**
- **Purpose:** Connecting LLMs to tools, data sources, and resources
- **Use Case:** Single LLM accessing external tools (like function calling)
- **Provider:** Anthropic/Claude team
- **NOT applicable to:** Multi-agent orchestration

**MCP is for:**
- LLM → Database connection
- LLM → API tool calls
- LLM → File system access
- LLM → External resources

**AFGA doesn't need MCP because:**
- We don't expose tools to LLMs
- We use agents with predefined workflows
- A2A handles agent communication
- Each agent has its own LangGraph logic

## Why the Confusion?

I incorrectly wrote "A2A/MCP" throughout the docs, conflating two separate protocols:
- ❌ "A2A/MCP" - Wrong terminology
- ✅ "A2A Protocol" - What we actually use

## What We Actually Implemented

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

### What We DON'T Use

```python
# MCP components (NOT in our project)
from mcp import Server, Tool, Resource  # ← Not imported anywhere
from mcp.server import stdio  # ← Not used

# We don't create MCP servers
# We don't expose tools via MCP
# We don't use MCP client-server pattern
```

## Correct Terminology Going Forward

### ✅ Correct
- "A2A Protocol"
- "Agent-to-Agent communication"
- "A2A-based multi-agent system"
- "Using a2a-sdk"

### ❌ Incorrect (Previously Used)
- "A2A/MCP" - These are separate protocols
- "MCP standards" - Not relevant to A2A
- "A2A with MCP" - Conflating two things

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
- ✅ A2A Protocol (Agent-to-Agent) via `a2a-sdk`
- ✅ LangGraph for agent state machines
- ✅ OpenRouter for LLM calls
- ❌ NOT using MCP (Model Context Protocol)

**Correction:**
- All documentation updated to remove MCP references
- Only A2A protocol is mentioned
- Accurate technical description

---

**Thank you for catching this! The documentation is now technically accurate.** ✅

