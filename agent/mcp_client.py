"""
Task 4 (continued): MCP Client

Dynamically discovers tools from the MCP server at startup and creates
LangChain-compatible tool wrappers so they can be bound to the LLM
alongside the local tools.
"""

import sys
import os
import asyncio
from typing import Any
from pydantic import Field, create_model
from langchain_core.tools import StructuredTool

from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters


# ── Helpers ──────────────────────────────────────────────────────────────────

def _json_type_to_python(type_str: str) -> type:
    """Map JSON Schema type strings to Python types."""
    mapping = {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
    }
    return mapping.get(type_str, str)


async def _call_mcp_tool(
    server_script: str, tool_name: str, arguments: dict
) -> str:
    """Open a fresh MCP connection, call one tool, return the text result."""
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[server_script],
    )
    async with stdio_client(server_params) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)
            # Concatenate all text content pieces
            texts = [c.text for c in result.content if hasattr(c, "text")]
            return "\n".join(texts)


# ── Public API ───────────────────────────────────────────────────────────────

class MCPToolManager:
    """Discovers tools from an MCP server and wraps them as LangChain tools."""

    def __init__(self, server_script: str):
        self.server_script = os.path.abspath(server_script)

    # ── Discovery ────────────────────────────────────────────────────────
    def discover_and_create_tools(self) -> list[StructuredTool]:
        """Connect to MCP server, list tools, return LangChain wrappers."""
        return asyncio.run(self._discover())

    async def _discover(self) -> list[StructuredTool]:
        server_params = StdioServerParameters(
            command=sys.executable,
            args=[self.server_script],
        )
        async with stdio_client(server_params) as streams:
            async with ClientSession(*streams) as session:
                await session.initialize()
                response = await session.list_tools()

        tools: list[StructuredTool] = []
        for schema in response.tools:
            tools.append(self._wrap_tool(schema))
            print(f"  [MCP] Discovered tool: {schema.name}")
        return tools

    # ── Wrapping ─────────────────────────────────────────────────────────
    def _wrap_tool(self, mcp_tool: Any) -> StructuredTool:
        """Convert a single MCP tool schema into a LangChain StructuredTool."""
        server_script = self.server_script
        name = mcp_tool.name

        def invoke_mcp(**kwargs: Any) -> str:
            return asyncio.run(_call_mcp_tool(server_script, name, kwargs))

        # Build a Pydantic args model from the JSON Schema
        properties = mcp_tool.input_schema.get("properties", {})
        required = set(mcp_tool.input_schema.get("required", []))
        fields: dict[str, Any] = {}
        for prop_name, prop_schema in properties.items():
            py_type = _json_type_to_python(prop_schema.get("type", "string"))
            desc = prop_schema.get("description", "")
            if prop_name in required:
                fields[prop_name] = (py_type, Field(description=desc))
            else:
                fields[prop_name] = (
                    py_type | None,
                    Field(default=None, description=desc),
                )

        ArgsModel = create_model(f"{name}_Args", **fields)

        return StructuredTool(
            name=name,
            description=mcp_tool.description or "",
            func=invoke_mcp,
            args_schema=ArgsModel,
        )
