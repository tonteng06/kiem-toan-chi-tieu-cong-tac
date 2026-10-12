"""MCP server entry point.

Tool handlers will be registered when the RAG retriever and claim state store
are integrated. Keep stdout reserved for MCP stdio transport; use logging on
stderr for diagnostics.
"""

from mcp.server import MCPServer


server = MCPServer("travel-expense-audit")


def main() -> None:
    """Run the MCP server over stdio."""
    server.run(transport="stdio")


if __name__ == "__main__":
    main()

