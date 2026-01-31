"""Analytics API routes."""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime

from ...db.database import get_db
from ...db.models import (
    Session, Message, TokenUsage, Vote, Insight,
    InsightType, VoteType, SessionPhase,
)
from ...providers.factory import get_available_providers, get_all_models

router = APIRouter()


class InsightResponse(BaseModel):
    """Insight response."""
    id: int
    insight_type: InsightType
    content: str
    personas_involved: List[str]
    importance: float
    phase: Optional[SessionPhase]
    created_at: datetime

    class Config:
        from_attributes = True


class VoteResponse(BaseModel):
    """Vote response."""
    id: int
    proposal: str
    proposal_id: Optional[str]
    persona_name: str
    vote: VoteType
    rank: Optional[int]
    reasoning: Optional[str]
    confidence: float
    created_at: datetime

    class Config:
        from_attributes = True


class ConsensusMetrics(BaseModel):
    """Consensus metrics for a session."""
    total_proposals: int
    proposals_with_consensus: int
    average_agreement: float
    most_contested: Optional[str]
    votes_by_type: dict


class ConversationMetrics(BaseModel):
    """Conversation metrics for a session."""
    total_messages: int
    messages_by_persona: dict
    messages_by_phase: dict
    average_message_length: float
    turn_count: int


@router.get("/providers")
async def get_providers():
    """Get available AI providers and their models."""
    providers = get_available_providers()
    models = get_all_models()

    return {
        "available_providers": [p.value for p in providers],
        "models": models,
    }


@router.get("/sessions/{session_id}/insights", response_model=List[InsightResponse])
async def get_session_insights(
    session_id: int,
    insight_type: Optional[InsightType] = None,
    min_importance: float = Query(0.0, ge=0.0, le=1.0),
    db: AsyncSession = Depends(get_db),
):
    """Get insights for a session."""
    query = select(Insight).where(
        Insight.session_id == session_id,
        Insight.importance >= min_importance,
    )

    if insight_type:
        query = query.where(Insight.insight_type == insight_type)

    query = query.order_by(Insight.importance.desc())

    result = await db.execute(query)
    insights = result.scalars().all()

    return [InsightResponse.model_validate(i) for i in insights]


