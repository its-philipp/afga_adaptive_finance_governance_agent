"""MCP Server for Policy Resources.

Exposes policy documents as MCP resources that PAA can access.
This provides a clean abstraction layer between agents and policy data.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List

from mcp.server import Server
from mcp.types import Resource, TextContent

from ..services.policy_retriever import PolicyRetriever


logger = logging.getLogger(__name__)


class PolicyMCPServer:
    """MCP Server that exposes policy documents as resources.

    This allows PAA to access policies through the Model Context Protocol,
    providing a standardized interface for LLM access to company policies.
    """

    def __init__(self, policies_dir: str = "data/policies"):
        self.policy_retriever = PolicyRetriever(policies_dir=policies_dir)
        self.server = Server("afga-policy-server")
        self._setup_handlers()
        logger.info(f"Policy MCP Server initialized with {len(self.policy_retriever.policies)} policies")

    def _setup_handlers(self):
        """Set up MCP server handlers for resources."""

        @self.server.list_resources()
        async def list_resources() -> List[Resource]:
            """List all available policy resources."""
            policies = self.policy_retriever.get_all_policies_summary()

            resources = []
            for policy in policies:
                resources.append(
                    Resource(
                        uri=f"policy://{policy['policy_name']}",
                        name=policy["filename"],
                        description=f"Company policy: {policy['filename']} ({policy['chunk_count']} chunks)",
                        mimeType="text/plain",
                    )
                )

            logger.info(f"MCP: Listed {len(resources)} policy resources")
            return resources

        @self.server.read_resource()
        async def read_resource(uri: str) -> str:
            """Read a specific policy resource.

            Args:
                uri: Resource URI (e.g., policy://vendor_approval_policy)

            Returns:
                Policy content as text
            """
            if not uri.startswith("policy://"):
                raise ValueError(f"Invalid policy URI: {uri}")

            policy_name = uri.replace("policy://", "")

            # Get policy content
            if policy_name in self.policy_retriever.policies:
                content = self.policy_retriever.policies[policy_name]["content"]
                logger.info(f"MCP: Read policy resource: {policy_name}")
                return content
            else:
                raise ValueError(f"Policy not found: {policy_name}")

    # Synchronous helper methods for agent use
    def get_policy_sync(self, policy_name: str) -> str:
        """Get policy content synchronously."""
        if policy_name in self.policy_retriever.policies:
            return self.policy_retriever.policies[policy_name]["content"]
        return ""

    def list_policies_sync(self) -> List[str]:
        """List all policy names synchronously."""
        return list(self.policy_retriever.policies.keys())

    def search_relevant_policies_sync(self, invoice, top_k: int = 5) -> List[dict]:
        """Search for relevant policies (RAG-style) synchronously.

        This is the primary method PAA uses - combines MCP resource access
        with intelligent retrieval based on invoice context.
        """
        return self.policy_retriever.retrieve_relevant_policies(invoice, top_k=top_k)

    def get_all_policies_sync(self) -> dict:
        """Get all policies as a dictionary."""
        return {name: data["content"] for name, data in self.policy_retriever.policies.items()}
