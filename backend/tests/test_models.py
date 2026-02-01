"""Tests for database models."""

import pytest
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.db.models import (
    Session, SessionPersona, Message, TokenUsage, Vote, Insight,
    Scratchpad, AuditLog, SessionPhase, SessionStatus, TurnMode,
    VoteType, InsightType
)


class TestSessionModel:
    """Tests for Session model."""

    async def test_create_session(self, db_session: AsyncSession):
        """Test creating a basic session."""
        session = Session(
            name="Test Session",
            problem_statement="Test problem",
        )
        db_session.add(session)
        await db_session.commit()
        await db_session.refresh(session)

        assert session.id is not None
        assert session.name == "Test Session"
        assert session.problem_statement == "Test problem"
        assert session.status == SessionStatus.ACTIVE
        assert session.phase == SessionPhase.DISCOVERY
        assert session.turn_mode == TurnMode.ROUND_ROBIN
        assert session.version == 1

    async def test_session_defaults(self, db_session: AsyncSession):
        """Test session default values."""
        session = Session(name="Defaults Test")
        db_session.add(session)
        await db_session.commit()
        await db_session.refresh(session)

        assert session.status == SessionStatus.ACTIVE
        assert session.phase == SessionPhase.DISCOVERY
        assert session.turn_mode == TurnMode.ROUND_ROBIN
        assert session.config == {}
        assert session.version == 1
        assert session.created_at is not None

    async def test_session_phases(self, db_session: AsyncSession):
        """Test all session phases."""
        for phase in SessionPhase:
            session = Session(name=f"Phase {phase.value}", phase=phase)
            db_session.add(session)
        await db_session.commit()

        result = await db_session.execute(select(Session))
        sessions = result.scalars().all()
        phases = {s.phase for s in sessions}
        assert phases == set(SessionPhase)

    async def test_session_statuses(self, db_session: AsyncSession):
        """Test all session statuses."""
        for status in SessionStatus:
            session = Session(name=f"Status {status.value}", status=status)
            db_session.add(session)
        await db_session.commit()

        result = await db_session.execute(select(Session))
        sessions = result.scalars().all()
        statuses = {s.status for s in sessions}
        assert statuses == set(SessionStatus)

    async def test_session_turn_modes(self, db_session: AsyncSession):
        """Test all turn modes."""
        for mode in TurnMode:
            session = Session(name=f"Mode {mode.value}", turn_mode=mode)
            db_session.add(session)
        await db_session.commit()

        result = await db_session.execute(select(Session))
        sessions = result.scalars().all()
        modes = {s.turn_mode for s in sessions}
        assert modes == set(TurnMode)


class TestSessionPersonaModel:
    """Tests for SessionPersona model."""

    async def test_create_session_persona(self, db_session: AsyncSession, sample_session: Session):
        """Test creating a session persona."""
        persona = SessionPersona(
            session_id=sample_session.id,
            persona_name="albert-einstein",
            provider="anthropic",
            model="claude-sonnet-4-20250514",
            role="participant",
            color="#3B82F6",
        )
        db_session.add(persona)
        await db_session.commit()
        await db_session.refresh(persona)

        assert persona.id is not None
        assert persona.session_id == sample_session.id
        assert persona.persona_name == "albert-einstein"
        assert persona.provider == "anthropic"
        assert persona.is_active is True

    async def test_session_persona_defaults(self, db_session: AsyncSession, sample_session: Session):
        """Test session persona default values."""
        persona = SessionPersona(
            session_id=sample_session.id,
            persona_name="test-persona",
            provider="openai",
            model="gpt-4",
        )
        db_session.add(persona)
        await db_session.commit()
        await db_session.refresh(persona)

        assert persona.role == "participant"
        assert persona.context_budget == 50000
        assert persona.is_active is True

    async def test_session_persona_roles(self, db_session: AsyncSession, sample_session: Session):
        """Test different persona roles."""
        roles = ["participant", "moderator", "devil_advocate", "synthesizer"]
        for role in roles:
            persona = SessionPersona(
                session_id=sample_session.id,
                persona_name=f"persona-{role}",
                provider="anthropic",
                model="claude-sonnet-4-20250514",
                role=role,
            )
            db_session.add(persona)
        await db_session.commit()

        result = await db_session.execute(
            select(SessionPersona).where(SessionPersona.session_id == sample_session.id)
        )
        personas = result.scalars().all()
        assert len(personas) == 4


