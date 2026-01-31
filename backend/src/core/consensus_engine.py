"""Consensus engine for multi-agent voting and agreement tracking."""

import logging
import uuid
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from sqlalchemy import select

from ..db.database import AsyncSessionLocal
from ..db.models import Vote, VoteType, Insight, InsightType

logger = logging.getLogger(__name__)


@dataclass
class VoteResult:
    """Result of a single persona's vote."""
    persona_name: str
    vote: VoteType
    reasoning: Optional[str] = None
    confidence: float = 1.0
    rank: Optional[int] = None  # For ranked-choice voting


@dataclass
class ConsensusResult:
    """Aggregated consensus result."""
    proposal: str
    proposal_id: str
    votes: List[VoteResult]
    consensus_reached: bool
    agreement_score: float  # 0.0 to 1.0
    majority_vote: Optional[VoteType] = None
    dissenting_personas: List[str] = field(default_factory=list)
    summary: Optional[str] = None


class ConsensusMode(str, Enum):
    """Consensus determination modes."""
    MAJORITY = "majority"  # Simple majority wins
    SUPERMAJORITY = "supermajority"  # 2/3 required
    UNANIMOUS = "unanimous"  # All must agree
    RANKED_CHOICE = "ranked_choice"  # Ranked voting
    WEIGHTED = "weighted"  # Weighted by confidence


