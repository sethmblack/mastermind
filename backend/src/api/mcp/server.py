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
            MCPTool(
                name="get_persona_prompt",
                description="Get a persona's full system prompt and conversation context so Claude Code can respond as that persona. Use this when you need to generate a response as a specific persona in a session.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "integer",
                            "description": "The session ID"
                        },
                        "persona_name": {
                            "type": "string",
                            "description": "The persona to respond as"
                        }
                    },
                    "required": ["session_id", "persona_name"]
                }
            ),
            MCPTool(
                name="submit_persona_response",
                description="Submit a response generated by Claude Code as a specific persona. Use this after get_persona_prompt to send the generated response back to the session.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "integer",
                            "description": "The session ID"
                        },
                        "persona_name": {
                            "type": "string",
                            "description": "The persona that generated this response"
                        },
                        "content": {
                            "type": "string",
                            "description": "The response content"
                        },
                        "round_number": {
                            "type": "integer",
                            "description": "The discussion round (1=initial, 2+=discussion rounds)",
                            "default": 1
                        }
                    },
                    "required": ["session_id", "persona_name", "content"]
                }
            ),
            MCPTool(
                name="get_session_state",
                description="Get the current state of a session including pending responses needed and conversation history",
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

        elif name == "get_persona_prompt":
            from ...personas.context_builder import ContextBuilder
            session_id = arguments["session_id"]
            persona_name = arguments["persona_name"]

            async with AsyncSessionLocal() as db:
                # Get session
                result = await db.execute(
                    select(Session).where(Session.id == session_id)
                )
                session = result.scalar_one_or_none()
                if not session:
                    return {"error": "Session not found"}

                # Get persona
                persona = loader.get_persona(persona_name)
                if not persona:
                    return {"error": f"Persona '{persona_name}' not found"}

                # Get session personas
                sp_result = await db.execute(
                    select(SessionPersona).where(SessionPersona.session_id == session_id)
                )
                session_personas = sp_result.scalars().all()
                other_personas = [sp.persona_name for sp in session_personas if sp.persona_name != persona_name]

                # Get conversation history
                msg_result = await db.execute(
                    select(Message)
                    .where(Message.session_id == session_id)
                    .order_by(Message.created_at)
                )
                messages = msg_result.scalars().all()

                # Build system prompt
                context_builder = ContextBuilder()
                system_prompt = context_builder.build_system_prompt(
                    persona=persona,
                    session_config=session.config or {},
                    current_phase=session.phase,
                    turn_mode=session.turn_mode,
                    other_personas=other_personas,
                    problem_statement=session.problem_statement,
                )

                return {
                    "persona_name": persona_name,
                    "display_name": persona.display_name,
                    "system_prompt": system_prompt,
                    "conversation_history": [
                        {
                            "role": m.role,
                            "content": m.content,
                            "persona": m.persona_name,
                        }
                        for m in messages
                    ],
                    "problem_statement": session.problem_statement,
                    "current_phase": session.phase.value,
                    "instructions": "Generate a response as this persona. Stay in character and respond to the conversation naturally. Then use submit_persona_response to send your response."
                }

        elif name == "submit_persona_response":
            from ...api.websocket.chat_handler import (
                send_persona_done,
                send_turn_end,
                send_persona_chunk,
                send_persona_thinking,
                manager as ws_manager,
                WSEvent,
                WSEventType,
            )
            from ...core.orchestrator import get_orchestrator
            import asyncio

            session_id = arguments["session_id"]
            persona_name = arguments["persona_name"]
            content = arguments["content"]
            round_number = arguments.get("round_number", 1)

            async with AsyncSessionLocal() as db:
                # Get session
                result = await db.execute(
                    select(Session).where(Session.id == session_id)
                )
                session = result.scalar_one_or_none()
                if not session:
                    return {"error": "Session not found"}

                # Get current turn number (from last user message)
                user_msg_result = await db.execute(
                    select(Message)
                    .where(Message.session_id == session_id)
                    .where(Message.role == "user")
                    .order_by(Message.turn_number.desc())
                    .limit(1)
                )
                last_user_msg = user_msg_result.scalar_one_or_none()
                turn_number = last_user_msg.turn_number if last_user_msg else 1

                # Save the message with round_number
                message = Message(
                    session_id=session_id,
                    persona_name=persona_name,
                    role="assistant",
                    content=content,
                    turn_number=turn_number,
                    round_number=round_number,
                    phase=session.phase,
                    extra_data={"provider": "claude_code", "round": round_number},
                )
                db.add(message)

                # Estimate tokens and save to database
                # Roughly 4 characters per token for English
                estimated_output_tokens = len(content) // 4
                estimated_input_tokens = estimated_output_tokens * 2  # Context is usually larger

                from ...db.models import TokenUsage
                token_record = TokenUsage(
                    session_id=session_id,
                    persona_name=persona_name,
                    provider="claude_code",
                    model="claude-code-orchestrator",
                    input_tokens=estimated_input_tokens,
                    output_tokens=estimated_output_tokens,
                    cost=0.0,  # No direct cost since Claude Code generates
                )
                db.add(token_record)
                await db.commit()

            # Broadcast the completed message directly (no streaming)
            # This avoids race conditions with multiple personas responding
            await send_persona_done(
                session_id, persona_name, content,
                estimated_input_tokens, estimated_output_tokens,
                turn_number=turn_number, round_number=round_number
            )

            # Notify orchestrator that the response was received
            orchestrator = get_orchestrator(session_id)
            await orchestrator.receive_mcp_response(persona_name, content)

            return {
                "status": "response_submitted",
                "session_id": session_id,
                "persona_name": persona_name,
                "turn_number": turn_number,
                "round_number": round_number,
            }

        elif name == "get_session_state":
            session_id = arguments["session_id"]

            async with AsyncSessionLocal() as db:
                # Get session
                result = await db.execute(
                    select(Session).where(Session.id == session_id)
                )
                session = result.scalar_one_or_none()
                if not session:
                    return {"error": "Session not found"}

                # Get personas
                sp_result = await db.execute(
                    select(SessionPersona).where(SessionPersona.session_id == session_id)
                )
                session_personas = sp_result.scalars().all()

                # Get messages
                msg_result = await db.execute(
                    select(Message)
                    .where(Message.session_id == session_id)
                    .order_by(Message.created_at)
                )
                messages = msg_result.scalars().all()

                # Find which personas haven't responded to the last user message
                last_user_turn = None
                for m in reversed(messages):
                    if m.role == "user":
                        last_user_turn = m.turn_number
                        break

                responded_personas = set()
                if last_user_turn is not None:
                    for m in messages:
                        if m.turn_number == last_user_turn and m.role == "assistant":
                            responded_personas.add(m.persona_name)

                pending_personas = [
                    sp.persona_name for sp in session_personas
                    if sp.persona_name not in responded_personas
                ] if last_user_turn is not None else []

                return {
                    "session_id": session_id,
                    "name": session.name,
                    "status": session.status.value,
                    "phase": session.phase.value,
                    "problem_statement": session.problem_statement,
                    "personas": [sp.persona_name for sp in session_personas],
                    "pending_responses": pending_personas,
                    "message_count": len(messages),
                    "last_messages": [
                        {
                            "role": m.role,
                            "content": m.content[:200] + "..." if len(m.content) > 200 else m.content,
                            "persona": m.persona_name,
                        }
                        for m in messages[-5:]
                    ],
                }

        else:
            return {"error": f"Unknown tool: {name}"}


# Global MCP server instance
mcp_server = MCPServer()