class TestMessageModel:
    """Tests for Message model."""

    async def test_create_user_message(self, db_session: AsyncSession, sample_session: Session):
        """Test creating a user message."""
        message = Message(
            session_id=sample_session.id,
            role="user",
            content="Hello, world!",
            turn_number=1,
        )
        db_session.add(message)
        await db_session.commit()
        await db_session.refresh(message)

        assert message.id is not None
        assert message.persona_name is None
        assert message.role == "user"
        assert message.content == "Hello, world!"

    async def test_create_assistant_message(self, db_session: AsyncSession, sample_session: Session):
        """Test creating an assistant message."""
        message = Message(
            session_id=sample_session.id,
            persona_name="albert-einstein",
            role="assistant",
            content="E = mc²",
            turn_number=2,
            phase=SessionPhase.IDEATION,
        )
        db_session.add(message)
        await db_session.commit()
        await db_session.refresh(message)

        assert message.persona_name == "albert-einstein"
        assert message.role == "assistant"
        assert message.phase == SessionPhase.IDEATION

    async def test_message_extra_data(self, db_session: AsyncSession, sample_session: Session):
        """Test message extra_data field."""
        message = Message(
            session_id=sample_session.id,
            role="assistant",
            persona_name="test",
            content="Test",
            turn_number=1,
            extra_data={"citations": ["source1", "source2"], "confidence": 0.95},
        )
        db_session.add(message)
        await db_session.commit()
        await db_session.refresh(message)

        assert message.extra_data["citations"] == ["source1", "source2"]
        assert message.extra_data["confidence"] == 0.95


class TestTokenUsageModel:
    """Tests for TokenUsage model."""

    async def test_create_token_usage(self, db_session: AsyncSession, sample_session: Session):
        """Test creating token usage record."""
        usage = TokenUsage(
            session_id=sample_session.id,
            persona_name="albert-einstein",
            provider="anthropic",
            model="claude-sonnet-4-20250514",
            input_tokens=100,
            output_tokens=200,
            cost=0.003,
        )
        db_session.add(usage)
        await db_session.commit()
        await db_session.refresh(usage)

        assert usage.id is not None
        assert usage.input_tokens == 100
        assert usage.output_tokens == 200
        assert usage.cost == 0.003

    async def test_token_usage_defaults(self, db_session: AsyncSession, sample_session: Session):
        """Test token usage default values."""
        usage = TokenUsage(
            session_id=sample_session.id,
            persona_name="test",
            provider="openai",
            model="gpt-4",
        )
        db_session.add(usage)
        await db_session.commit()
        await db_session.refresh(usage)

        assert usage.input_tokens == 0
        assert usage.output_tokens == 0
        assert usage.cost == 0.0


class TestVoteModel:
    """Tests for Vote model."""

    async def test_create_vote(self, db_session: AsyncSession, sample_session: Session):
        """Test creating a vote."""
        vote = Vote(
            session_id=sample_session.id,
            proposal="Should we use TDD?",
            persona_name="albert-einstein",
            vote=VoteType.AGREE,
            reasoning="Testing leads to better code.",
            confidence=0.9,
        )
        db_session.add(vote)
        await db_session.commit()
        await db_session.refresh(vote)

        assert vote.id is not None
        assert vote.vote == VoteType.AGREE
        assert vote.confidence == 0.9

    async def test_vote_types(self, db_session: AsyncSession, sample_session: Session):
        """Test all vote types."""
        for i, vote_type in enumerate(VoteType):
            vote = Vote(
                session_id=sample_session.id,
                proposal=f"Proposal {i}",
                persona_name=f"persona-{i}",
                vote=vote_type,
            )
            db_session.add(vote)
        await db_session.commit()

        result = await db_session.execute(
            select(Vote).where(Vote.session_id == sample_session.id)
        )
        votes = result.scalars().all()
        vote_types = {v.vote for v in votes}
        assert vote_types == set(VoteType)


