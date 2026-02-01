"""Shared test fixtures and configuration."""

import pytest
import asyncio
from typing import AsyncGenerator, Generator
from pathlib import Path
import tempfile
import shutil
import os

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from httpx import AsyncClient, ASGITransport

# Set test environment before importing app modules
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["ANTHROPIC_API_KEY"] = "test-key"
os.environ["DEBUG"] = "true"

from src.main import app
from src.db.database import Base, get_db
from src.db.models import Session, SessionPersona, Message, TokenUsage, Vote, Insight, Scratchpad, AuditLog


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def async_engine():
    """Create async engine for testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async_session_maker = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with async_session_maker() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def client(async_engine) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with overridden database."""
    async_session_maker = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with async_session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def temp_personas_dir() -> Generator[Path, None, None]:
    """Create a temporary directory with mock persona files."""
    temp_dir = Path(tempfile.mkdtemp())
    experts_dir = temp_dir / "experts"
    experts_dir.mkdir()

    # Create mock personas
    personas = [
        ("albert-einstein", "Scientists", "Albert Einstein"),
        ("richard-feynman", "Scientists", "Richard Feynman"),
        ("ada-lovelace", "Scientists", "Ada Lovelace"),
        ("socrates", "Philosophers", "Socrates"),
        ("plato", "Philosophers", "Plato"),
    ]

    for slug, domain, display_name in personas:
        persona_dir = experts_dir / slug
        persona_dir.mkdir()

        # Create PROMPT.md
        prompt_content = f"""# {display_name}

## Voice Profile
{display_name} speaks with clarity and insight.

## Core Philosophy
Knowledge is the foundation of wisdom.

## Methodology
- Ask questions
- Seek evidence
- Draw conclusions

## Signature Quotes
- "The important thing is not to stop questioning."
- "Imagination is more important than knowledge."
"""
        (persona_dir / "PROMPT.md").write_text(prompt_content)

        # Create info.yaml
        info_content = f"""name: {slug}
display_name: {display_name}
domain: {domain}
era: "Historical"
"""
        (persona_dir / "info.yaml").write_text(info_content)

    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_persona_data():
    """Return mock persona data for testing."""
    return {
        "name": "test-persona",
        "display_name": "Test Persona",
        "domain": "Testing",
        "era": "Modern",
        "voice_profile": "Speaks clearly and concisely.",
        "core_philosophy": "Test everything.",
        "methodology": "Write tests, run tests, fix bugs.",
        "signature_quotes": ["Testing is believing.", "Coverage is king."],
    }


@pytest.fixture
async def sample_session(db_session: AsyncSession) -> Session:
    """Create a sample session for testing."""
    session = Session(
        name="Test Session",
        problem_statement="How do we test effectively?",
        turn_mode="round_robin",
        config={},
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)
    return session


@pytest.fixture
async def sample_session_with_personas(db_session: AsyncSession, sample_session: Session) -> Session:
    """Create a session with personas attached."""
    personas = [
        SessionPersona(
            session_id=sample_session.id,
            persona_name="albert-einstein",
            provider="anthropic",
            model="claude-sonnet-4-20250514",
            role="participant",
            color="#3B82F6",
        ),
        SessionPersona(
            session_id=sample_session.id,
            persona_name="richard-feynman",
            provider="anthropic",
            model="claude-sonnet-4-20250514",
            role="participant",
            color="#10B981",
        ),
    ]
    for p in personas:
        db_session.add(p)
    await db_session.commit()
    await db_session.refresh(sample_session)
    return sample_session


@pytest.fixture
async def sample_messages(db_session: AsyncSession, sample_session: Session) -> list[Message]:
    """Create sample messages for testing."""
    messages = [
        Message(
            session_id=sample_session.id,
            persona_name=None,
            role="user",
            content="What is the meaning of life?",
            turn_number=1,
        ),
        Message(
            session_id=sample_session.id,
            persona_name="albert-einstein",
            role="assistant",
            content="The meaning of life is to seek understanding.",
            turn_number=2,
        ),
        Message(
            session_id=sample_session.id,
            persona_name="richard-feynman",
            role="assistant",
            content="The meaning is in the joy of finding things out.",
            turn_number=3,
        ),
    ]
    for m in messages:
        db_session.add(m)
    await db_session.commit()
    return messages
