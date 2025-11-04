# Hybrid A2A + MCP Architecture

## Overview

AFGA implements a **sophisticated hybrid architecture** combining two industry-standard protocols:

1. **A2A (Agent-to-Agent)** - For inter-agent communication
2. **MCP (Model Context Protocol)** - For agent access to resources and tools

This follows **MIT GenAI research** recommendations for scalable, governable AI systems.

---

## Why Two Protocols?

### Different Problems, Different Solutions

**A2A Protocol** solves: "How do agents communicate with each other?"
- TAA needs to ask PAA to check compliance
- TAA needs to ask EMA to process feedback
- Agents coordinate and delegate tasks

**MCP Protocol** solves: "How do agents access data and tools?"
- PAA needs to read policy documents
- EMA needs to update memory database
- Agents operate on external resources

### Separation of Concerns

```
┌─────────────┐
│     TAA     │  ← Pure orchestrator (no MCP needed)
│ (Client)    │
└──────┬──────┘
       │ A2A (delegates tasks)
       ├─────────────┬────────────────┐
       │             │                │
   ┌───▼───┐     ┌──▼───┐       ┌────▼────┐
   │  PAA  │     │ EMA  │       │   ...   │
   │(Server│     │(Server│       │         │
   └───┬───┘     └──┬───┘       └─────────┘
       │            │
       │ MCP        │ MCP
       │(access     │(tools)
       │resources)  │
       │            │
   ┌───▼───┐    ┌──▼────┐
   │Policies│    │Memory │
   │  (MCP  │    │ (MCP  │
   │Server) │    │Server)│
   └────────┘    └───────┘
```

---

## A2A Protocol in AFGA

### What It Does

**Agent Orchestration:**
- TAA delegates compliance checking to PAA
- TAA delegates HITL processing to EMA
- Structured task-based communication
- Async/streaming support

### Components

**Agent Cards** (`agent_card.py`):
```python
from a2a.types import AgentCard, Capability

def get_paa_agent_card() -> AgentCard:
    return AgentCard(
        name="Policy Adherence Agent",
        capabilities=[
            Capability(
                name="policy_checking",
                description="Check transaction compliance",
                input_schema={...},
                output_schema={...}
            )
        ]
    )
```

**Agent Executors** (`agent_executor.py`):
```python
from a2a.server.agent_execution import AgentExecutor

class PAAExecutor(AgentExecutor):
    async def execute(self, context, event_queue):
        # Receive task from TAA
        # Run PAA's LangGraph workflow
        # Return compliance result
```

**Client Invocation** (in orchestrator):
```python
# TAA invokes PAA via A2A
paa_state = self.paa.check_compliance_sync(invoice, trace_id)
```

---

## MCP Protocol in AFGA

### What It Does

**Resource & Tool Access:**
- PAA reads policy documents through MCP resources
- EMA manipulates memory through MCP tools
- Clean abstraction layer
- Standardized interfaces

### MCP Servers Implemented

#### 1. PolicyMCPServer (for PAA)

**Location:** `src/mcp_servers/policy_server.py`

**Exposes:**
```python
# MCP Resources
policy://vendor_approval_policy
policy://expense_limits_policy
policy://po_matching_requirements
policy://international_transaction_rules
policy://exception_management_policy
```

**Usage by PAA:**
```python
# In PAA's retrieve_policies node:
policies = self.policy_mcp.search_relevant_policies_sync(invoice, top_k=5)
# Returns: Policy chunks relevant to this invoice
```

**Benefits:**
- PAA doesn't access file system directly
- Policies exposed through standard MCP interface
- Easy to swap implementations (files → database → API)

#### 2. MemoryMCPServer (for EMA)

**Location:** `src/mcp_servers/memory_server.py`

**Exposes:**
```python
# MCP Tools
add_exception(vendor, category, rule_type, description, reason)
query_exceptions(vendor, category, rule_type, min_success_rate)
update_exception_usage(exception_id, success)
get_memory_stats()
calculate_crs(date)
```

**Usage by EMA:**
```python
# In EMA's update_memory node:
exception_id = self.memory_mcp.add_exception_sync(
    vendor=invoice.vendor,
    category=invoice.category,
    rule_type="recurring",
    description="Learned rule",
    reason="Human override"
)
# Returns: Exception ID
```

**Benefits:**
- EMA doesn't access database directly
- Memory operations exposed as callable tools
- LLM could theoretically call these tools directly
- Clean separation of concerns

