"""Main orchestration engine for multi-agent collaboration."""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from sqlalchemy import select

from ..db.database import AsyncSessionLocal
from ..db.models import (
    Session, SessionPersona, Message, TokenUsage, AuditLog,
    SessionPhase, SessionStatus, TurnMode,
)
from ..personas.loader import get_persona_loader, Persona
from ..personas.context_builder import ContextBuilder, ContextMessage
from ..providers.factory import get_provider
from ..providers.base import ChatMessage
from ..api.websocket.chat_handler import (
    send_persona_thinking,
    send_persona_chunk,
    send_persona_done,
    send_token_update,
    send_turn_start,
    send_turn_end,
    manager as ws_manager,
    WSEvent,
    WSEventType,
)
from .turn_manager import TurnManager
from .consensus_engine import ConsensusEngine
from .context_manager import ContextManager

logger = logging.getLogger(__name__)


class OrchestratorState(str, Enum):
    """State of the orchestrator."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    VOTING = "voting"
    AWAITING_MCP = "awaiting_mcp"  # Waiting for Claude Code to provide responses


@dataclass
class PersonaState:
    """Runtime state for a persona in a session."""
    persona: Persona
    session_persona: SessionPersona
    provider: Any
    context_manager: ContextManager
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    message_count: int = 0


class Orchestrator:
    """
    Main orchestration engine for managing multi-agent discussions.

    Handles turn-taking, context management, streaming responses,
    and coordination between multiple AI personas.
    """

    def __init__(self, session_id: int):
        self.session_id = session_id
        self.state = OrchestratorState.IDLE
        self.turn_manager: Optional[TurnManager] = None
        self.consensus_engine: Optional[ConsensusEngine] = None
        self.personas: Dict[str, PersonaState] = {}
        self.current_turn = 0
        self._lock = asyncio.Lock()
        self._initialized = False
        # MCP/Claude Code mode tracking
        self._mcp_mode = False
        self._pending_mcp_responses: Dict[str, bool] = {}  # persona_name -> awaiting response
        self._mcp_response_events: Dict[str, asyncio.Event] = {}  # For async waiting

    async def initialize(self):
        """Initialize the orchestrator with session data."""
        if self._initialized:
            return

        async with AsyncSessionLocal() as db:
            # Load session
            result = await db.execute(
                select(Session).where(Session.id == self.session_id)
            )
            session = result.scalar_one_or_none()
            if not session:
                raise ValueError(f"Session {self.session_id} not found")

            self.session = session
            self.config = session.config or {}
            self._mcp_mode = self.config.get("mcp_mode", False)

            # Load session personas
            personas_result = await db.execute(
                select(SessionPersona).where(SessionPersona.session_id == self.session_id)
            )
            session_personas = personas_result.scalars().all()

            # Initialize persona states
            loader = get_persona_loader()
            for sp in session_personas:
                persona = loader.get_persona(sp.persona_name)
                if persona:
                    provider = get_provider(sp.provider)
                    context_mgr = ContextManager(
                        persona_name=sp.persona_name,
                        budget=sp.context_budget,
                        model=sp.model,
                    )
                    self.personas[sp.persona_name] = PersonaState(
                        persona=persona,
                        session_persona=sp,
                        provider=provider,
                        context_manager=context_mgr,
                    )

            # Initialize turn manager
            self.turn_manager = TurnManager(
                mode=session.turn_mode,
                personas=list(self.personas.keys()),
            )

            # Initialize consensus engine
            self.consensus_engine = ConsensusEngine(
                session_id=self.session_id,
                personas=list(self.personas.keys()),
            )

            # Get current turn from messages
            msg_result = await db.execute(
                select(Message)
                .where(Message.session_id == self.session_id)
                .order_by(Message.turn_number.desc())
                .limit(1)
            )
            last_msg = msg_result.scalar_one_or_none()
            self.current_turn = last_msg.turn_number if last_msg else 0

        self._initialized = True
        logger.info(f"Orchestrator initialized for session {self.session_id} with {len(self.personas)} personas")

    async def start_discussion(self):
        """Start the discussion."""
        async with self._lock:
            await self.initialize()

            if self.state == OrchestratorState.RUNNING:
                return

            self.state = OrchestratorState.RUNNING

            # Log start
            async with AsyncSessionLocal() as db:
                audit = AuditLog(
                    session_id=self.session_id,
                    event_type="discussion_start",
                    actor="system",
                    details={"personas": list(self.personas.keys())},
                )
                db.add(audit)
                await db.commit()

            logger.info(f"Discussion started for session {self.session_id}")

    async def pause(self):
        """Pause the discussion."""
        self.state = OrchestratorState.PAUSED
        logger.info(f"Discussion paused for session {self.session_id}")

    async def resume(self):
        """Resume the discussion."""
        if self.state == OrchestratorState.PAUSED:
            self.state = OrchestratorState.RUNNING
            logger.info(f"Discussion resumed for session {self.session_id}")

    async def stop(self):
        """Stop the discussion."""
        self.state = OrchestratorState.STOPPED

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Session).where(Session.id == self.session_id)
            )
            session = result.scalar_one_or_none()
            if session:
                session.status = SessionStatus.PAUSED
                await db.commit()

        logger.info(f"Discussion stopped for session {self.session_id}")

    async def process_user_message(self, content: str, turn_number: int):
        """Process a user message and generate AI responses."""
        await self.initialize()

        if self.state != OrchestratorState.RUNNING:
            await self.start_discussion()

        self.current_turn = turn_number

        # Get conversation history
        history = await self._get_conversation_history()

        # Determine which personas should respond
        if self.session.turn_mode == TurnMode.PARALLEL:
            # All personas respond in parallel
            responding_personas = list(self.personas.keys())
            tasks = [
                self._generate_persona_response(name, history, turn_number)
                for name in responding_personas
            ]
            await asyncio.gather(*tasks)
        else:
            # Get next speaker(s) from turn manager
            speakers = self.turn_manager.get_next_speakers(content)
            for speaker in speakers:
                if self.state != OrchestratorState.RUNNING:
                    break
                await self._generate_persona_response(speaker, history, turn_number)
                # Update history after each response
                history = await self._get_conversation_history()

    async def _generate_persona_response(
        self,
        persona_name: str,
        history: List[Message],
        turn_number: int,
    ):
        """Generate a response from a specific persona."""
        if persona_name not in self.personas:
            logger.warning(f"Unknown persona: {persona_name}")
            return

        persona_state = self.personas[persona_name]
        persona = persona_state.persona
        sp = persona_state.session_persona
        provider = persona_state.provider

        # Notify turn start
        await send_turn_start(self.session_id, persona_name, turn_number)
        await send_persona_thinking(self.session_id, persona_name)

        # Check if MCP mode is enabled - wait for Claude Code to provide response
        if self._mcp_mode:
            await self._await_mcp_response(persona_name, turn_number)
            return

        try:
            # Build system prompt
            context_builder = ContextBuilder(model=sp.model)
            other_personas = [n for n in self.personas.keys() if n != persona_name]

            system_prompt = context_builder.build_system_prompt(
                persona=persona,
                session_config=self.config,
                current_phase=self.session.phase,
                turn_mode=self.session.turn_mode,
                other_personas=other_personas,
                problem_statement=self.session.problem_statement,
            )

            # Build messages
            messages = [
                ChatMessage(
                    role=msg.role,
                    content=msg.content,
                    name=msg.persona_name,
                )
                for msg in history
            ]

            # Stream response
            full_content = ""
            input_tokens = 0
            output_tokens = 0

            async for chunk in provider.generate_stream(
                messages=messages,
                model=sp.model,
                system=system_prompt,
                temperature=0.7,
            ):
                if chunk.content:
                    full_content += chunk.content
                    await send_persona_chunk(self.session_id, persona_name, chunk.content)

                if chunk.is_finished:
                    input_tokens = chunk.input_tokens or 0
                    output_tokens = chunk.output_tokens or 0

            # Save message to database
            async with AsyncSessionLocal() as db:
                message = Message(
                    session_id=self.session_id,
                    persona_name=persona_name,
                    role="assistant",
                    content=full_content,
                    turn_number=turn_number,
                    phase=self.session.phase,
                    metadata={
                        "model": sp.model,
                        "provider": sp.provider,
                    },
                )
                db.add(message)

                # Save token usage
                cost = provider.calculate_cost(input_tokens, output_tokens)
                usage = TokenUsage(
                    session_id=self.session_id,
                    persona_name=persona_name,
                    provider=sp.provider,
                    model=sp.model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost=cost,
                )
                db.add(usage)

                await db.commit()

            # Update persona state
            persona_state.total_input_tokens += input_tokens
            persona_state.total_output_tokens += output_tokens
            persona_state.message_count += 1

            # Notify completion
            await send_persona_done(
                self.session_id,
                persona_name,
                full_content,
                input_tokens,
                output_tokens,
            )

            # Send token update
            await send_token_update(self.session_id, {
                "persona_name": persona_name,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_input": persona_state.total_input_tokens,
                "total_output": persona_state.total_output_tokens,
                "cost": cost,
            })

            # Notify turn end
            await send_turn_end(self.session_id, persona_name, turn_number)

            # Update turn manager
            self.turn_manager.mark_speaker_done(persona_name)

        except Exception as e:
            logger.error(f"Error generating response for {persona_name}: {e}", exc_info=True)
            await ws_manager.broadcast(self.session_id, WSEvent(
                type=WSEventType.PERSONA_ERROR,
                data={"persona_name": persona_name, "error": str(e)},
            ))

    async def _await_mcp_response(self, persona_name: str, turn_number: int):
        """Mark persona as awaiting MCP response from Claude Code."""
        self._pending_mcp_responses[persona_name] = True
        self._mcp_response_events[persona_name] = asyncio.Event()

        # Broadcast that this persona is awaiting a response from Claude Code
        await ws_manager.broadcast(self.session_id, WSEvent(
            type=WSEventType.PERSONA_AWAITING_MCP,
            data={
                "persona_name": persona_name,
                "turn_number": turn_number,
                "message": f"Waiting for Claude Code to generate response as {persona_name}",
            },
        ))

        logger.info(f"Persona {persona_name} awaiting MCP response for session {self.session_id}")

    def get_pending_mcp_responses(self) -> List[str]:
        """Get list of personas awaiting MCP responses."""
        return [name for name, pending in self._pending_mcp_responses.items() if pending]

    async def receive_mcp_response(self, persona_name: str, content: str):
        """Receive a response from Claude Code via MCP."""
        if persona_name not in self._pending_mcp_responses:
            logger.warning(f"Unexpected MCP response for {persona_name}")
            return False

        # Clear pending status
        self._pending_mcp_responses[persona_name] = False

        # Signal the event if anyone is waiting
        if persona_name in self._mcp_response_events:
            self._mcp_response_events[persona_name].set()

        # Notify turn end
        await send_turn_end(self.session_id, persona_name, self.current_turn)

        # Update turn manager
        if self.turn_manager:
            self.turn_manager.mark_speaker_done(persona_name)

        logger.info(f"Received MCP response for {persona_name} in session {self.session_id}")
        return True

    def set_mcp_mode(self, enabled: bool):
        """Enable or disable MCP mode."""
        self._mcp_mode = enabled
        logger.info(f"MCP mode {'enabled' if enabled else 'disabled'} for session {self.session_id}")

    async def _get_conversation_history(self) -> List[Message]:
        """Get conversation history for the session."""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Message)
                .where(Message.session_id == self.session_id)
                .order_by(Message.created_at)
            )
            return list(result.scalars().all())

    async def request_vote(self, proposal: str):
        """Request a vote on a proposal from all personas."""
        await self.initialize()

        self.state = OrchestratorState.VOTING

        await ws_manager.broadcast(self.session_id, WSEvent(
            type=WSEventType.VOTE_REQUEST,
            data={"proposal": proposal},
        ))

        # Get votes from each persona
        votes = await self.consensus_engine.collect_votes(
            proposal=proposal,
            personas=self.personas,
        )

        # Analyze results
        result = await self.consensus_engine.analyze_votes(proposal, votes)

        await ws_manager.broadcast(self.session_id, WSEvent(
            type=WSEventType.VOTE_COMPLETE,
            data=result,
        ))

        self.state = OrchestratorState.RUNNING

    async def advance_phase(self, new_phase: SessionPhase):
        """Advance to a new session phase."""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Session).where(Session.id == self.session_id)
            )
            session = result.scalar_one_or_none()
            if session:
                old_phase = session.phase
                session.phase = new_phase
                session.version += 1
                self.session = session

                audit = AuditLog(
                    session_id=self.session_id,
                    event_type="phase_change",
                    actor="orchestrator",
                    details={"old_phase": old_phase.value, "new_phase": new_phase.value},
                )
                db.add(audit)
                await db.commit()

        await ws_manager.broadcast(self.session_id, WSEvent(
            type=WSEventType.PHASE_CHANGE,
            data={"old_phase": old_phase.value, "new_phase": new_phase.value},
        ))


# Orchestrator registry
_orchestrators: Dict[int, Orchestrator] = {}


def get_orchestrator(session_id: int) -> Orchestrator:
    """Get or create an orchestrator for a session."""
    if session_id not in _orchestrators:
        _orchestrators[session_id] = Orchestrator(session_id)
    return _orchestrators[session_id]


def remove_orchestrator(session_id: int):
    """Remove an orchestrator from the registry."""
    if session_id in _orchestrators:
        del _orchestrators[session_id]
