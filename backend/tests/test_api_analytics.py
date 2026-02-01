"""Tests for analytics API routes."""

import pytest
from httpx import AsyncClient
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime
from src.db.models import InsightType, VoteType, SessionPhase


class TestGetProviders:
    """Tests for GET /api/analytics/providers"""

    async def test_get_providers(self, client: AsyncClient):
        """Test getting available providers."""
        response = await client.get("/api/analytics/providers")
        assert response.status_code == 200
        data = response.json()
        assert "available_providers" in data
        assert "models" in data


class TestGetSessionInsights:
    """Tests for GET /api/analytics/sessions/{session_id}/insights"""

    async def test_get_insights_empty(self, client: AsyncClient, sample_session):
        """Test getting insights when none exist."""
        response = await client.get(f"/api/analytics/sessions/{sample_session.id}/insights")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_get_insights_with_min_importance(self, client: AsyncClient, sample_session):
        """Test filtering insights by minimum importance."""
        response = await client.get(
            f"/api/analytics/sessions/{sample_session.id}/insights",
            params={"min_importance": 0.5}
        )
        assert response.status_code == 200


class TestGetSessionVotes:
    """Tests for GET /api/analytics/sessions/{session_id}/votes"""

    async def test_get_votes_empty(self, client: AsyncClient, sample_session):
        """Test getting votes when none exist."""
        response = await client.get(f"/api/analytics/sessions/{sample_session.id}/votes")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestGetConsensusMetrics:
    """Tests for GET /api/analytics/sessions/{session_id}/consensus"""

    async def test_get_consensus_empty(self, client: AsyncClient, sample_session):
        """Test getting consensus metrics when no votes exist."""
        response = await client.get(f"/api/analytics/sessions/{sample_session.id}/consensus")
        assert response.status_code == 200
        data = response.json()
        assert data["total_proposals"] == 0
        assert data["proposals_with_consensus"] == 0
        assert data["average_agreement"] == 0.0


class TestGetConversationMetrics:
    """Tests for GET /api/analytics/sessions/{session_id}/conversation-metrics"""

    async def test_get_conversation_metrics_empty(self, client: AsyncClient, sample_session):
        """Test getting conversation metrics when no messages exist."""
        response = await client.get(f"/api/analytics/sessions/{sample_session.id}/conversation-metrics")
        assert response.status_code == 200
        data = response.json()
        assert data["total_messages"] == 0
        assert data["messages_by_persona"] == {}
        assert data["turn_count"] == 0

    async def test_get_conversation_metrics_with_messages(self, client: AsyncClient, sample_session, sample_messages):
        """Test getting conversation metrics with messages."""
        response = await client.get(f"/api/analytics/sessions/{sample_session.id}/conversation-metrics")
        assert response.status_code == 200
        data = response.json()
        assert data["total_messages"] >= 1


class TestBiasCheck:
    """Tests for GET /api/analytics/sessions/{session_id}/bias-check"""

    async def test_bias_check_low_risk(self, client: AsyncClient, sample_session):
        """Test bias check with low risk."""
        response = await client.get(f"/api/analytics/sessions/{sample_session.id}/bias-check")
        assert response.status_code == 200
        data = response.json()
        assert "groupthink_risk_score" in data
        assert "risk_level" in data
        assert "indicators" in data
        assert "recommendations" in data


class TestScopeCheck:
    """Tests for GET /api/analytics/sessions/{session_id}/scope-check"""

    async def test_scope_check(self, client: AsyncClient, sample_session):
        """Test scope check."""
        response = await client.get(f"/api/analytics/sessions/{sample_session.id}/scope-check")
        assert response.status_code == 200
        data = response.json()
        assert "scope_creep_score" in data
        assert "risk_level" in data
        assert "recommendations" in data


