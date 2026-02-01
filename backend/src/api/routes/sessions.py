"""Session API routes."""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import datetime

from ...db.database import get_db
from ...db.models import (
    Session, SessionPersona, Message, TokenUsage,
    SessionStatus, SessionPhase, TurnMode,
)

router = APIRouter()


# Request/Response Models

class PersonaConfig(BaseModel):
    """Configuration for a persona in a session."""
    persona_name: str
    provider: str = "anthropic"
    model: str = "claude-sonnet-4-20250514"
    role: str = "participant"
    color: Optional[str] = None


class SessionConfig(BaseModel):
    """Session configuration options."""
    require_citations: bool = False
    steelman_mode: bool = False
    devil_advocate: bool = False
    fact_check: bool = False
    assumption_surfacing: bool = False
    blind_spot_detection: bool = False
    time_box_minutes: Optional[int] = None
    max_turns: Optional[int] = None
    min_rounds: int = 3  # Minimum discussion rounds
    max_rounds: int = 3  # Maximum discussion rounds (can be same as min for fixed)
    web_search_enabled: bool = False
    code_execution_enabled: bool = False
    mcp_mode: bool = False  # Use Claude Code to power responses via MCP


class CreateSessionRequest(BaseModel):
    """Request to create a new session."""
    name: str = Field(..., min_length=1, max_length=255)
    problem_statement: Optional[str] = None
    personas: List[PersonaConfig] = Field(..., min_length=1, max_length=5)
    turn_mode: TurnMode = TurnMode.ROUND_ROBIN
    config: SessionConfig = Field(default_factory=SessionConfig)


class UpdateSessionRequest(BaseModel):
    """Request to update a session."""
    name: Optional[str] = None
    problem_statement: Optional[str] = None
    phase: Optional[SessionPhase] = None
    turn_mode: Optional[TurnMode] = None
    status: Optional[SessionStatus] = None
    config: Optional[SessionConfig] = None


class SessionPersonaResponse(BaseModel):
    """Persona in a session response."""
    id: int
    persona_name: str
    display_name: Optional[str]
    provider: str
    model: str
    role: str
    color: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True


class SessionResponse(BaseModel):
    """Session response."""
    id: int
    name: str
    problem_statement: Optional[str]
    status: SessionStatus
    phase: SessionPhase
    turn_mode: TurnMode
    config: dict
    version: int
    created_at: datetime
    updated_at: Optional[datetime]
    personas: List[SessionPersonaResponse] = []

    class Config:
        from_attributes = True


class SessionSummary(BaseModel):
    """Summary of a session for list views."""
    id: int
    name: str
    status: SessionStatus
    phase: SessionPhase
    persona_count: int
    message_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    """Message response."""
    id: int
    persona_name: Optional[str]
    role: str
    content: str
    turn_number: int
    round_number: Optional[int] = 1  # Discussion round within a turn
    phase: Optional[SessionPhase]
    extra_data: dict
    created_at: datetime

    class Config:
        from_attributes = True


# Routes

