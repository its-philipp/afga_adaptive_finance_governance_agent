"""MCP Server for Memory Tools.

Exposes adaptive memory operations as MCP tools that EMA can use.
This provides a clean interface for memory management via Model Context Protocol.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from mcp.server import Server
from mcp.types import Tool, TextContent

from ..agents.ema.memory_manager import MemoryManager
from ..models.memory_schemas import MemoryQuery
from ..models.schemas import DecisionType


logger = logging.getLogger(__name__)


class MemoryMCPServer:
    """MCP Server that exposes memory operations as tools.

    This allows EMA to manage adaptive memory through the Model Context Protocol,
    providing a standardized interface for LLM-driven memory operations.
    """

    def __init__(self, memory_manager: MemoryManager | None = None):
        self.memory_manager = memory_manager or MemoryManager()
        self.server = Server("afga-memory-server")
        self._setup_handlers()
        logger.info("Memory MCP Server initialized")

    def _setup_handlers(self):
        """Set up MCP server handlers for tools."""

        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """List all available memory management tools."""
            return [
                Tool(
                    name="add_exception",
                    description="Add a new learned exception to adaptive memory",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "vendor": {"type": "string", "description": "Vendor name (optional)"},
                            "category": {"type": "string", "description": "Expense category (optional)"},
                            "rule_type": {"type": "string", "enum": ["recurring", "temporary", "policy_gap"]},
                            "description": {
                                "type": "string",
                                "description": "Human-readable description of the exception",
                            },
                            "reason": {"type": "string", "description": "Detailed reasoning for this exception"},
                            "auto_decision": {
                                "type": "string",
                                "enum": ["approved", "rejected"],
                                "description": "Optional automatic decision to apply when this rule matches",
                            },
                        },
                        "required": ["rule_type", "description", "reason"],
                    },
                ),
                Tool(
                    name="query_exceptions",
                    description="Query adaptive memory for exceptions matching criteria",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "vendor": {"type": "string", "description": "Filter by vendor"},
                            "category": {"type": "string", "description": "Filter by category"},
                            "rule_type": {"type": "string", "description": "Filter by rule type"},
                            "min_success_rate": {"type": "number", "description": "Minimum success rate (0.0-1.0)"},
                        },
                    },
                ),
                Tool(
                    name="update_exception_usage",
                    description="Update usage statistics for an exception (applied count, success rate)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "exception_id": {"type": "string", "description": "Exception ID to update"},
                            "success": {"type": "boolean", "description": "Whether the application was successful"},
                        },
                        "required": ["exception_id", "success"],
                    },
                ),
                Tool(
                    name="get_memory_stats",
                    description="Get statistics about adaptive memory (total exceptions, applications, success rate)",
                    inputSchema={"type": "object", "properties": {}},
                ),
                Tool(
                    name="calculate_crs",
                    description="Calculate the Context Retention Score (CRS) - measures memory effectiveness",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "date": {"type": "string", "description": "Date to calculate for (YYYY-MM-DD, optional)"}
                        },
                    },
                ),
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Handle tool calls for memory operations."""
            logger.info(f"MCP tool call: {name} with args: {arguments}")

            try:
                if name == "add_exception":
                    # Extract invoice from arguments if provided
                    from ..models.schemas import Invoice, LineItem

                    # Create a minimal invoice for the exception
                    invoice = Invoice(
                        invoice_id="MCP-EXCEPTION",
                        vendor=arguments.get("vendor", "Any"),
                        vendor_reputation=75,
                        amount=0,
                        currency="USD",
                        category=arguments.get("category", "Any"),
                        date="2025-11-04",
                        line_items=[LineItem(description="MCP exception", quantity=1, unit_price=0)],
                        tax=0,
                        total=0,
                    )

                    exception_id = self.memory_manager.add_learned_exception(
                        invoice=invoice,
                        exception_type=arguments["rule_type"],
                        description=arguments["description"],
                        reason=arguments["reason"],
                        auto_decision=arguments.get("auto_decision"),
                    )

                    result = {
                        "success": True,
                        "exception_id": exception_id,
                        "message": f"Added exception {exception_id}",
                    }

                elif name == "query_exceptions":
                    query = MemoryQuery(
                        vendor=arguments.get("vendor"),
                        category=arguments.get("category"),
                        rule_type=arguments.get("rule_type"),
                        min_success_rate=arguments.get("min_success_rate", 0.5),
                    )

                    exceptions = self.memory_manager.db.query_exceptions(query)

                    result = {
                        "success": True,
                        "count": len(exceptions),
                        "exceptions": [
                            {
                                "exception_id": exc.exception_id,
                                "vendor": exc.vendor,
                                "category": exc.category,
                                "description": exc.description,
                                "applied_count": exc.applied_count,
                                "success_rate": exc.success_rate,
                            }
                            for exc in exceptions
                        ],
                    }

                elif name == "update_exception_usage":
                    self.memory_manager.update_exception_usage(
                        exception_id=arguments["exception_id"], success=arguments["success"]
                    )

                    result = {"success": True, "message": f"Updated exception {arguments['exception_id']}"}

                elif name == "get_memory_stats":
                    stats = self.memory_manager.get_memory_stats()

                    result = {
                        "success": True,
                        "stats": {
                            "total_exceptions": stats.total_exceptions,
                            "active_exceptions": stats.active_exceptions,
                            "total_applications": stats.total_applications,
                            "avg_success_rate": stats.avg_success_rate,
                            "most_applied_rules": stats.most_applied_rules,
                            "recent_additions": stats.recent_additions,
                        },
                    }

                elif name == "calculate_crs":
                    crs = self.memory_manager.db.calculate_crs(arguments.get("date"))

                    result = {
                        "success": True,
                        "crs_score": crs.crs_score,
                        "applicable_scenarios": crs.applicable_scenarios,
                        "successful_applications": crs.successful_applications,
                        "details": crs.details,
                    }

                else:
                    raise ValueError(f"Unknown tool: {name}")

                return [TextContent(type="text", text=json.dumps(result, indent=2))]

            except Exception as e:
                logger.error(f"Error in MCP tool call {name}: {e}")
                error_result = {"success": False, "error": str(e)}
                return [TextContent(type="text", text=json.dumps(error_result, indent=2))]

    # Synchronous helper methods for agent use
    def add_exception_sync(
        self,
        vendor: str,
        category: str,
        rule_type: str,
        description: str,
        reason: str,
        auto_decision: DecisionType | str | None = None,
    ) -> str:
        """Synchronous wrapper for add_exception tool."""
        from ..models.schemas import Invoice, LineItem

        invoice = Invoice(
            invoice_id="MCP-EXCEPTION",
            vendor=vendor or "Any",
            vendor_reputation=75,
            amount=0,
            currency="USD",
            category=category or "Any",
            date="2025-11-04",
            line_items=[LineItem(description="MCP exception", quantity=1, unit_price=0)],
            tax=0,
            total=0,
        )

        return self.memory_manager.add_learned_exception(
            invoice=invoice,
            exception_type=rule_type,
            description=description,
            reason=reason,
            auto_decision=auto_decision,
        )

    def query_exceptions_sync(self, vendor: str = None, category: str = None, rule_type: str = None):
        """Synchronous wrapper for query_exceptions tool."""
        query = MemoryQuery(vendor=vendor, category=category, rule_type=rule_type, min_success_rate=0.5)
        return self.memory_manager.db.query_exceptions(query)

    def get_stats_sync(self):
        """Synchronous wrapper for get_memory_stats tool."""
        return self.memory_manager.get_memory_stats()
