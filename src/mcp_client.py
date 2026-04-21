"""MCP Client - connects to MCP servers and exposes their tools."""

import asyncio
import json
from contextlib import AsyncExitStack
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from src.config import MCPServerConfig


class MCPClient:
    """Manages connections to multiple MCP servers."""

    def __init__(self):
        self._sessions: dict[str, ClientSession] = {}
        self._tool_to_server: dict[str, str] = {}  # tool_name -> server_name
        self._exit_stack = AsyncExitStack()
        self._tools_cache: list[dict] = []

    async def connect(self, servers: dict[str, MCPServerConfig]):
        """Connect to all configured MCP servers."""
        for name, config in servers.items():
            try:
                await self._connect_server(name, config)
            except Exception as e:
                print(f"[warn] Failed to connect MCP server '{name}': {e}")

    async def _connect_server(self, name: str, config: MCPServerConfig):
        """Connect to a single MCP server via stdio."""
        server_params = StdioServerParameters(
            command=config.command,
            args=config.args,
            env=config.env or None,
        )

        stdio_transport = await self._exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        read_stream, write_stream = stdio_transport
        session = await self._exit_stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )
        await session.initialize()

        self._sessions[name] = session

        # Discover tools
        tools_result = await session.list_tools()
        for tool in tools_result.tools:
            self._tool_to_server[tool.name] = name
            self._tools_cache.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": tool.inputSchema if tool.inputSchema else {"type": "object", "properties": {}},
                },
            })

    def get_tool_definitions(self) -> list[dict]:
        """Get all MCP tools in OpenAI function calling format."""
        return self._tools_cache

    def is_mcp_tool(self, tool_name: str) -> bool:
        """Check if a tool name belongs to an MCP server."""
        return tool_name in self._tool_to_server

    async def call_tool(self, tool_name: str, arguments: dict) -> str:
        """Call an MCP tool and return the result as string."""
        server_name = self._tool_to_server.get(tool_name)
        if not server_name:
            return f"Error: MCP tool '{tool_name}' not found"

        session = self._sessions[server_name]
        try:
            result = await session.call_tool(tool_name, arguments)
            # Extract text from result content
            texts = []
            for content in result.content:
                if hasattr(content, "text"):
                    texts.append(content.text)
                else:
                    texts.append(str(content))
            return "\n".join(texts)
        except Exception as e:
            return f"Error calling MCP tool '{tool_name}': {e}"

    async def close(self):
        """Close all MCP connections."""
        await self._exit_stack.aclose()