---

## How They Work Together

### Complete Transaction Flow

```
1. User submits invoice
   ↓
2. FastAPI → TAA.process_transaction()
   ↓
3. TAA: Risk assessment (internal logic, no protocols)
   ↓
4. TAA → PAA via A2A
   │
   ├─→ A2A: Task delegation
   │   Message: "Check compliance for this invoice"
   │
   └─→ PAA receives task
       │
       ├─→ MCP: Access policy resources
       │   PAA → PolicyMCPServer
       │   Retrieves: Relevant policy chunks
       │
       ├─→ MCP: Access memory (via MemoryManager)
       │   PAA → Memory database
       │   Retrieves: Learned exceptions
       │
       ├─→ LLM: Evaluate compliance
       │   Input: Invoice + Policies + Memory
       │   Output: is_compliant, confidence
       │
       └─→ A2A: Return result to TAA
   
5. TAA: Make final decision
   ↓
6. Return to user
```

### HITL Feedback Flow

```
1. Human provides feedback
   ↓
2. FastAPI → TAA → EMA via A2A
   │
   ├─→ A2A: Task delegation
   │   Message: "Process this HITL feedback"
   │
   └─→ EMA receives task
       │
       ├─→ LLM: Analyze correction type
       │   Input: Feedback + Original decision
       │   Output: should_learn, exception_type
       │
       ├─→ MCP: Add exception to memory
       │   EMA → MemoryMCPServer
       │   Tool: add_exception()
       │   Result: Exception ID
       │
       ├─→ MCP: Update KPIs
       │   EMA → MemoryManager
       │   Calculate H-CR
       │
       └─→ A2A: Return result to TAA

3. Memory updated, available for next PAA query!
```

---

## Benefits of Hybrid Architecture

### 1. Clean Separation of Concerns

**Without MCP (Direct Access):**
```python
# PAA directly accesses files
policies = self.policy_retriever.read_files_from_disk()

# EMA directly accesses database
db.execute("INSERT INTO adaptive_memory...")
```
❌ Tight coupling  
❌ Hard to test  
❌ Hard to swap implementations  

**With MCP (Abstracted Access):**
```python
# PAA uses MCP resources
policies = self.policy_mcp.search_relevant_policies_sync(invoice)

# EMA uses MCP tools
self.memory_mcp.add_exception_sync(...)
```
✅ Loose coupling  
✅ Easy to test (mock MCP servers)  
✅ Easy to swap (files → DB → API)  

### 2. Standard Interfaces

**MCP provides:**
- Standard resource URI format (`policy://`)
- Standard tool calling interface
- Observable operations
- Type-safe schemas

**A2A provides:**
- Standard agent discovery (Agent Cards)
- Standard task execution
- Observable communication
- Streaming support

### 3. Scalability Path

**Local MVP:**
```
All in one process:
- TAA, PAA, EMA in same Python app
- MCP servers in-process
- A2A communication in-process
```

**Production (Phase 3):**
```
Distributed deployment:
- TAA in Container 1
- PAA in Container 2 + PolicyMCPServer
- EMA in Container 3 + MemoryMCPServer
- A2A over HTTP (with Istio)
- MCP servers as microservices
```

### 4. Alignment with Research

**MIT GenAI Report Recommendations:**
- ✅ Use standard protocols (A2A, MCP)
- ✅ Governable AI systems
- ✅ Observable workflows
- ✅ Modular architecture
- ✅ Scalable design

---

## Code Examples

### PAA Using MCP for Policy Access

```python
# src/agents/paa/agent.py

class PolicyAdherenceAgent:
    def __init__(self, policy_mcp_server: PolicyMCPServer):
        self.policy_mcp = policy_mcp_server  # MCP server
    
    def retrieve_policies(self, state):
        # Access policies via MCP (not directly from files)
        policies = self.policy_mcp.search_relevant_policies_sync(
            invoice=state["invoice"],
            top_k=5
        )
        
        # MCP provides clean abstraction
        # Could swap file-based for API-based without changing PAA
```

### EMA Using MCP for Memory Operations

