# Known Issues

## ⚠️ LangGraph Workflow Caching (Development Only)

**Issue:** Audit trail warnings persist despite code fixes during `uvicorn --reload` development.

**Root Cause:**  
LangGraph compiles workflows ONCE at agent initialization with `workflow.compile()`. This captures method references (closures) at that moment. Even when uvicorn reloads Python modules, the compiled graph state machine keeps the old method bindings.

**Why It Happens:**
```python
# TAA agent __init__:
self.graph = self._build_graph()  # Line 37

# _build_graph:
workflow.add_node("delegate_to_paa", self.delegate_to_paa)  # Binds method reference
return workflow.compile()  # Compiles with current method implementation
```

When you change `delegate_to_paa()` code and uvicorn reloads:
- ✅ New source code loads
- ✅ New module imported  
- ❌ **Compiled graph still has OLD method binding**

**Solution for Production:**
- ✅ Not an issue - production runs don't use `--reload`
- ✅ Clean restart always uses fresh code

**Solution for Development:**
```bash
# Option 1: Full restart (recommended)
./force_restart.sh

# Option 2: Fresh database + restart  
rm data/memory.db
./start.sh

# Option 3: Accept old transactions have old messages
# Just check NEW transactions for correctness
```

**Impact:**
- ⚠️ **Cosmetic only** - old audit trail messages
- ✅ **Functionality works** - PAA actually runs correctly
- ✅ **Decisions are correct** - compliance checking works
- ✅ **Not a production issue** - only affects dev with --reload

**Future Improvement:**
Could implement hot-reload detection for LangGraph workflows, but adds complexity for minimal dev-only benefit.

