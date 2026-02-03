"""SQLAlchemy models for the Multi-Agent Collaboration Platform."""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
    Enum as SQLEnum,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from enum import Enum
from typing import Optional, List

from .database import Base


class SessionPhase(str, Enum):
    """Session phases for the collaboration workflow."""
    DISCOVERY = "discovery"
    IDEATION = "ideation"
    EVALUATION = "evaluation"
    DECISION = "decision"
    ACTION = "action"
    SYNTHESIS = "synthesis"


class SessionStatus(str, Enum):
    """Session status values."""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class TurnMode(str, Enum):
    """Turn-taking modes for conversation."""
    ROUND_ROBIN = "round_robin"
    MODERATOR = "moderator"
    FREE_FORM = "free_form"
    INTERRUPT = "interrupt"
    PARALLEL = "parallel"


class VoteType(str, Enum):
    """Types of voting."""
    AGREE = "agree"
    DISAGREE = "disagree"
    ABSTAIN = "abstain"
    RANK = "rank"


class PollPhase(str, Enum):
    """Phases for multi-round poll mode."""
    SYNTHESIS = "synthesis"      # Round 1: Frame question, suggest solutions
    VOTE_ROUND_1 = "vote_round_1"  # First vote: Rank all options → narrow to top 5
    VOTE_ROUND_2 = "vote_round_2"  # Final vote: Vote on 5 options → 3 result formats
    COMPLETED = "completed"       # Poll finished


class InsightType(str, Enum):
    """Types of insights extracted from conversation."""
    CONSENSUS = "consensus"
    DISAGREEMENT = "disagreement"
    KEY_POINT = "key_point"
    ACTION_ITEM = "action_item"
    QUESTION = "question"
    BIAS_WARNING = "bias_warning"
    SCOPE_CREEP = "scope_creep"


class Session(Base):
    """A collaboration session with multiple personas."""
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    problem_statement = Column(Text, nullable=True)
    status = Column(SQLEnum(SessionStatus), default=SessionStatus.ACTIVE)
    phase = Column(SQLEnum(SessionPhase), default=SessionPhase.DISCOVERY)
    turn_mode = Column(SQLEnum(TurnMode), default=TurnMode.ROUND_ROBIN)
    config = Column(JSON, default=dict)
    version = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    personas = relationship("SessionPersona", back_populates="session", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")
    token_usage = relationship("TokenUsage", back_populates="session", cascade="all, delete-orphan")
    scratchpad = relationship("Scratchpad", back_populates="session", cascade="all, delete-orphan")
    votes = relationship("Vote", back_populates="session", cascade="all, delete-orphan")
    insights = relationship("Insight", back_populates="session", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="session", cascade="all, delete-orphan")


class SessionPersona(Base):
    """A persona participating in a session."""
    __tablename__ = "session_personas"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    persona_name = Column(String(255), nullable=False)  # References the markdown persona
    display_name = Column(String(255), nullable=True)  # Custom display name
    provider = Column(String(50), nullable=False)  # anthropic, openai
    model = Column(String(100), nullable=False)
    role = Column(String(50), default="participant")  # participant, moderator, devil_advocate, synthesizer
    color = Column(String(7), nullable=True)  # Hex color for UI
    context_budget = Column(Integer, default=50000)  # Token budget for this persona
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    session = relationship("Session", back_populates="personas")


class Message(Base):
    """A message in a session conversation."""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    persona_name = Column(String(255), nullable=True)  # None for user/system messages
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    turn_number = Column(Integer, default=0)  # Which user message this relates to
    round_number = Column(Integer, default=1)  # Discussion round within a turn (1=initial, 2+=replies)
    phase = Column(SQLEnum(SessionPhase), nullable=True)
    extra_data = Column(JSON, default=dict)  # Additional data like citations, confidence
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    session = relationship("Session", back_populates="messages")


class TokenUsage(Base):
    """Token usage tracking per persona per session."""
    __tablename__ = "token_usage"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    persona_name = Column(String(255), nullable=False)
    provider = Column(String(50), nullable=False)
    model = Column(String(100), nullable=False)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    cost = Column(Float, default=0.0)  # Estimated cost in USD
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    session = relationship("Session", back_populates="token_usage")


class Scratchpad(Base):
    """Shared working memory for a session."""
    __tablename__ = "scratchpad"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    key = Column(String(255), nullable=False)
    value = Column(Text, nullable=False)
    author_persona = Column(String(255), nullable=True)
    version = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    session = relationship("Session", back_populates="scratchpad")


class Vote(Base):
    """Voting records for consensus tracking."""
    __tablename__ = "votes"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    proposal = Column(Text, nullable=False)
    proposal_id = Column(String(100), nullable=True)  # For linking related votes
    persona_name = Column(String(255), nullable=False)
    vote = Column(SQLEnum(VoteType), nullable=False)
    rank = Column(Integer, nullable=True)  # For ranked-choice voting
    reasoning = Column(Text, nullable=True)
    confidence = Column(Float, default=1.0)  # 0.0 to 1.0
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    session = relationship("Session", back_populates="votes")


class Insight(Base):
    """Extracted insights from the conversation."""
    __tablename__ = "insights"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    insight_type = Column(SQLEnum(InsightType), nullable=False)
    content = Column(Text, nullable=False)
    source_message_ids = Column(JSON, default=list)  # Message IDs that contributed
    personas_involved = Column(JSON, default=list)
    importance = Column(Float, default=0.5)  # 0.0 to 1.0
    phase = Column(SQLEnum(SessionPhase), nullable=True)
    extra_data = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    session = relationship("Session", back_populates="insights")


class AuditLog(Base):
    """Full audit trail for sessions."""
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String(100), nullable=False)
    actor = Column(String(255), nullable=True)  # persona name or "user" or "system"
    details = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    session = relationship("Session", back_populates="audit_logs")