```python
# src/agents/ema/agent.py

class ExceptionManagerAgent:
    def __init__(self, memory_mcp_server: MemoryMCPServer):
        self.memory_mcp = memory_mcp_server  # MCP server
    
    def update_memory(self, state):
        # Use MCP tool (not direct database access)
        exception_id = self.memory_mcp.add_exception_sync(
            vendor=invoice.vendor,
            category=invoice.category,
            rule_type="recurring",
            description="Learned rule",
            reason="Human override"
        )
        
        # MCP provides clean tool interface
        # Could swap SQLite for Delta Lake without changing EMA
```

### TAA Using A2A (No MCP)

```python
# src/agents/taa/agent.py

class TransactionAuditorAgent:
    # TAA doesn't need MCP - it's pure orchestrator
    # It delegates via A2A but doesn't access resources/tools
    
    def delegate_to_paa(self, state):
        # A2A delegation (in orchestrator)
        paa_result = orchestrator.paa.check_compliance_sync(invoice)
```

---

## MCP Server Details

### PolicyMCPServer

**Resources Exposed:**
```python
# List resources
await policy_mcp.server.list_resources()
→ [
    Resource(uri="policy://vendor_approval_policy", ...),
    Resource(uri="policy://expense_limits_policy", ...),
    ...
]

# Read resource
await policy_mcp.server.read_resource("policy://vendor_approval_policy")
→ "VENDOR APPROVAL POLICY\n\nAll transactions must..."
```

### MemoryMCPServer

**Tools Exposed:**
```python
# List tools
await memory_mcp.server.list_tools()
→ [
    Tool(name="add_exception", inputSchema={...}),
    Tool(name="query_exceptions", inputSchema={...}),
    ...
]

# Call tool
await memory_mcp.server.call_tool(
    name="add_exception",
    arguments={
        "vendor": "Acme Corp",
        "rule_type": "recurring",
        "description": "Trusted vendor",
        "reason": "Long-term partner"
    }
)
→ {"success": True, "exception_id": "abc123"}
```

---

## Observability

### Both Protocols Are Logged

**A2A Communication:**
```python
self.observability.log_a2a_communication(
    trace_id=trace_id,
    from_agent="TAA",
    to_agent="PAA",
    message={"invoice_id": "...", "action": "check_compliance"}
)
```

**MCP Operations:**
```python
self.observability.log_agent_step(
    trace_id=trace_id,
    agent_name="PAA",
    step_name="retrieve_policies_mcp",
    input_data={"protocol": "MCP"},
    output_data={"retrieved_count": 5, "policies": [...]}
)
```

**Complete Audit Trail Includes:**
- A2A: Which agents communicated
- MCP: Which resources/tools were accessed
- LLM: What decisions were made
- Timing: How long each step took

---

## Testing Benefits

### Mock MCP Servers

```python
# tests/unit/test_paa_mcp.py

def test_paa_with_mock_mcp():
    # Create mock MCP server
    mock_policy_mcp = MockPolicyMCPServer()
    mock_policy_mcp.set_policies({
        "test_policy": "Always approve test vendors"
    })
    
    # PAA uses mock instead of real MCP
    paa = PolicyAdherenceAgent(policy_mcp_server=mock_policy_mcp)
    
    # Test without needing real policy files
    result = paa.check_compliance_sync(test_invoice)
    assert result.is_compliant
```

### Integration Testing

```python
# Can test each protocol independently

# Test A2A only
test_agent_communication()

# Test MCP only
test_policy_resource_access()
test_memory_tool_calls()

# Test hybrid
test_full_transaction_flow()
```

---

## Production Deployment

### Phase 3: Distributed Deployment

**Current (MVP):**
```
Single Python Process
├── TAA (orchestrator)
├── PAA (with PolicyMCPServer in-process)
├── EMA (with MemoryMCPServer in-process)
└── A2A communication in-process
```

**Production (AKS):**
```
Container 1: TAA
├── Communicates via A2A HTTP

Container 2: PAA
├── PolicyMCPServer (HTTP endpoint)
├── Receives A2A tasks from TAA
├── Accesses policies via MCP

Container 3: EMA
├── MemoryMCPServer (HTTP endpoint)
├── Receives A2A tasks from TAA
├── Manages memory via MCP

Istio Service Mesh:
├── Secures A2A communication
├── Encrypts MCP endpoints
├── Handles routing and observability
```

---

## Comparison to Other Architectures

### Traditional Microservices

```
Service 1 → HTTP → Service 2 → HTTP → Database
```
- Custom APIs
- No standard protocols
- Hard to discover capabilities

### AFGA (Hybrid A2A + MCP)

