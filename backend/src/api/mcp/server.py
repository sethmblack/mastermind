"""MCP Server for Claude Code integration.

This provides tools for Claude Code to interact with the multi-agent
collaboration platform, enabling AI-assisted session management and analysis.
"""

import json
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MCPTool:
    """Definition of an MCP tool."""
    name: str
    description: str
    input_schema: Dict[str, Any]


class MCPServer:
    """
    MCP (Model Context Protocol) server for Claude Code integration.

    Exposes tools for:
    - Creating and managing sessions
    - Loading and querying personas
    - Analyzing conversation metrics
    - Generating summaries
    """

    def __init__(self):
        self.tools = self._define_tools()

    def _define_tools(self) -> List[MCPTool]:
        """Define available MCP tools."""
        return [
            MCPTool(
                name="list_personas",
                description="List available AI personas with optional filtering by domain or search query",
                input_schema={
                    "type": "object",
                    "properties": {
                        "domain": {
                            "type": "string",
                            "description": "Filter by domain (e.g., 'scientists', 'philosophers')"
                        },
                        "search": {
                            "type": "string",
                            "description": "Search query for persona names"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results",
                            "default": 20
                        }
                    }
                }
            ),
            MCPTool(
                name="get_persona_details",
                description="Get detailed information about a specific persona including their voice profile, skills, and methodology",
                input_schema={
                    "type": "object",
                    "properties": {
                        "persona_name": {
                            "type": "string",
                            "description": "The slug name of the persona (e.g., 'richard-feynman')"
                        }
                    },
                    "required": ["persona_name"]
                }
            ),
            MCPTool(
                name="create_session",
                description="Create a new multi-agent collaboration session with specified personas",
                input_schema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Name for the session"
                        },
                        "problem_statement": {
                            "type": "string",
                            "description": "The problem or topic for discussion"
                        },
                        "persona_names": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of persona names to include (max 5)"
                        },
                        "turn_mode": {
                            "type": "string",
                            "enum": ["round_robin", "moderator", "free_form", "parallel"],
                            "description": "How turns are managed",
                            "default": "round_robin"
                        }
                    },
                    "required": ["name", "persona_names"]
                }
            ),
            MCPTool(
                name="send_message",
                description="Send a message to an active session and get responses from the AI personas",
                input_schema={
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "integer",
                            "description": "The session ID"
                        },
                        "message": {
                            "type": "string",
                            "description": "The message to send"
                        }
                    },
                    "required": ["session_id", "message"]
                }
            ),
            MCPTool(
                name="get_session_summary",
                description="Get a summary of a session including key insights, decisions, and action items",
                input_schema={
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "integer",
                            "description": "The session ID"
                        }
                    },
                    "required": ["session_id"]
                }
            ),
            MCPTool(
                name="analyze_consensus",
                description="Analyze the level of agreement and disagreement in a session",
                input_schema={
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "integer",
                            "description": "The session ID"
                        }
                    },
                    "required": ["session_id"]
                }
            ),
            MCPTool(
                name="request_vote",
                description="Request all personas in a session to vote on a proposal",
                input_schema={
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "integer",
                            "description": "The session ID"
                        },
                        "proposal": {
                            "type": "string",
                            "description": "The proposal to vote on"
                        }
                    },
                    "required": ["session_id", "proposal"]
                }
            ),
            MCPTool(
                name="change_phase",
                description="Change the discussion phase of a session",
                input_schema={
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "integer",
                            "description": "The session ID"
                        },
                        "phase": {
                            "type": "string",
                            "enum": ["discovery", "ideation", "evaluation", "decision", "action", "synthesis"],
                            "description": "The new phase"
                        }
                    },
                    "required": ["session_id", "phase"]
                }
            ),
            MCPTool(
                name="list_domains",
                description="List all available persona domains/categories",
                input_schema={
                    "type": "object",
                    "properties": {}
                }
            ),
        ]

    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """Get the JSON schema for all tools."""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema
            }
            for tool in self.tools
        ]

    async def execute_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool by name with given arguments."""
        from ...personas.loader import get_persona_loader
        from ...db.database import AsyncSessionLocal
        from ...db.models import Session, SessionPersona, Message
        from ...core.orchestrator import get_orchestrator
        from sqlalchemy import select

        loader = get_persona_loader()

        if name == "list_personas":
            if arguments.get("search"):
                personas = loader.search_personas(
                    arguments["search"],
                    limit=arguments.get("limit", 20)
                )
            elif arguments.get("domain"):
                personas = loader.get_personas_by_domain(arguments["domain"])
            else:
                personas = loader.get_all_personas()[:arguments.get("limit", 20)]

            return {
                "personas": [
                    {
                        "name": p.name,
                        "display_name": p.display_name,
                        "domain": p.domain,
                        "era": p.era,
                    }
                    for p in personas
                ],
                "count": len(personas)
            }

        elif name == "get_persona_details":
            persona = loader.get_persona(arguments["persona_name"])
            if not persona:
                return {"error": f"Persona '{arguments['persona_name']}' not found"}

            return persona.to_dict()

        elif name == "list_domains":
            domains = loader.get_all_domains()
            return {
                "domains": [
                    {
                        "name": d,
                        "persona_count": len(loader.get_personas_by_domain(d))
                    }
                    for d in domains
                ]
            }

        elif name == "create_session":
            from ..routes.sessions import sessionsApi

            # Create session via API
            async with AsyncSessionLocal() as db:
                session = Session(
                    name=arguments["name"],
                    problem_statement=arguments.get("problem_statement"),
                    turn_mode=arguments.get("turn_mode", "round_robin"),
                )
                db.add(session)
                await db.flush()

                colors = ["#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6"]
                for i, persona_name in enumerate(arguments["persona_names"][:5]):
                    sp = SessionPersona(
                        session_id=session.id,
                        persona_name=persona_name,
                        provider="anthropic",
                        model="claude-sonnet-4-20250514",
                        color=colors[i % len(colors)],
                    )
                    db.add(sp)

                await db.commit()

                return {
                    "session_id": session.id,
                    "name": session.name,
                    "personas": arguments["persona_names"][:5]
                }

        elif name == "get_session_summary":
            from ..routes.analytics import analyticsApi

            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Session).where(Session.id == arguments["session_id"])
                )
                session = result.scalar_one_or_none()
                if not session:
                    return {"error": "Session not found"}

                # Get messages
                msg_result = await db.execute(
                    select(Message)
                    .where(Message.session_id == arguments["session_id"])
                    .order_by(Message.created_at)
                )
                messages = msg_result.scalars().all()

                return {
                    "session_id": session.id,
                    "name": session.name,
                    "phase": session.phase.value,
                    "status": session.status.value,
                    "message_count": len(messages),
                    "problem_statement": session.problem_statement,
                }

        elif name == "analyze_consensus":
            # Use analytics API
            from ..routes.analytics import analyticsApi
            # This would integrate with the consensus engine
            return {"message": "Consensus analysis not yet implemented via MCP"}

        elif name == "send_message":
            orchestrator = get_orchestrator(arguments["session_id"])
            await orchestrator.process_user_message(
                arguments["message"],
                turn_number=0  # Will be calculated
            )
            return {"status": "message_sent"}

        elif name == "request_vote":
            orchestrator = get_orchestrator(arguments["session_id"])
            await orchestrator.request_vote(arguments["proposal"])
            return {"status": "vote_requested"}

        elif name == "change_phase":
            orchestrator = get_orchestrator(arguments["session_id"])
            from ...db.models import SessionPhase
            await orchestrator.advance_phase(SessionPhase(arguments["phase"]))
            return {"status": "phase_changed", "new_phase": arguments["phase"]}

        else:
            return {"error": f"Unknown tool: {name}"}


# Global MCP server instance
mcp_server = MCPServer()