class PendingVoteRequest(Base):
    """Pending vote requests waiting for MCP/Claude Code responses."""
    __tablename__ = "pending_vote_requests"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    proposal = Column(Text, nullable=False)
    proposal_id = Column(String(100), nullable=False)  # Unique ID for this vote request
    status = Column(String(20), default="pending")  # pending, in_progress, completed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    session = relationship("Session")


class Poll(Base):
    """A multi-phase poll for collecting and voting on options."""
    __tablename__ = "polls"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    poll_id = Column(String(100), nullable=False, unique=True)  # Unique identifier
    question = Column(Text, nullable=False)  # Original question
    framed_question = Column(Text, nullable=True)  # Synthesized/framed version
    phase = Column(SQLEnum(PollPhase), default=PollPhase.SYNTHESIS)
    parent_poll_id = Column(String(100), nullable=True)  # For sub-polls of complex questions
    synthesis_responses = Column(JSON, default=dict)  # {persona_name: {"framing": "...", "options": [...]}}
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    session = relationship("Session")
    options = relationship("PollOption", back_populates="poll", cascade="all, delete-orphan")
    votes = relationship("PollVote", back_populates="poll", cascade="all, delete-orphan")


class PollOption(Base):
    """An option proposed during poll synthesis phase."""
    __tablename__ = "poll_options"

    id = Column(Integer, primary_key=True, index=True)
    poll_id = Column(Integer, ForeignKey("polls.id", ondelete="CASCADE"), nullable=False)
    option_text = Column(Text, nullable=False)
    proposed_by = Column(String(255), nullable=True)  # Persona who proposed it
    is_active = Column(Boolean, default=True)  # False if eliminated in round 1
    round_1_score = Column(Float, nullable=True)  # Score after first vote
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    poll = relationship("Poll", back_populates="options")


class PollVote(Base):
    """A vote on a poll option (supports ranked choice)."""
    __tablename__ = "poll_votes"

    id = Column(Integer, primary_key=True, index=True)
    poll_id = Column(Integer, ForeignKey("polls.id", ondelete="CASCADE"), nullable=False)
    option_id = Column(Integer, ForeignKey("poll_options.id", ondelete="CASCADE"), nullable=False)
    persona_name = Column(String(255), nullable=False)
    vote_round = Column(Integer, nullable=False)  # 1 or 2
    rank = Column(Integer, nullable=True)  # For ranked choice (1 = first choice)
    vote_value = Column(String(20), nullable=True)  # agree/disagree/abstain for round 2
    confidence = Column(Float, default=1.0)
    reasoning = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    poll = relationship("Poll", back_populates="votes")
    option = relationship("PollOption")