class TestInsightModel:
    """Tests for Insight model."""

    async def test_create_insight(self, db_session: AsyncSession, sample_session: Session):
        """Test creating an insight."""
        insight = Insight(
            session_id=sample_session.id,
            insight_type=InsightType.KEY_POINT,
            content="Testing is essential for quality software.",
            importance=0.8,
        )
        db_session.add(insight)
        await db_session.commit()
        await db_session.refresh(insight)

        assert insight.id is not None
        assert insight.insight_type == InsightType.KEY_POINT
        assert insight.importance == 0.8

    async def test_insight_types(self, db_session: AsyncSession, sample_session: Session):
        """Test all insight types."""
        for insight_type in InsightType:
            insight = Insight(
                session_id=sample_session.id,
                insight_type=insight_type,
                content=f"Insight of type {insight_type.value}",
            )
            db_session.add(insight)
        await db_session.commit()

        result = await db_session.execute(
            select(Insight).where(Insight.session_id == sample_session.id)
        )
        insights = result.scalars().all()
        types = {i.insight_type for i in insights}
        assert types == set(InsightType)


class TestScratchpadModel:
    """Tests for Scratchpad model."""

    async def test_create_scratchpad_entry(self, db_session: AsyncSession, sample_session: Session):
        """Test creating a scratchpad entry."""
        entry = Scratchpad(
            session_id=sample_session.id,
            key="main_idea",
            value="Testing improves code quality",
            author_persona="albert-einstein",
        )
        db_session.add(entry)
        await db_session.commit()
        await db_session.refresh(entry)

        assert entry.id is not None
        assert entry.key == "main_idea"
        assert entry.version == 1

    async def test_scratchpad_versioning(self, db_session: AsyncSession, sample_session: Session):
        """Test scratchpad version tracking."""
        entry = Scratchpad(
            session_id=sample_session.id,
            key="evolving_idea",
            value="Version 1",
            version=1,
        )
        db_session.add(entry)
        await db_session.commit()

        entry2 = Scratchpad(
            session_id=sample_session.id,
            key="evolving_idea",
            value="Version 2",
            version=2,
        )
        db_session.add(entry2)
        await db_session.commit()

        result = await db_session.execute(
            select(Scratchpad)
            .where(Scratchpad.session_id == sample_session.id)
            .where(Scratchpad.key == "evolving_idea")
        )
        entries = result.scalars().all()
        assert len(entries) == 2


class TestAuditLogModel:
    """Tests for AuditLog model."""

    async def test_create_audit_log(self, db_session: AsyncSession, sample_session: Session):
        """Test creating an audit log entry."""
        log = AuditLog(
            session_id=sample_session.id,
            event_type="session_created",
            actor="user",
            details={"source": "api"},
        )
        db_session.add(log)
        await db_session.commit()
        await db_session.refresh(log)

        assert log.id is not None
        assert log.event_type == "session_created"
        assert log.created_at is not None

    async def test_audit_log_events(self, db_session: AsyncSession, sample_session: Session):
        """Test various audit log events."""
        events = [
            ("session_created", "user"),
            ("persona_added", "user"),
            ("message_sent", "albert-einstein"),
            ("phase_changed", "system"),
            ("vote_cast", "richard-feynman"),
        ]
        for event_type, actor in events:
            log = AuditLog(
                session_id=sample_session.id,
                event_type=event_type,
                actor=actor,
            )
            db_session.add(log)
        await db_session.commit()

        result = await db_session.execute(
            select(AuditLog).where(AuditLog.session_id == sample_session.id)
        )
        logs = result.scalars().all()
        assert len(logs) == 5
