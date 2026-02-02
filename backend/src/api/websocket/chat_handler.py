"""WebSocket handler for real-time chat communication."""

import json
import logging
import asyncio
from typing import Dict, Set, Optional, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from ...db.database import get_db, AsyncSessionLocal
from ...db.models import Session, SessionPersona, Message, TokenUsage, AuditLog, SessionPhase
from ...personas.loader import get_persona_loader
from ...personas.context_builder import ContextBuilder
from ...providers.factory import get_provider
from ...providers.base import ChatMessage

logger = logging.getLogger(__name__)

router = APIRouter()


class WSEventType(str, Enum):
    """WebSocket event types."""
    # Connection events
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"

    # User events
    USER_MESSAGE = "user_message"
    START_DISCUSSION = "start_discussion"
    PAUSE_DISCUSSION = "pause_discussion"
    RESUME_DISCUSSION = "resume_discussion"
    STOP_DISCUSSION = "stop_discussion"
    CHANGE_PHASE = "change_phase"
    VOTE_REQUEST = "vote_request"

    # Agent events
    PERSONA_THINKING = "persona_thinking"
    PERSONA_CHUNK = "persona_chunk"
    PERSONA_DONE = "persona_done"
    PERSONA_ERROR = "persona_error"
    PERSONA_AWAITING_MCP = "persona_awaiting_mcp"  # Waiting for Claude Code

    # MCP events
    SET_MCP_MODE = "set_mcp_mode"
    MCP_STATUS = "mcp_status"

    # Orchestrator events (status updates from Claude Code)
    ORCHESTRATOR_STATUS = "orchestrator_status"

    # Turn events
    TURN_START = "turn_start"
    TURN_END = "turn_end"
    SPEAKER_QUEUE = "speaker_queue"

    # Consensus events
    CONSENSUS_UPDATE = "consensus_update"
    VOTE_RECEIVED = "vote_received"
    VOTE_COMPLETE = "vote_complete"

    # System events
    SYSTEM_MESSAGE = "system_message"

    # Metrics events
    TOKEN_UPDATE = "token_update"
    BUDGET_WARNING = "budget_warning"

    # Session events
    PHASE_CHANGE = "phase_change"
    SESSION_UPDATE = "session_update"


@dataclass
class WSEvent:
    """WebSocket event structure."""
    type: WSEventType
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_json(self) -> str:
        return json.dumps({
            "type": self.type.value,
            "data": self.data,
            "timestamp": self.timestamp,
        })


class ConnectionManager:
    """Manages WebSocket connections for sessions."""

    def __init__(self):
        # Map of session_id -> set of WebSocket connections
        self.active_connections: Dict[int, Set[WebSocket]] = {}
        # Map of session_id -> discussion state
        self.discussion_states: Dict[int, Dict[str, Any]] = {}

    async def connect(self, websocket: WebSocket, session_id: int) -> bool:
        """Accept a WebSocket connection for a session."""
        await websocket.accept()

        if session_id not in self.active_connections:
            self.active_connections[session_id] = set()

        self.active_connections[session_id].add(websocket)

        # Send connected event
        await self.send_personal(websocket, WSEvent(
            type=WSEventType.CONNECTED,
            data={"session_id": session_id},
        ))

        logger.info(f"WebSocket connected to session {session_id}")
        return True

    def disconnect(self, websocket: WebSocket, session_id: int):
        """Remove a WebSocket connection."""
        if session_id in self.active_connections:
            self.active_connections[session_id].discard(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]
        logger.info(f"WebSocket disconnected from session {session_id}")

    async def send_personal(self, websocket: WebSocket, event: WSEvent):
        """Send event to a specific connection."""
        try:
            await websocket.send_text(event.to_json())
        except Exception as e:
            logger.error(f"Error sending to websocket: {e}")

    async def broadcast(self, session_id: int, event: WSEvent):
        """Broadcast event to all connections in a session."""
        if session_id not in self.active_connections:
            return

        disconnected = []
        for websocket in self.active_connections[session_id]:
            try:
                await websocket.send_text(event.to_json())
            except Exception as e:
                logger.error(f"Error broadcasting: {e}")
                disconnected.append(websocket)

        # Clean up disconnected clients
        for ws in disconnected:
            self.active_connections[session_id].discard(ws)


# Global connection manager
manager = ConnectionManager()