@router.get("/sessions/{session_id}/votes", response_model=List[VoteResponse])
async def get_session_votes(
    session_id: int,
    proposal_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Get votes for a session."""
    query = select(Vote).where(Vote.session_id == session_id)

    if proposal_id:
        query = query.where(Vote.proposal_id == proposal_id)

    query = query.order_by(Vote.created_at)

    result = await db.execute(query)
    votes = result.scalars().all()

    return [VoteResponse.model_validate(v) for v in votes]


@router.get("/sessions/{session_id}/consensus", response_model=ConsensusMetrics)
async def get_consensus_metrics(
    session_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get consensus metrics for a session."""
    result = await db.execute(
        select(Vote).where(Vote.session_id == session_id)
    )
    votes = result.scalars().all()

    if not votes:
        return ConsensusMetrics(
            total_proposals=0,
            proposals_with_consensus=0,
            average_agreement=0.0,
            most_contested=None,
            votes_by_type={},
        )

    # Group by proposal
    proposals = {}
    for vote in votes:
        key = vote.proposal_id or vote.proposal[:50]
        if key not in proposals:
            proposals[key] = {"agree": 0, "disagree": 0, "abstain": 0, "text": vote.proposal}
        proposals[key][vote.vote.value] += 1

    # Calculate metrics
    total_proposals = len(proposals)
    proposals_with_consensus = 0
    most_contested = None
    max_disagreement = 0

    for key, counts in proposals.items():
        total_votes = counts["agree"] + counts["disagree"] + counts["abstain"]
        if total_votes > 0:
            agreement_ratio = counts["agree"] / total_votes
            if agreement_ratio >= 0.7:  # 70% threshold for consensus
                proposals_with_consensus += 1
            disagreement = counts["disagree"] / total_votes
            if disagreement > max_disagreement:
                max_disagreement = disagreement
                most_contested = counts["text"]

    # Vote type counts
    votes_by_type = {
        "agree": sum(1 for v in votes if v.vote == VoteType.AGREE),
        "disagree": sum(1 for v in votes if v.vote == VoteType.DISAGREE),
        "abstain": sum(1 for v in votes if v.vote == VoteType.ABSTAIN),
    }

    total_votes = sum(votes_by_type.values())
    average_agreement = votes_by_type["agree"] / total_votes if total_votes > 0 else 0.0

    return ConsensusMetrics(
        total_proposals=total_proposals,
        proposals_with_consensus=proposals_with_consensus,
        average_agreement=average_agreement,
        most_contested=most_contested,
        votes_by_type=votes_by_type,
    )


@router.get("/sessions/{session_id}/conversation-metrics", response_model=ConversationMetrics)
async def get_conversation_metrics(
    session_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get conversation metrics for a session."""
    result = await db.execute(
        select(Message).where(Message.session_id == session_id)
    )
    messages = result.scalars().all()

    if not messages:
        return ConversationMetrics(
            total_messages=0,
            messages_by_persona={},
            messages_by_phase={},
            average_message_length=0.0,
            turn_count=0,
        )

    # Calculate metrics
    messages_by_persona = {}
    messages_by_phase = {}
    total_length = 0
    max_turn = 0

    for msg in messages:
        # By persona
        persona = msg.persona_name or "user"
        if persona not in messages_by_persona:
            messages_by_persona[persona] = 0
        messages_by_persona[persona] += 1

        # By phase
        phase = msg.phase.value if msg.phase else "unknown"
        if phase not in messages_by_phase:
            messages_by_phase[phase] = 0
        messages_by_phase[phase] += 1

        total_length += len(msg.content)
        max_turn = max(max_turn, msg.turn_number)

    return ConversationMetrics(
        total_messages=len(messages),
        messages_by_persona=messages_by_persona,
        messages_by_phase=messages_by_phase,
        average_message_length=total_length / len(messages),
        turn_count=max_turn,
    )


@router.get("/sessions/{session_id}/bias-check")
async def check_for_bias(
    session_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Check for potential groupthink or bias in the conversation."""
    # Get insights with bias warnings
    result = await db.execute(
        select(Insight).where(
            Insight.session_id == session_id,
            Insight.insight_type == InsightType.BIAS_WARNING,
        )
    )
    bias_insights = result.scalars().all()

    # Get vote distribution
    vote_result = await db.execute(
        select(Vote).where(Vote.session_id == session_id)
    )
    votes = vote_result.scalars().all()

    # Analyze for groupthink indicators
    groupthink_score = 0.0
    indicators = []

    if votes:
        # High agreement rate might indicate groupthink
        agree_count = sum(1 for v in votes if v.vote == VoteType.AGREE)
        agreement_rate = agree_count / len(votes)
        if agreement_rate > 0.9:
            groupthink_score += 0.3
            indicators.append("Very high agreement rate (>90%)")
        elif agreement_rate > 0.8:
            groupthink_score += 0.15
            indicators.append("High agreement rate (>80%)")

        # Low abstention might indicate pressure to conform
        abstain_count = sum(1 for v in votes if v.vote == VoteType.ABSTAIN)
        if abstain_count == 0 and len(votes) > 5:
            groupthink_score += 0.1
            indicators.append("No abstentions in voting")

    # Existing bias insights
    if bias_insights:
        groupthink_score += len(bias_insights) * 0.1
        for insight in bias_insights:
            indicators.append(insight.content[:100])

    return {
        "session_id": session_id,
        "groupthink_risk_score": min(groupthink_score, 1.0),
        "risk_level": "high" if groupthink_score > 0.6 else "medium" if groupthink_score > 0.3 else "low",
        "indicators": indicators,
        "recommendations": [
            "Consider adding a devil's advocate persona",
            "Encourage explicit disagreement",
            "Ask personas to steelman opposing views",
        ] if groupthink_score > 0.3 else [],
    }


@router.get("/sessions/{session_id}/scope-check")
async def check_scope_creep(
    session_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Check for scope creep in the conversation."""
    # Get scope creep insights
    result = await db.execute(
        select(Insight).where(
            Insight.session_id == session_id,
            Insight.insight_type == InsightType.SCOPE_CREEP,
        )
    )
    scope_insights = result.scalars().all()

    # Get session for original problem statement
    session_result = await db.execute(
        select(Session).where(Session.id == session_id)
    )
    session = session_result.scalar_one_or_none()

    scope_creep_score = len(scope_insights) * 0.2

    return {
        "session_id": session_id,
        "scope_creep_score": min(scope_creep_score, 1.0),
        "risk_level": "high" if scope_creep_score > 0.6 else "medium" if scope_creep_score > 0.3 else "low",
        "original_problem": session.problem_statement if session else None,
        "scope_creep_instances": [
            {"content": i.content, "importance": i.importance}
            for i in scope_insights
        ],
        "recommendations": [
            "Revisit the original problem statement",
            "Create sub-problems for related topics",
            "Table tangential discussions for future sessions",
        ] if scope_creep_score > 0.3 else [],
    }