@router.post("/", response_model=SessionResponse)
async def create_session(
    request: CreateSessionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a new collaboration session."""
    # Create session
    session = Session(
        name=request.name,
        problem_statement=request.problem_statement,
        turn_mode=request.turn_mode,
        config=request.config.model_dump(),
    )
    db.add(session)
    await db.flush()

    # Add personas
    colors = ["#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6"]
    for i, persona_config in enumerate(request.personas):
        session_persona = SessionPersona(
            session_id=session.id,
            persona_name=persona_config.persona_name,
            provider=persona_config.provider,
            model=persona_config.model,
            role=persona_config.role,
            color=persona_config.color or colors[i % len(colors)],
        )
        db.add(session_persona)

    # AUTO-START: If problem_statement provided, create it as the first user message
    # This kicks off the discussion immediately
    if request.problem_statement:
        first_message = Message(
            session_id=session.id,
            persona_name=None,  # User message
            role="user",
            content=request.problem_statement,
            turn_number=1,
            round_number=1,
            phase=session.phase,
        )
        db.add(first_message)

    await db.commit()
    await db.refresh(session)

    # Load personas relationship
    result = await db.execute(
        select(SessionPersona).where(SessionPersona.session_id == session.id)
    )
    personas = result.scalars().all()

    return SessionResponse(
        id=session.id,
        name=session.name,
        problem_statement=session.problem_statement,
        status=session.status,
        phase=session.phase,
        turn_mode=session.turn_mode,
        config=session.config,
        version=session.version,
        created_at=session.created_at,
        updated_at=session.updated_at,
        personas=[SessionPersonaResponse.model_validate(p) for p in personas],
    )


@router.get("/", response_model=List[SessionSummary])
async def list_sessions(
    status: Optional[SessionStatus] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List all sessions."""
    query = select(Session).order_by(desc(Session.created_at))

    if status:
        query = query.where(Session.status == status)

    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    sessions = result.scalars().all()

    summaries = []
    for session in sessions:
        # Get counts
        persona_result = await db.execute(
            select(SessionPersona).where(SessionPersona.session_id == session.id)
        )
        persona_count = len(persona_result.scalars().all())

        message_result = await db.execute(
            select(Message).where(Message.session_id == session.id)
        )
        message_count = len(message_result.scalars().all())

        summaries.append(SessionSummary(
            id=session.id,
            name=session.name,
            status=session.status,
            phase=session.phase,
            persona_count=persona_count,
            message_count=message_count,
            created_at=session.created_at,
        ))

    return summaries


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific session."""
    result = await db.execute(
        select(Session).where(Session.id == session_id)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Load personas
    personas_result = await db.execute(
        select(SessionPersona).where(SessionPersona.session_id == session.id)
    )
    personas = personas_result.scalars().all()

    return SessionResponse(
        id=session.id,
        name=session.name,
        problem_statement=session.problem_statement,
        status=session.status,
        phase=session.phase,
        turn_mode=session.turn_mode,
        config=session.config,
        version=session.version,
        created_at=session.created_at,
        updated_at=session.updated_at,
        personas=[SessionPersonaResponse.model_validate(p) for p in personas],
    )


@router.patch("/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: int,
    request: UpdateSessionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update a session."""
    result = await db.execute(
        select(Session).where(Session.id == session_id)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Update fields
    if request.name is not None:
        session.name = request.name
    if request.problem_statement is not None:
        session.problem_statement = request.problem_statement
    if request.phase is not None:
        session.phase = request.phase
    if request.turn_mode is not None:
        session.turn_mode = request.turn_mode
    if request.status is not None:
        session.status = request.status
    if request.config is not None:
        session.config = request.config.model_dump()

    session.version += 1
    await db.commit()
    await db.refresh(session)

    # Load personas
    personas_result = await db.execute(
        select(SessionPersona).where(SessionPersona.session_id == session.id)
    )
    personas = personas_result.scalars().all()

    return SessionResponse(
        id=session.id,
        name=session.name,
        problem_statement=session.problem_statement,
        status=session.status,
        phase=session.phase,
        turn_mode=session.turn_mode,
        config=session.config,
        version=session.version,
        created_at=session.created_at,
        updated_at=session.updated_at,
        personas=[SessionPersonaResponse.model_validate(p) for p in personas],
    )


@router.delete("/{session_id}")
async def delete_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a session."""
    result = await db.execute(
        select(Session).where(Session.id == session_id)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    await db.delete(session)
    await db.commit()

    return {"status": "deleted", "session_id": session_id}


@router.get("/{session_id}/messages", response_model=List[MessageResponse])
async def get_session_messages(
    session_id: int,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Get messages for a session."""
    result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at)
        .offset(offset)
        .limit(limit)
    )
    messages = result.scalars().all()

    return [MessageResponse.model_validate(m) for m in messages]


@router.get("/{session_id}/token-usage")
async def get_token_usage(
    session_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get token usage for a session."""
    result = await db.execute(
        select(TokenUsage).where(TokenUsage.session_id == session_id)
    )
    usages = result.scalars().all()

    # Aggregate by persona and provider
    by_persona = {}
    by_provider = {}
    total_input = 0
    total_output = 0
    total_cost = 0.0

    for usage in usages:
        # By persona
        if usage.persona_name not in by_persona:
            by_persona[usage.persona_name] = {
                "input_tokens": 0,
                "output_tokens": 0,
                "cost": 0.0,
            }
        by_persona[usage.persona_name]["input_tokens"] += usage.input_tokens
        by_persona[usage.persona_name]["output_tokens"] += usage.output_tokens
        by_persona[usage.persona_name]["cost"] += usage.cost

        # By provider
        if usage.provider not in by_provider:
            by_provider[usage.provider] = {
                "input_tokens": 0,
                "output_tokens": 0,
                "cost": 0.0,
            }
        by_provider[usage.provider]["input_tokens"] += usage.input_tokens
        by_provider[usage.provider]["output_tokens"] += usage.output_tokens
        by_provider[usage.provider]["cost"] += usage.cost

        total_input += usage.input_tokens
        total_output += usage.output_tokens
        total_cost += usage.cost

    return {
        "session_id": session_id,
        "total": {
            "input_tokens": total_input,
            "output_tokens": total_output,
            "total_tokens": total_input + total_output,
            "cost": total_cost,
        },
        "by_persona": by_persona,
        "by_provider": by_provider,
    }