class TestGetInsightsWithData:
    """Tests for insights endpoint with actual data."""

    async def test_get_insights_with_data(self, client: AsyncClient, sample_session, db_session):
        """Test getting insights when they exist."""
        from src.db.models import Insight

        # Create test insight
        insight = Insight(
            session_id=sample_session.id,
            insight_type=InsightType.KEY_POINT,
            content="Important test insight",
            personas_involved=["einstein", "feynman"],
            importance=0.8,
            phase=SessionPhase.DISCOVERY,
        )
        db_session.add(insight)
        await db_session.commit()

        response = await client.get(f"/api/analytics/sessions/{sample_session.id}/insights")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(i["content"] == "Important test insight" for i in data)

    async def test_get_insights_filtered_by_type(self, client: AsyncClient, sample_session, db_session):
        """Test filtering insights by type."""
        from src.db.models import Insight

        # Create insights of different types
        insight1 = Insight(
            session_id=sample_session.id,
            insight_type=InsightType.KEY_POINT,
            content="Key point insight",
            personas_involved=["einstein"],
            importance=0.7,
        )
        insight2 = Insight(
            session_id=sample_session.id,
            insight_type=InsightType.DISAGREEMENT,
            content="Disagreement insight",
            personas_involved=["einstein", "feynman"],
            importance=0.9,
        )
        db_session.add(insight1)
        db_session.add(insight2)
        await db_session.commit()

        response = await client.get(
            f"/api/analytics/sessions/{sample_session.id}/insights",
            params={"insight_type": InsightType.KEY_POINT.value}
        )
        assert response.status_code == 200
        data = response.json()
        # All returned insights should be KEY_POINT type
        for insight in data:
            assert insight["insight_type"] == InsightType.KEY_POINT.value


class TestGetVotesWithData:
    """Tests for votes endpoint with actual data."""

    async def test_get_votes_with_data(self, client: AsyncClient, sample_session, db_session):
        """Test getting votes when they exist."""
        from src.db.models import Vote

        vote = Vote(
            session_id=sample_session.id,
            proposal="Should we use microservices?",
            proposal_id="prop-001",
            persona_name="einstein",
            vote=VoteType.AGREE,
            reasoning="I believe this is the right approach",
            confidence=0.85,
        )
        db_session.add(vote)
        await db_session.commit()

        response = await client.get(f"/api/analytics/sessions/{sample_session.id}/votes")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    async def test_get_votes_filtered_by_proposal(self, client: AsyncClient, sample_session, db_session):
        """Test filtering votes by proposal ID."""
        from src.db.models import Vote

        vote1 = Vote(
            session_id=sample_session.id,
            proposal="Proposal 1",
            proposal_id="prop-001",
            persona_name="einstein",
            vote=VoteType.AGREE,
            confidence=0.8,
        )
        vote2 = Vote(
            session_id=sample_session.id,
            proposal="Proposal 2",
            proposal_id="prop-002",
            persona_name="feynman",
            vote=VoteType.DISAGREE,
            confidence=0.7,
        )
        db_session.add(vote1)
        db_session.add(vote2)
        await db_session.commit()

        response = await client.get(
            f"/api/analytics/sessions/{sample_session.id}/votes",
            params={"proposal_id": "prop-001"}
        )
        assert response.status_code == 200
        data = response.json()
        assert all(v["proposal_id"] == "prop-001" for v in data)


class TestConsensusMetricsWithData:
    """Tests for consensus metrics with actual vote data."""

    async def test_consensus_with_votes(self, client: AsyncClient, sample_session, db_session):
        """Test consensus metrics calculation with votes."""
        from src.db.models import Vote

        # Create votes that should show consensus
        votes = [
            Vote(session_id=sample_session.id, proposal="Use TDD?", proposal_id="p1",
                 persona_name="einstein", vote=VoteType.AGREE, confidence=0.9),
            Vote(session_id=sample_session.id, proposal="Use TDD?", proposal_id="p1",
                 persona_name="feynman", vote=VoteType.AGREE, confidence=0.8),
            Vote(session_id=sample_session.id, proposal="Use TDD?", proposal_id="p1",
                 persona_name="curie", vote=VoteType.AGREE, confidence=0.85),
        ]
        for vote in votes:
            db_session.add(vote)
        await db_session.commit()

        response = await client.get(f"/api/analytics/sessions/{sample_session.id}/consensus")
        assert response.status_code == 200
        data = response.json()
        assert data["total_proposals"] >= 1
        assert data["proposals_with_consensus"] >= 1  # 100% agreement
        assert data["average_agreement"] == 1.0  # All agree

    async def test_consensus_with_disagreement(self, client: AsyncClient, sample_session, db_session):
        """Test consensus metrics with mixed votes."""
        from src.db.models import Vote

        votes = [
            Vote(session_id=sample_session.id, proposal="Use microservices?", proposal_id="p2",
                 persona_name="einstein", vote=VoteType.DISAGREE, confidence=0.9),
            Vote(session_id=sample_session.id, proposal="Use microservices?", proposal_id="p2",
                 persona_name="feynman", vote=VoteType.DISAGREE, confidence=0.8),
            Vote(session_id=sample_session.id, proposal="Use microservices?", proposal_id="p2",
                 persona_name="curie", vote=VoteType.AGREE, confidence=0.7),
        ]
        for vote in votes:
            db_session.add(vote)
        await db_session.commit()

        response = await client.get(f"/api/analytics/sessions/{sample_session.id}/consensus")
        assert response.status_code == 200
        data = response.json()
        assert data["most_contested"] is not None  # Should detect contested proposal
        assert data["votes_by_type"]["disagree"] >= 2


