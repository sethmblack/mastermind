"""Tests for session API routes."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.db.models import Session, SessionPersona, Message, SessionStatus, SessionPhase, TurnMode


class TestCreateSession:
    """Tests for POST /api/sessions/"""

    async def test_create_session_success(self, client: AsyncClient):
        """Test successful session creation."""
        response = await client.post(
            "/api/sessions/",
            json={
                "name": "Test Session",
                "problem_statement": "How do we test APIs?",
                "personas": [
                    {"persona_name": "albert-einstein", "provider": "anthropic", "model": "claude-sonnet-4-20250514"},
                    {"persona_name": "richard-feynman", "provider": "anthropic", "model": "claude-sonnet-4-20250514"},
                ],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Session"
        assert data["problem_statement"] == "How do we test APIs?"
        assert len(data["personas"]) == 2
        assert data["status"] == "active"
        assert data["phase"] == "discovery"

    async def test_create_session_minimal(self, client: AsyncClient):
        """Test creating session with minimal data."""
        response = await client.post(
            "/api/sessions/",
            json={
                "name": "Minimal Session",
                "personas": [
                    {"persona_name": "test-persona", "provider": "anthropic", "model": "claude-sonnet-4-20250514"},
                ],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Minimal Session"
        assert data["problem_statement"] is None

    async def test_create_session_with_turn_mode(self, client: AsyncClient):
        """Test creating session with specific turn mode."""
        response = await client.post(
            "/api/sessions/",
            json={
                "name": "Moderator Session",
                "personas": [
                    {"persona_name": "test", "provider": "anthropic", "model": "claude-sonnet-4-20250514"},
                ],
                "turn_mode": "moderator",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["turn_mode"] == "moderator"

    async def test_create_session_with_config(self, client: AsyncClient):
        """Test creating session with custom config."""
        response = await client.post(
            "/api/sessions/",
            json={
                "name": "Configured Session",
                "personas": [
                    {"persona_name": "test", "provider": "anthropic", "model": "claude-sonnet-4-20250514"},
                ],
                "config": {
                    "require_citations": True,
                    "steelman_mode": True,
                },
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["config"]["require_citations"] is True
        assert data["config"]["steelman_mode"] is True

    async def test_create_session_max_personas(self, client: AsyncClient):
        """Test creating session with maximum 5 personas."""
        response = await client.post(
            "/api/sessions/",
            json={
                "name": "Full Session",
                "personas": [
                    {"persona_name": f"persona-{i}", "provider": "anthropic", "model": "claude-sonnet-4-20250514"}
                    for i in range(5)
                ],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["personas"]) == 5

    async def test_create_session_no_name_fails(self, client: AsyncClient):
        """Test that session without name fails validation."""
        response = await client.post(
            "/api/sessions/",
            json={
                "personas": [
                    {"persona_name": "test", "provider": "anthropic", "model": "claude-sonnet-4-20250514"},
                ],
            },
        )
        assert response.status_code == 422

    async def test_create_session_no_personas_fails(self, client: AsyncClient):
        """Test that session without personas fails validation."""
        response = await client.post(
            "/api/sessions/",
            json={
                "name": "No Personas",
                "personas": [],
            },
        )
        assert response.status_code == 422

    async def test_create_session_persona_colors(self, client: AsyncClient):
        """Test that personas get assigned colors."""
        response = await client.post(
            "/api/sessions/",
            json={
                "name": "Colored Session",
                "personas": [
                    {"persona_name": "p1", "provider": "anthropic", "model": "claude-sonnet-4-20250514"},
                    {"persona_name": "p2", "provider": "anthropic", "model": "claude-sonnet-4-20250514"},
                ],
            },
        )
        assert response.status_code == 200
        data = response.json()
        colors = [p["color"] for p in data["personas"]]
        assert all(c.startswith("#") for c in colors)
        assert colors[0] != colors[1]  # Different colors


class TestListSessions:
    """Tests for GET /api/sessions/"""

    async def test_list_sessions_empty(self, client: AsyncClient):
        """Test listing sessions when none exist."""
        response = await client.get("/api/sessions/")
        assert response.status_code == 200
        assert response.json() == []

    async def test_list_sessions(self, client: AsyncClient):
        """Test listing multiple sessions."""
        # Create sessions
        for i in range(3):
            await client.post(
                "/api/sessions/",
                json={
                    "name": f"Session {i}",
                    "personas": [
                        {"persona_name": "test", "provider": "anthropic", "model": "claude-sonnet-4-20250514"},
                    ],
                },
            )

        response = await client.get("/api/sessions/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

    async def test_list_sessions_with_limit(self, client: AsyncClient):
        """Test listing sessions with limit."""
        for i in range(5):
            await client.post(
                "/api/sessions/",
                json={
                    "name": f"Session {i}",
                    "personas": [
                        {"persona_name": "test", "provider": "anthropic", "model": "claude-sonnet-4-20250514"},
                    ],
                },
            )

        response = await client.get("/api/sessions/?limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    async def test_list_sessions_with_offset(self, client: AsyncClient):
        """Test listing sessions with offset."""
        for i in range(5):
            await client.post(
                "/api/sessions/",
                json={
                    "name": f"Session {i}",
                    "personas": [
                        {"persona_name": "test", "provider": "anthropic", "model": "claude-sonnet-4-20250514"},
                    ],
                },
            )

        response = await client.get("/api/sessions/?offset=3")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    async def test_list_sessions_filter_by_status(self, client: AsyncClient):
        """Test filtering sessions by status."""
        # Create active session
        await client.post(
            "/api/sessions/",
            json={
                "name": "Active Session",
                "personas": [
                    {"persona_name": "test", "provider": "anthropic", "model": "claude-sonnet-4-20250514"},
                ],
            },
        )

        response = await client.get("/api/sessions/?status=active")
        assert response.status_code == 200
        data = response.json()
        assert all(s["status"] == "active" for s in data)


class TestGetSession:
    """Tests for GET /api/sessions/{session_id}"""

    async def test_get_session(self, client: AsyncClient):
        """Test getting a specific session."""
        # Create session
        create_response = await client.post(
            "/api/sessions/",
            json={
                "name": "Get Test",
                "personas": [
                    {"persona_name": "test", "provider": "anthropic", "model": "claude-sonnet-4-20250514"},
                ],
            },
        )
        session_id = create_response.json()["id"]

        response = await client.get(f"/api/sessions/{session_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == session_id
        assert data["name"] == "Get Test"

    async def test_get_session_not_found(self, client: AsyncClient):
        """Test getting non-existent session."""
        response = await client.get("/api/sessions/99999")
        assert response.status_code == 404

    async def test_get_session_includes_personas(self, client: AsyncClient):
        """Test that get session includes personas."""
        create_response = await client.post(
            "/api/sessions/",
            json={
                "name": "With Personas",
                "personas": [
                    {"persona_name": "einstein", "provider": "anthropic", "model": "claude-sonnet-4-20250514"},
                    {"persona_name": "feynman", "provider": "anthropic", "model": "claude-sonnet-4-20250514"},
                ],
            },
        )
        session_id = create_response.json()["id"]

        response = await client.get(f"/api/sessions/{session_id}")
        assert response.status_code == 200
        data = response.json()
        assert len(data["personas"]) == 2


class TestUpdateSession:
    """Tests for PATCH /api/sessions/{session_id}"""

    async def test_update_session_name(self, client: AsyncClient):
        """Test updating session name."""
        create_response = await client.post(
            "/api/sessions/",
            json={
                "name": "Original Name",
                "personas": [
                    {"persona_name": "test", "provider": "anthropic", "model": "claude-sonnet-4-20250514"},
                ],
            },
        )
        session_id = create_response.json()["id"]

        response = await client.patch(
            f"/api/sessions/{session_id}",
            json={"name": "Updated Name"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"

    async def test_update_session_phase(self, client: AsyncClient):
        """Test updating session phase."""
        create_response = await client.post(
            "/api/sessions/",
            json={
                "name": "Phase Test",
                "personas": [
                    {"persona_name": "test", "provider": "anthropic", "model": "claude-sonnet-4-20250514"},
                ],
            },
        )
        session_id = create_response.json()["id"]

        response = await client.patch(
            f"/api/sessions/{session_id}",
            json={"phase": "ideation"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["phase"] == "ideation"

    async def test_update_session_status(self, client: AsyncClient):
        """Test updating session status."""
        create_response = await client.post(
            "/api/sessions/",
            json={
                "name": "Status Test",
                "personas": [
                    {"persona_name": "test", "provider": "anthropic", "model": "claude-sonnet-4-20250514"},
                ],
            },
        )
        session_id = create_response.json()["id"]

        response = await client.patch(
            f"/api/sessions/{session_id}",
            json={"status": "paused"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "paused"

    async def test_update_session_increments_version(self, client: AsyncClient):
        """Test that updates increment version."""
        create_response = await client.post(
            "/api/sessions/",
            json={
                "name": "Version Test",
                "personas": [
                    {"persona_name": "test", "provider": "anthropic", "model": "claude-sonnet-4-20250514"},
                ],
            },
        )
        session_id = create_response.json()["id"]
        original_version = create_response.json()["version"]

        response = await client.patch(
            f"/api/sessions/{session_id}",
            json={"name": "Updated"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == original_version + 1

    async def test_update_session_not_found(self, client: AsyncClient):
        """Test updating non-existent session."""
        response = await client.patch(
            "/api/sessions/99999",
            json={"name": "New Name"},
        )
        assert response.status_code == 404


class TestDeleteSession:
    """Tests for DELETE /api/sessions/{session_id}"""

    async def test_delete_session(self, client: AsyncClient):
        """Test deleting a session."""
        create_response = await client.post(
            "/api/sessions/",
            json={
                "name": "To Delete",
                "personas": [
                    {"persona_name": "test", "provider": "anthropic", "model": "claude-sonnet-4-20250514"},
                ],
            },
        )
        session_id = create_response.json()["id"]

        response = await client.delete(f"/api/sessions/{session_id}")
        assert response.status_code == 200

        # Verify deleted
        get_response = await client.get(f"/api/sessions/{session_id}")
        assert get_response.status_code == 404

    async def test_delete_session_not_found(self, client: AsyncClient):
        """Test deleting non-existent session."""
        response = await client.delete("/api/sessions/99999")
        assert response.status_code == 404


class TestSessionMessages:
    """Tests for GET /api/sessions/{session_id}/messages"""

    async def test_get_messages_empty(self, client: AsyncClient):
        """Test getting messages from session with none."""
        create_response = await client.post(
            "/api/sessions/",
            json={
                "name": "Empty Messages",
                "personas": [
                    {"persona_name": "test", "provider": "anthropic", "model": "claude-sonnet-4-20250514"},
                ],
            },
        )
        session_id = create_response.json()["id"]

        response = await client.get(f"/api/sessions/{session_id}/messages")
        assert response.status_code == 200
        assert response.json() == []


class TestSessionTokenUsage:
    """Tests for GET /api/sessions/{session_id}/token-usage"""

    async def test_get_token_usage_empty(self, client: AsyncClient):
        """Test getting token usage from new session."""
        create_response = await client.post(
            "/api/sessions/",
            json={
                "name": "Token Test",
                "personas": [
                    {"persona_name": "test", "provider": "anthropic", "model": "claude-sonnet-4-20250514"},
                ],
            },
        )
        session_id = create_response.json()["id"]

        response = await client.get(f"/api/sessions/{session_id}/token-usage")
        assert response.status_code == 200
        data = response.json()
        assert data["total"]["input_tokens"] == 0
        assert data["total"]["output_tokens"] == 0
        assert data["total"]["cost"] == 0

    async def test_get_token_usage_with_data(self, client: AsyncClient):
        """Test getting token usage with actual data."""
        from src.db.models import TokenUsage

        # Create a session first
        create_response = await client.post(
            "/api/sessions/",
            json={
                "name": "Token Usage Test",
                "personas": [
                    {"persona_name": "einstein", "provider": "anthropic", "model": "claude-sonnet-4-20250514"},
                    {"persona_name": "feynman", "provider": "openai", "model": "gpt-4"},
                ],
            },
        )
        session_id = create_response.json()["id"]

        # Get token usage (will be empty but tests the endpoint)
        response = await client.get(f"/api/sessions/{session_id}/token-usage")
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id
        assert "by_persona" in data
        assert "by_provider" in data


class TestTokenUsageAggregation:
    """Tests for token usage aggregation."""

    async def test_token_usage_aggregation(self, client: AsyncClient, sample_session, db_session):
        """Test token usage aggregation with data."""
        from src.db.models import TokenUsage

        # Add token usage records
        usage1 = TokenUsage(
            session_id=sample_session.id,
            persona_name="einstein",
            provider="anthropic",
            model="claude-sonnet-4-20250514",
            input_tokens=100,
            output_tokens=50,
            cost=0.001,
        )
        usage2 = TokenUsage(
            session_id=sample_session.id,
            persona_name="feynman",
            provider="openai",
            model="gpt-4",
            input_tokens=200,
            output_tokens=100,
            cost=0.002,
        )
        db_session.add(usage1)
        db_session.add(usage2)
        await db_session.commit()

        response = await client.get(f"/api/sessions/{sample_session.id}/token-usage")
        assert response.status_code == 200
        data = response.json()

        # Check totals
        assert data["total"]["input_tokens"] == 300
        assert data["total"]["output_tokens"] == 150
        assert data["by_persona"]["einstein"]["input_tokens"] == 100
        assert data["by_provider"]["openai"]["input_tokens"] == 200


class TestUpdateSessionAllFields:
    """Tests for updating all session fields."""

    async def test_update_session_problem_statement(self, client: AsyncClient):
        """Test updating session problem statement."""
        create_response = await client.post(
            "/api/sessions/",
            json={
                "name": "Problem Test",
                "personas": [
                    {"persona_name": "test", "provider": "anthropic", "model": "claude-sonnet-4-20250514"},
                ],
            },
        )
        session_id = create_response.json()["id"]

        response = await client.patch(
            f"/api/sessions/{session_id}",
            json={"problem_statement": "New problem statement"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["problem_statement"] == "New problem statement"

    async def test_update_session_turn_mode(self, client: AsyncClient):
        """Test updating session turn mode."""
        create_response = await client.post(
            "/api/sessions/",
            json={
                "name": "Turn Mode Test",
                "personas": [
                    {"persona_name": "test", "provider": "anthropic", "model": "claude-sonnet-4-20250514"},
                ],
            },
        )
        session_id = create_response.json()["id"]

        response = await client.patch(
            f"/api/sessions/{session_id}",
            json={"turn_mode": "parallel"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["turn_mode"] == "parallel"

    async def test_update_session_config(self, client: AsyncClient):
        """Test updating session config."""
        create_response = await client.post(
            "/api/sessions/",
            json={
                "name": "Config Test",
                "personas": [
                    {"persona_name": "test", "provider": "anthropic", "model": "claude-sonnet-4-20250514"},
                ],
            },
        )
        session_id = create_response.json()["id"]

        response = await client.patch(
            f"/api/sessions/{session_id}",
            json={"config": {"require_citations": True, "steelman_mode": True}},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["config"]["require_citations"] is True

    async def test_update_session_multiple_fields(self, client: AsyncClient):
        """Test updating multiple session fields at once."""
        create_response = await client.post(
            "/api/sessions/",
            json={
                "name": "Multi Update Test",
                "personas": [
                    {"persona_name": "test", "provider": "anthropic", "model": "claude-sonnet-4-20250514"},
                ],
            },
        )
        session_id = create_response.json()["id"]

        response = await client.patch(
            f"/api/sessions/{session_id}",
            json={
                "name": "Updated Name",
                "problem_statement": "Updated problem",
                "phase": "evaluation",
                "turn_mode": "free_form",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["problem_statement"] == "Updated problem"
        assert data["phase"] == "evaluation"
        assert data["turn_mode"] == "free_form"