@router.websocket("/chat/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: int,
):
    """WebSocket endpoint for session chat."""
    # Verify session exists
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Session).where(Session.id == session_id)
        )
        session = result.scalar_one_or_none()

        if not session:
            await websocket.close(code=4004, reason="Session not found")
            return

    # Connect
    await manager.connect(websocket, session_id)

    try:
        while True:
            # Receive message
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                event_type = message.get("type")
                event_data = message.get("data", {})

                # Handle different event types
                await handle_event(
                    websocket,
                    session_id,
                    event_type,
                    event_data,
                )

            except json.JSONDecodeError:
                await manager.send_personal(websocket, WSEvent(
                    type=WSEventType.ERROR,
                    data={"message": "Invalid JSON"},
                ))

    except WebSocketDisconnect:
        manager.disconnect(websocket, session_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        manager.disconnect(websocket, session_id)


async def handle_event(
    websocket: WebSocket,
    session_id: int,
    event_type: str,
    event_data: Dict[str, Any],
):
    """Handle incoming WebSocket events."""
    # Import here to avoid circular imports
    from ...core.orchestrator import get_orchestrator

    try:
        if event_type == WSEventType.USER_MESSAGE.value:
            # Handle user message
            content = event_data.get("content", "")
            if content:
                await process_user_message(session_id, content)

        elif event_type == WSEventType.START_DISCUSSION.value:
            # Start the discussion
            orchestrator = get_orchestrator(session_id)
            await orchestrator.start_discussion()

        elif event_type == WSEventType.PAUSE_DISCUSSION.value:
            orchestrator = get_orchestrator(session_id)
            await orchestrator.pause()

        elif event_type == WSEventType.RESUME_DISCUSSION.value:
            orchestrator = get_orchestrator(session_id)
            await orchestrator.resume()

        elif event_type == WSEventType.STOP_DISCUSSION.value:
            orchestrator = get_orchestrator(session_id)
            await orchestrator.stop()

        elif event_type == WSEventType.CHANGE_PHASE.value:
            new_phase = event_data.get("phase")
            if new_phase:
                await change_session_phase(session_id, SessionPhase(new_phase))

        elif event_type == WSEventType.VOTE_REQUEST.value:
            # Request a vote on a proposal
            proposal = event_data.get("proposal")
            if proposal:
                orchestrator = get_orchestrator(session_id)
                await orchestrator.request_vote(proposal)

        elif event_type == WSEventType.SET_MCP_MODE.value:
            # Toggle MCP mode (Claude Code powers the responses)
            enabled = event_data.get("enabled", False)
            orchestrator = get_orchestrator(session_id)
            orchestrator.set_mcp_mode(enabled)

            # Also update session config in database
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Session).where(Session.id == session_id)
                )
                session = result.scalar_one_or_none()
                if session:
                    config = session.config or {}
                    config["mcp_mode"] = enabled
                    session.config = config
                    await db.commit()

            # Broadcast MCP status
            await manager.broadcast(session_id, WSEvent(
                type=WSEventType.MCP_STATUS,
                data={
                    "enabled": enabled,
                    "pending_responses": orchestrator.get_pending_mcp_responses(),
                },
            ))

        else:
            await manager.send_personal(websocket, WSEvent(
                type=WSEventType.ERROR,
                data={"message": f"Unknown event type: {event_type}"},
            ))

    except Exception as e:
        logger.error(f"Error handling event {event_type}: {e}", exc_info=True)
        await manager.send_personal(websocket, WSEvent(
            type=WSEventType.ERROR,
            data={"message": str(e)},
        ))


async def process_user_message(session_id: int, content: str):
    """Process a user message and trigger AI responses."""
    async with AsyncSessionLocal() as db:
        # Get session
        result = await db.execute(
            select(Session).where(Session.id == session_id)
        )
        session = result.scalar_one_or_none()
        if not session:
            return

        # Get current turn number
        msg_result = await db.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.turn_number.desc())
            .limit(1)
        )
        last_msg = msg_result.scalar_one_or_none()
        turn_number = (last_msg.turn_number if last_msg else 0) + 1

        # Save user message
        user_message = Message(
            session_id=session_id,
            role="user",
            content=content,
            turn_number=turn_number,
            phase=session.phase,
        )
        db.add(user_message)

        # Log the event
        audit = AuditLog(
            session_id=session_id,
            event_type="user_message",
            actor="user",
            details={"content_length": len(content)},
        )
        db.add(audit)

        await db.commit()

    # Broadcast the user message
    await manager.broadcast(session_id, WSEvent(
        type=WSEventType.USER_MESSAGE,
        data={
            "content": content,
            "turn_number": turn_number,
        },
    ))

    # Trigger orchestrator to generate responses
    from ...core.orchestrator import get_orchestrator
    orchestrator = get_orchestrator(session_id)
    await orchestrator.process_user_message(content, turn_number)


