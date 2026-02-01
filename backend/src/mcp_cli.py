#!/usr/bin/env python3
"""
MCP CLI server for Claude Code integration.

Run with: python -m src.mcp_cli

Add to your .claude/settings.json:
{
  "mcpServers": {
    "multi-agent-collab": {
      "command": "python",
      "args": ["-m", "src.mcp_cli"],
      "cwd": "/path/to/multi-agent-collab/backend"
    }
  }
}
"""

import asyncio
import json
import sys
import logging

from src.api.mcp.server import mcp_server
from src.personas.loader import get_persona_loader

# Set up logging to stderr (stdout is for MCP protocol)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr
)
logger = logging.getLogger(__name__)


def write_message(message: dict):
    """Write an MCP message to stdout."""
    msg_str = json.dumps(message)
    sys.stdout.write(f"{msg_str}\n")
    sys.stdout.flush()


def read_message() -> dict | None:
    """Read an MCP message from stdin."""
    try:
        line = sys.stdin.readline()
        if not line:
            return None
        return json.loads(line.strip())
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse message: {e}")
        return None


async def handle_request(request: dict) -> dict:
    """Handle an incoming MCP request."""
    method = request.get("method")
    params = request.get("params", {})
    req_id = request.get("id")

    logger.info(f"Handling request: {method}")

    if method == "initialize":
        # Return server info
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "multi-agent-collab",
                    "version": "1.0.0"
                }
            }
        }

    elif method == "initialized":
        # Client has confirmed initialization
        return None  # No response needed

    elif method == "tools/list":
        # Return available tools
        tools = mcp_server.get_tools_schema()
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": tools
            }
        }

    elif method == "tools/call":
        # Execute a tool
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        try:
            result = await mcp_server.execute_tool(tool_name, arguments)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, indent=2)
                        }
                    ]
                }
            }
        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32000,
                    "message": str(e)
                }
            }

    elif method == "ping":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {}
        }

    else:
        logger.warning(f"Unknown method: {method}")
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": -32601,
                "message": f"Method not found: {method}"
            }
        }


async def main():
    """Main MCP server loop."""
    logger.info("Starting Multi-Agent Collab MCP Server...")

    # Pre-load personas
    loader = get_persona_loader()
    personas_count = len(loader.load_all())
    domains_count = len(loader.get_all_domains())
    logger.info(f"Loaded {personas_count} personas across {domains_count} domains")

    # Process messages
    while True:
        message = read_message()
        if message is None:
            logger.info("No more input, shutting down")
            break

        response = await handle_request(message)
        if response:
            write_message(response)


if __name__ == "__main__":
    asyncio.run(main())