class ConsensusEngine:
    """
    Manages voting, consensus tracking, and agreement analysis.

    Supports multiple voting modes and provides metrics on
    group agreement and disagreement.
    """

    def __init__(
        self,
        session_id: int,
        personas: List[str],
        mode: ConsensusMode = ConsensusMode.MAJORITY,
        threshold: float = 0.5,  # Consensus threshold (0.5 = majority)
    ):
        self.session_id = session_id
        self.personas = personas
        self.mode = mode
        self.threshold = threshold

        # Track historical agreement
        self.agreement_history: List[float] = []

    async def collect_votes(
        self,
        proposal: str,
        personas: Dict[str, Any],
    ) -> List[VoteResult]:
        """
        Collect votes from all personas on a proposal.

        This generates AI responses asking each persona to vote.
        """
        from ..providers.base import ChatMessage

        proposal_id = str(uuid.uuid4())[:8]
        votes = []

        vote_prompt = f"""
You are being asked to vote on the following proposal:

"{proposal}"

Please respond with your vote and brief reasoning. Format your response as:

VOTE: [AGREE/DISAGREE/ABSTAIN]
CONFIDENCE: [0.0-1.0]
REASONING: [Your reasoning in 1-2 sentences]
"""

        for persona_name, persona_state in personas.items():
            try:
                provider = persona_state.provider
                sp = persona_state.session_persona
                persona = persona_state.persona

                # Generate vote response
                response = await provider.generate(
                    messages=[ChatMessage(role="user", content=vote_prompt)],
                    model=sp.model,
                    system=persona.get_system_prompt(),
                    temperature=0.3,  # Lower temperature for more consistent voting
                    max_tokens=200,
                )

                # Parse the response
                vote_result = self._parse_vote_response(
                    persona_name,
                    response.content,
                )
                votes.append(vote_result)

                # Save vote to database
                await self._save_vote(proposal, proposal_id, vote_result)

            except Exception as e:
                logger.error(f"Error collecting vote from {persona_name}: {e}")
                # Record abstention on error
                votes.append(VoteResult(
                    persona_name=persona_name,
                    vote=VoteType.ABSTAIN,
                    reasoning=f"Error: {str(e)}",
                    confidence=0.0,
                ))

        return votes

    def _parse_vote_response(self, persona_name: str, response: str) -> VoteResult:
        """Parse a vote response from an AI persona."""
        # Default values
        vote = VoteType.ABSTAIN
        confidence = 0.5
        reasoning = response

        # Try to parse structured response
        response_upper = response.upper()

        # Parse vote
        if "VOTE:" in response_upper:
            if "AGREE" in response_upper.split("VOTE:")[1].split("\n")[0]:
                vote = VoteType.AGREE
            elif "DISAGREE" in response_upper.split("VOTE:")[1].split("\n")[0]:
                vote = VoteType.DISAGREE
        else:
            # Fallback: look for keywords
            if "I AGREE" in response_upper or "YES" in response_upper[:50]:
                vote = VoteType.AGREE
            elif "I DISAGREE" in response_upper or "NO" in response_upper[:50]:
                vote = VoteType.DISAGREE

        # Parse confidence
        if "CONFIDENCE:" in response_upper:
            try:
                conf_str = response_upper.split("CONFIDENCE:")[1].split("\n")[0].strip()
                confidence = float(conf_str.replace(",", "."))
                confidence = max(0.0, min(1.0, confidence))
            except (ValueError, IndexError):
                pass

        # Parse reasoning
        if "REASONING:" in response_upper:
            try:
                reasoning = response.split("REASONING:")[1].strip()
            except IndexError:
                pass

        return VoteResult(
            persona_name=persona_name,
            vote=vote,
            reasoning=reasoning,
            confidence=confidence,
        )

    async def _save_vote(self, proposal: str, proposal_id: str, vote_result: VoteResult):
        """Save a vote to the database."""
        async with AsyncSessionLocal() as db:
            vote = Vote(
                session_id=self.session_id,
                proposal=proposal,
                proposal_id=proposal_id,
                persona_name=vote_result.persona_name,
                vote=vote_result.vote,
                reasoning=vote_result.reasoning,
                confidence=vote_result.confidence,
                rank=vote_result.rank,
            )
            db.add(vote)
            await db.commit()

    async def analyze_votes(
        self,
        proposal: str,
        votes: List[VoteResult],
    ) -> Dict[str, Any]:
        """Analyze votes and determine consensus."""
        if not votes:
            return {
                "proposal": proposal,
                "consensus_reached": False,
                "agreement_score": 0.0,
                "votes": [],
            }

        # Count votes
        agree_count = sum(1 for v in votes if v.vote == VoteType.AGREE)
        disagree_count = sum(1 for v in votes if v.vote == VoteType.DISAGREE)
        abstain_count = sum(1 for v in votes if v.vote == VoteType.ABSTAIN)
        total_votes = len(votes)
        voting_count = agree_count + disagree_count  # Exclude abstentions

        # Calculate agreement score
        if voting_count > 0:
            agreement_score = agree_count / voting_count
        else:
            agreement_score = 0.5  # No clear consensus if all abstain

        # Determine if consensus is reached based on mode
        consensus_reached = False
        if self.mode == ConsensusMode.MAJORITY:
            consensus_reached = agreement_score > 0.5 or (disagree_count / max(voting_count, 1)) > 0.5
        elif self.mode == ConsensusMode.SUPERMAJORITY:
            consensus_reached = agreement_score >= 0.67 or (disagree_count / max(voting_count, 1)) >= 0.67
        elif self.mode == ConsensusMode.UNANIMOUS:
            consensus_reached = agree_count == total_votes or disagree_count == total_votes
        elif self.mode == ConsensusMode.WEIGHTED:
            # Weight by confidence
            weighted_agree = sum(v.confidence for v in votes if v.vote == VoteType.AGREE)
            weighted_disagree = sum(v.confidence for v in votes if v.vote == VoteType.DISAGREE)
            total_weight = weighted_agree + weighted_disagree
            if total_weight > 0:
                agreement_score = weighted_agree / total_weight
            consensus_reached = agreement_score > self.threshold

        # Determine majority vote
        majority_vote = None
        if agree_count > disagree_count:
            majority_vote = VoteType.AGREE
        elif disagree_count > agree_count:
            majority_vote = VoteType.DISAGREE

        # Identify dissenters
        dissenting_personas = []
        if majority_vote:
            for v in votes:
                if v.vote != majority_vote and v.vote != VoteType.ABSTAIN:
                    dissenting_personas.append(v.persona_name)

        # Track agreement history
        self.agreement_history.append(agreement_score)

        # Create insight if significant disagreement
        if len(dissenting_personas) > 0 and not consensus_reached:
            await self._create_insight(
                InsightType.DISAGREEMENT,
                f"Disagreement on: {proposal[:100]}. Dissenters: {', '.join(dissenting_personas)}",
                dissenting_personas,
            )

        result = {
            "proposal": proposal,
            "consensus_reached": consensus_reached,
            "agreement_score": agreement_score,
            "majority_vote": majority_vote.value if majority_vote else None,
            "votes": {
                "agree": agree_count,
                "disagree": disagree_count,
                "abstain": abstain_count,
            },
            "dissenting_personas": dissenting_personas,
            "vote_details": [
                {
                    "persona": v.persona_name,
                    "vote": v.vote.value,
                    "confidence": v.confidence,
                    "reasoning": v.reasoning,
                }
                for v in votes
            ],
        }

        return result

    async def _create_insight(
        self,
        insight_type: InsightType,
        content: str,
        personas: List[str],
    ):
        """Create an insight in the database."""
        async with AsyncSessionLocal() as db:
            insight = Insight(
                session_id=self.session_id,
                insight_type=insight_type,
                content=content,
                personas_involved=personas,
                importance=0.7,
            )
            db.add(insight)
            await db.commit()

    def get_agreement_trend(self) -> Dict[str, Any]:
        """Get the trend of agreement over time."""
        if not self.agreement_history:
            return {"trend": "none", "average": 0.0, "values": []}

        average = sum(self.agreement_history) / len(self.agreement_history)

        # Determine trend
        if len(self.agreement_history) >= 3:
            recent = self.agreement_history[-3:]
            if all(recent[i] <= recent[i + 1] for i in range(len(recent) - 1)):
                trend = "increasing"
            elif all(recent[i] >= recent[i + 1] for i in range(len(recent) - 1)):
                trend = "decreasing"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"

        return {
            "trend": trend,
            "average": average,
            "values": self.agreement_history,
        }

    def reset(self):
        """Reset the consensus engine state."""
        self.agreement_history = []