async def change_session_phase(session_id: int, new_phase: SessionPhase):
    """Change the session phase."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Session).where(Session.id == session_id)
        )
        session = result.scalar_one_or_none()
        if not session:
            return

        old_phase = session.phase
        session.phase = new_phase
        session.version += 1

        # Log the change
        audit = AuditLog(
            session_id=session_id,
            event_type="phase_change",
            actor="user",
            details={"old_phase": old_phase.value, "new_phase": new_phase.value},
        )
        db.add(audit)

        await db.commit()

    # Broadcast phase change
    await manager.broadcast(session_id, WSEvent(
        type=WSEventType.PHASE_CHANGE,
        data={
            "old_phase": old_phase.value,
            "new_phase": new_phase.value,
        },
    ))


# Helper functions for sending events from orchestrator

async def send_persona_thinking(session_id: int, persona_name: str):
    """Notify that a persona is thinking."""
    await manager.broadcast(session_id, WSEvent(
        type=WSEventType.PERSONA_THINKING,
        data={"persona_name": persona_name},
    ))


async def send_persona_chunk(session_id: int, persona_name: str, chunk: str):
    """Send a streaming chunk from a persona."""
    await manager.broadcast(session_id, WSEvent(
        type=WSEventType.PERSONA_CHUNK,
        data={"persona_name": persona_name, "chunk": chunk},
    ))


async def send_persona_done(
    session_id: int,
    persona_name: str,
    full_content: str,
    input_tokens: int,
    output_tokens: int,
    turn_number: int = 0,
    round_number: int = 1,
):
    """Notify that a persona finished speaking."""
    await manager.broadcast(session_id, WSEvent(
        type=WSEventType.PERSONA_DONE,
        data={
            "persona_name": persona_name,
            "content": full_content,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "turn_number": turn_number,
            "round_number": round_number,
        },
    ))


async def send_token_update(session_id: int, usage: Dict[str, Any]):
    """Send token usage update."""
    await manager.broadcast(session_id, WSEvent(
        type=WSEventType.TOKEN_UPDATE,
        data=usage,
    ))


async def send_turn_start(session_id: int, persona_name: str, turn_number: int):
    """Notify turn start."""
    await manager.broadcast(session_id, WSEvent(
        type=WSEventType.TURN_START,
        data={"persona_name": persona_name, "turn_number": turn_number},
    ))


async def send_turn_end(session_id: int, persona_name: str, turn_number: int):
    """Notify turn end."""
    await manager.broadcast(session_id, WSEvent(
        type=WSEventType.TURN_END,
        data={"persona_name": persona_name, "turn_number": turn_number},
    ))


async def send_orchestrator_status(
    session_id: int,
    status: str,
    persona_name: str = None,
    round_number: int = None,
    details: str = None,
    input_tokens: int = None,
    output_tokens: int = None,
    cache_read_tokens: int = None,
    cache_creation_tokens: int = None,
):
    """
    Send orchestrator status update to the frontend.

    Args:
        session_id: The session to broadcast to
        status: Status type (e.g., "checking", "generating", "submitting", "waiting", "complete")
        persona_name: Which persona is being processed (if applicable)
        round_number: Current discussion round (if applicable)
        details: Additional details about the status
        input_tokens: Claude Code input tokens used
        output_tokens: Claude Code output tokens used
        cache_read_tokens: Tokens read from cache
        cache_creation_tokens: Tokens used to create cache
    """
    data = {"status": status}
    if persona_name:
        data["persona_name"] = persona_name
    if round_number:
        data["round_number"] = round_number
    if details:
        data["details"] = details
    if input_tokens is not None:
        data["input_tokens"] = input_tokens
    if output_tokens is not None:
        data["output_tokens"] = output_tokens
    if cache_read_tokens is not None:
        data["cache_read_tokens"] = cache_read_tokens
    if cache_creation_tokens is not None:
        data["cache_creation_tokens"] = cache_creation_tokens

    await manager.broadcast(session_id, WSEvent(
        type=WSEventType.ORCHESTRATOR_STATUS,
        data=data,
    ))