class TestBiasCheckWithData:
    """Tests for bias check with actual data."""

    async def test_bias_check_high_agreement(self, client: AsyncClient, sample_session, db_session):
        """Test bias check detects high agreement rate."""
        from src.db.models import Vote

        # Create votes with >90% agreement
        for i, persona in enumerate(["einstein", "feynman", "curie", "darwin", "newton", "tesla"]):
            vote = Vote(
                session_id=sample_session.id,
                proposal="Everyone agrees",
                proposal_id=f"p{i}",
                persona_name=persona,
                vote=VoteType.AGREE,
                confidence=0.9,
            )
            db_session.add(vote)
        await db_session.commit()

        response = await client.get(f"/api/analytics/sessions/{sample_session.id}/bias-check")
        assert response.status_code == 200
        data = response.json()
        assert data["groupthink_risk_score"] > 0
        assert len(data["indicators"]) > 0

    async def test_bias_check_with_bias_insights(self, client: AsyncClient, sample_session, db_session):
        """Test bias check includes bias insights."""
        from src.db.models import Insight

        insight = Insight(
            session_id=sample_session.id,
            insight_type=InsightType.BIAS_WARNING,
            content="Potential confirmation bias detected",
            personas_involved=["einstein", "feynman"],
            importance=0.8,
        )
        db_session.add(insight)
        await db_session.commit()

        response = await client.get(f"/api/analytics/sessions/{sample_session.id}/bias-check")
        assert response.status_code == 200
        data = response.json()
        assert data["groupthink_risk_score"] > 0


class TestScopeCheckWithData:
    """Tests for scope check with actual data."""

    async def test_scope_check_with_insights(self, client: AsyncClient, sample_session, db_session):
        """Test scope check with scope creep insights."""
        from src.db.models import Insight

        insight = Insight(
            session_id=sample_session.id,
            insight_type=InsightType.SCOPE_CREEP,
            content="Discussion drifted to unrelated topic",
            personas_involved=["einstein"],
            importance=0.7,
        )
        db_session.add(insight)
        await db_session.commit()

        response = await client.get(f"/api/analytics/sessions/{sample_session.id}/scope-check")
        assert response.status_code == 200
        data = response.json()
        assert data["scope_creep_score"] > 0
        assert len(data["scope_creep_instances"]) > 0


class TestAnalyticsModels:
    """Tests for analytics Pydantic models."""

    def test_insight_response_model(self):
        """Test InsightResponse model."""
        from src.api.routes.analytics import InsightResponse
        data = {
            "id": 1,
            "insight_type": InsightType.KEY_POINT,
            "content": "Important finding",
            "personas_involved": ["einstein"],
            "importance": 0.8,
            "phase": SessionPhase.DISCOVERY,
            "created_at": datetime.now(),
        }
        response = InsightResponse(**data)
        assert response.id == 1
        assert response.importance == 0.8

    def test_vote_response_model(self):
        """Test VoteResponse model."""
        from src.api.routes.analytics import VoteResponse
        data = {
            "id": 1,
            "proposal": "Test proposal",
            "proposal_id": "abc123",
            "persona_name": "einstein",
            "vote": VoteType.AGREE,
            "rank": None,
            "reasoning": "I agree",
            "confidence": 0.9,
            "created_at": datetime.now(),
        }
        response = VoteResponse(**data)
        assert response.vote == VoteType.AGREE

    def test_consensus_metrics_model(self):
        """Test ConsensusMetrics model."""
        from src.api.routes.analytics import ConsensusMetrics
        data = {
            "total_proposals": 5,
            "proposals_with_consensus": 3,
            "average_agreement": 0.7,
            "most_contested": "Should we use TDD?",
            "votes_by_type": {"agree": 10, "disagree": 3, "abstain": 2},
        }
        metrics = ConsensusMetrics(**data)
        assert metrics.total_proposals == 5
        assert metrics.average_agreement == 0.7

    def test_conversation_metrics_model(self):
        """Test ConversationMetrics model."""
        from src.api.routes.analytics import ConversationMetrics
        data = {
            "total_messages": 50,
            "messages_by_persona": {"einstein": 20, "feynman": 15, "user": 15},
            "messages_by_phase": {"discovery": 20, "ideation": 30},
            "average_message_length": 150.5,
            "turn_count": 25,
        }
        metrics = ConversationMetrics(**data)
        assert metrics.total_messages == 50
        assert metrics.turn_count == 25