```
Agent 1 --A2A-→ Agent 2 --MCP-→ Resources/Tools
```
- Standard protocols
- Self-documenting (Agent Cards, Resource URIs)
- Easy to discover and integrate

---

## MIT GenAI Alignment

### From MIT Report

**Recommendation:** Use standard protocols for AI governance

**AFGA Implementation:**
- ✅ A2A for agent coordination
- ✅ MCP for data access
- ✅ Observable workflows
- ✅ Governable architecture
- ✅ Scalable design

**Why This Matters:**
- Reduces integration complexity
- Enables interoperability
- Supports governance requirements
- Future-proof architecture

---

## When to Use Which Protocol

### Use A2A When:

✅ Agent needs to delegate a task to another agent  
✅ Need orchestration / workflow coordination  
✅ Asynchronous communication required  
✅ Task has multiple steps with streaming updates  

**Example:** TAA delegating compliance check to PAA

### Use MCP When:

✅ Agent needs to read data/resources  
✅ Agent needs to call tools/functions  
✅ Need clean abstraction from data sources  
✅ Want to expose capabilities to LLMs  

**Example:** PAA accessing policy documents

### Use Neither When:

✅ Internal agent logic (LangGraph nodes)  
✅ Direct LLM calls  
✅ Risk calculations  
✅ Business logic  

**Example:** TAA's risk assessment

---

## Code Structure

### MCP Servers

```
src/mcp_servers/
├── __init__.py
├── policy_server.py          # MCP server for policies
│   ├── PolicyMCPServer
│   ├── list_resources()      # Lists policy:// URIs
│   ├── read_resource(uri)    # Reads policy content
│   └── search_relevant_policies_sync()  # Helper for PAA
└── memory_server.py          # MCP server for memory
    ├── MemoryMCPServer
    ├── list_tools()          # Lists available tools
    ├── call_tool(name, args) # Executes memory operations
    └── Helper methods for EMA
```

### Agent Integration

```
src/agents/
├── taa/
│   ├── agent.py              # No MCP (pure orchestrator)
│   └── agent_card.py         # A2A capability definition
├── paa/
│   ├── agent.py              # Uses PolicyMCPServer
│   ├── agent_executor.py     # A2A executor
│   └── agent_card.py         # A2A capability definition
├── ema/
│   ├── agent.py              # Uses MemoryMCPServer
│   ├── agent_executor.py     # A2A executor
│   └── agent_card.py         # A2A capability definition
└── orchestrator.py           # Initializes both protocols
```

---

## Advantages Over Single-Protocol Approach

### A2A Only (Without MCP)

```python
# Agents access data directly
class PAA:
    def retrieve_policies(self):
        files = os.listdir("data/policies")  # Direct file access
        ...
```

**Problems:**
- ❌ Tight coupling to implementation
- ❌ Hard to swap data sources
- ❌ Agents know about file structure
- ❌ Not standardized

### A2A + MCP (Current)

```python
# Agents use MCP abstraction
class PAA:
    def retrieve_policies(self):
        policies = self.policy_mcp.search_relevant_policies_sync(...)  # MCP interface
        ...
```

**Benefits:**
- ✅ Loose coupling
- ✅ Easy to swap (files → DB → API)
- ✅ Agents use standard interfaces
- ✅ Industry standard (MCP)

---

## Future: LLM-Driven MCP Tool Use

### Current (Scripted)

```python
# EMA calls MCP tools programmatically
exception_id = self.memory_mcp.add_exception_sync(...)
```

### Future (LLM-Driven)

```python
# LLM decides which MCP tools to call
llm_response = llm.chat(
    "How should I process this feedback?",
    available_tools=memory_mcp.list_tools()  # MCP tools available
)

# LLM returns: "Call add_exception with these args..."
# System executes the MCP tool call
```

This is the **full vision of MCP** - LLMs choosing which tools to use!

---

## Summary

### AFGA's Hybrid Architecture

**A2A Protocol:**
- TAA ↔ PAA communication
- TAA ↔ EMA communication
- Agent Cards + Executors

**MCP Protocol:**
- PAA → Policy Resources
- EMA → Memory Tools
- Servers + Resources/Tools

**Result:**
- ✅ Industry-standard protocols
- ✅ Clean architecture
- ✅ Governable and observable
- ✅ Scalable and extensible
- ✅ Aligned with MIT research

**This is the state-of-the-art approach for production multi-agent AI systems!** 🚀

