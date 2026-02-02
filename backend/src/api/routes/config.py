"""Configuration API routes for managing API keys and settings."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
import os

router = APIRouter()


class ApiKeyRequest(BaseModel):
    """Request to set an API key."""
    provider: str
    api_key: str


class ApiKeyResponse(BaseModel):
    """Response after setting API key."""
    status: str
    provider: str
    configured: bool


@router.post("/api-key", response_model=ApiKeyResponse)
async def set_api_key(request: ApiKeyRequest):
    """
    Set an API key for a provider.
    Writes to the .env file in the backend directory.
    """
    provider = request.provider.lower()

    if provider not in ["anthropic", "openai"]:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")

    env_var = f"{provider.upper()}_API_KEY"

    # Find the .env file
    env_path = Path(__file__).parent.parent.parent.parent / ".env"

    # Read existing content
    env_content = ""
    if env_path.exists():
        env_content = env_path.read_text()

    # Update or add the API key
    lines = env_content.split("\n")
    found = False
    new_lines = []

    for line in lines:
        if line.startswith(f"{env_var}="):
            new_lines.append(f"{env_var}={request.api_key}")
            found = True
        else:
            new_lines.append(line)

    if not found:
        new_lines.append(f"{env_var}={request.api_key}")

    # Write back
    env_path.write_text("\n".join(new_lines))

    # Also update the environment variable for current process
    os.environ[env_var] = request.api_key

    # Update settings
    from ...config import settings
    if provider == "anthropic":
        settings.anthropic_api_key = request.api_key
    elif provider == "openai":
        settings.openai_api_key = request.api_key

    # Clear provider cache so it picks up new key
    from ...providers.factory import _providers
    _providers.clear()

    return ApiKeyResponse(
        status="saved",
        provider=provider,
        configured=bool(request.api_key)
    )


@router.get("/providers")
async def get_provider_status():
    """Get status of all configured providers."""
    from ...providers.factory import get_available_providers, get_all_models

    available = get_available_providers()
    models = get_all_models()

    return {
        "available_providers": [p.value for p in available],
        "models": models,
    }


@router.get("/mcp/status")
async def get_mcp_status():
    """Get MCP server status and available tools."""
    from ..mcp.server import mcp_server

    try:
        tools = mcp_server.get_tools_schema()
        return {
            "status": "available",
            "tools_count": len(tools),
            "tools": [t["name"] for t in tools],
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }


@router.get("/mcp/test")
async def test_mcp_tool():
    """Test MCP by executing a simple tool (list_domains)."""
    from ..mcp.server import mcp_server

    try:
        result = await mcp_server.execute_tool("list_domains", {})
        return {
            "status": "success",
            "test_result": result,
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }


class SubmitResponseRequest(BaseModel):
    """Request to submit a persona response via MCP/Claude Code."""
    session_id: int
    persona_name: str
    content: str
    round_number: int = 1  # Which discussion round (1=initial, 2+=discussion)


class SubmitVoteRequest(BaseModel):
    """Request to submit a vote response via MCP/Claude Code."""
    session_id: int
    proposal_id: str
    persona_name: str
    vote: str  # "agree", "disagree", "abstain" OR for poll mode: option name
    confidence: float = 1.0
    reasoning: str = ""
    rank: int = 1  # For ranked choice voting (1 = first choice, 2 = second, etc.)


class OrchestratorStatusRequest(BaseModel):
    """Request to broadcast orchestrator status to the frontend."""
    session_id: int
    status: str  # "checking", "generating", "submitting", "waiting", "complete", "error"
    persona_name: Optional[str] = None
    round_number: Optional[int] = None
    details: Optional[str] = None
    # Token usage from Claude Code
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    cache_read_tokens: Optional[int] = None
    cache_creation_tokens: Optional[int] = None


@router.post("/mcp/orchestrator-status")
async def broadcast_orchestrator_status(request: OrchestratorStatusRequest):
    """
    Broadcast an orchestrator status update to the frontend.
    Called by Claude Code to keep the UI informed during response generation.
    """
    from ..websocket.chat_handler import send_orchestrator_status

    try:
        await send_orchestrator_status(
            session_id=request.session_id,
            status=request.status,
            persona_name=request.persona_name,
            round_number=request.round_number,
            details=request.details,
            input_tokens=request.input_tokens,
            output_tokens=request.output_tokens,
            cache_read_tokens=request.cache_read_tokens,
            cache_creation_tokens=request.cache_creation_tokens,
        )
        return {"status": "broadcasted"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.post("/mcp/submit-response")
async def submit_mcp_response(request: SubmitResponseRequest):
    """Submit a response generated by Claude Code for a persona."""
    from ..mcp.server import mcp_server
    from ...db.database import AsyncSessionLocal
    from ...db.models import Poll, PollOption, PollPhase, SessionPersona
    from ..websocket.chat_handler import manager as ws_manager, WSEvent, WSEventType
    from sqlalchemy import select
    import re

    # Normalize persona name to internal format (lowercase with hyphens)
    # "AG Lafley" -> "ag-lafley", "Akio Morita" -> "akio-morita"
    normalized_name = re.sub(r'[^a-zA-Z0-9]+', '-', request.persona_name.lower()).strip('-')
    request.persona_name = normalized_name

    try:
        # Check if there's an active poll for this session
        async with AsyncSessionLocal() as db:
            from ...db.models import PollVote

            # Check for any active poll (synthesis or voting)
            poll_result = await db.execute(
                select(Poll)
                .where(Poll.session_id == request.session_id)
                .where(Poll.phase.in_([PollPhase.SYNTHESIS, PollPhase.VOTE_ROUND_1, PollPhase.VOTE_ROUND_2]))
            )
            active_poll = poll_result.scalar_one_or_none()

            if active_poll and active_poll.phase == PollPhase.VOTE_ROUND_1:
                # Handle vote round 1 - parse rankings
                content = request.content
                rankings = []

                # Parse RANKINGS from content
                import re
                lines = content.split('\n')
                in_rankings = False
                for line in lines:
                    line = line.strip()
                    if line.upper().startswith('RANKINGS:'):
                        in_rankings = True
                        continue
                    if in_rankings and line:
                        # Parse "1. 61 - reason" or "1. [61] - reason" format
                        match = re.match(r'^(\d+)[\.\)]\s*\[?(\d+)\]?\s*[-–]?\s*(.*)$', line)
                        if match:
                            rank = int(match.group(1))
                            option_id = int(match.group(2))
                            rankings.append({"rank": rank, "option_id": option_id})

                # Save votes
                for ranking in rankings:
                    vote = PollVote(
                        poll_id=active_poll.id,
                        option_id=ranking["option_id"],
                        persona_name=request.persona_name,
                        vote_round=1,
                        rank=ranking["rank"],
                    )
                    db.add(vote)

                await db.commit()

                # Check if all personas have voted
                personas_result = await db.execute(
                    select(SessionPersona).where(SessionPersona.session_id == request.session_id)
                )
                all_personas = {sp.persona_name for sp in personas_result.scalars().all()}

                votes_result = await db.execute(
                    select(PollVote)
                    .where(PollVote.poll_id == active_poll.id)
                    .where(PollVote.vote_round == 1)
                )
                voted = {v.persona_name for v in votes_result.scalars().all()}
                all_voted = voted >= all_personas

                response = {
                    "status": "poll_vote_submitted",
                    "poll_id": active_poll.poll_id,
                    "persona_name": request.persona_name,
                    "rankings_count": len(rankings),
                    "all_voted": all_voted,
                }

                # Broadcast live vote update for election-day excitement!
                await ws_manager.broadcast(request.session_id, WSEvent(
                    type=WSEventType.SYSTEM_MESSAGE,
                    data={
                        "type": "poll_vote_received",
                        "poll_id": active_poll.poll_id,
                        "persona_name": request.persona_name,
                        "vote_round": 1,
                        "voted_count": len(voted) + 1,
                        "total_personas": len(all_personas),
                    },
                ))

                if all_voted:
                    # Process round 1 and advance to round 2
                    top_5 = await _process_round_1_votes(db, active_poll)
                    active_poll.phase = PollPhase.VOTE_ROUND_2
                    await db.commit()

                    response["phase_advanced"] = True
                    response["next_phase"] = "vote_round_2"
                    response["top_5_options"] = top_5

                    await ws_manager.broadcast(request.session_id, WSEvent(
                        type=WSEventType.SYSTEM_MESSAGE,
                        data={
                            "type": "poll_phase_change",
                            "poll_id": active_poll.poll_id,
                            "new_phase": "vote_round_2",
                            "top_5_options": top_5,
                        },
                    ))

                return response

            elif active_poll and active_poll.phase == PollPhase.VOTE_ROUND_2:
                # Handle vote round 2 - parse OPTION votes
                content = request.content
                votes_parsed = []

                # Parse "OPTION [id]: AGREE/DISAGREE/ABSTAIN (confidence: X.X) - reason"
                import re
                lines = content.split('\n')
                for line in lines:
                    line = line.strip()
                    match = re.match(
                        r'^OPTION\s*\[?(\d+)\]?\s*:\s*(AGREE|DISAGREE|ABSTAIN)\s*\(?\s*confidence\s*[:=]?\s*([\d.]+)\s*\)?\s*[-–]?\s*(.*)$',
                        line,
                        re.IGNORECASE
                    )
                    if match:
                        option_id = int(match.group(1))
                        vote_value = match.group(2).lower()
                        confidence = float(match.group(3))
                        reasoning = match.group(4).strip()
                        votes_parsed.append({
                            "option_id": option_id,
                            "vote": vote_value,
                            "confidence": confidence,
                            "reasoning": reasoning,
                        })

                # Save votes
                for vote_data in votes_parsed:
                    vote = PollVote(
                        poll_id=active_poll.id,
                        option_id=vote_data["option_id"],
                        persona_name=request.persona_name,
                        vote_round=2,
                        vote_value=vote_data["vote"],
                        confidence=vote_data["confidence"],
                        reasoning=vote_data["reasoning"],
                    )
                    db.add(vote)

                await db.commit()

                # Check if all personas have voted
                personas_result = await db.execute(
                    select(SessionPersona).where(SessionPersona.session_id == request.session_id)
                )
                all_personas = {sp.persona_name for sp in personas_result.scalars().all()}

                votes_result = await db.execute(
                    select(PollVote)
                    .where(PollVote.poll_id == active_poll.id)
                    .where(PollVote.vote_round == 2)
                )
                voted = {v.persona_name for v in votes_result.scalars().all()}
                all_voted = voted >= all_personas

                response = {
                    "status": "poll_vote_submitted",
                    "poll_id": active_poll.poll_id,
                    "persona_name": request.persona_name,
                    "votes_count": len(votes_parsed),
                    "all_voted": all_voted,
                }

                # Broadcast live vote update for election-day excitement!
                await ws_manager.broadcast(request.session_id, WSEvent(
                    type=WSEventType.SYSTEM_MESSAGE,
                    data={
                        "type": "poll_vote_received",
                        "poll_id": active_poll.poll_id,
                        "persona_name": request.persona_name,
                        "vote_round": 2,
                        "voted_count": len(voted),
                        "total_personas": len(all_personas),
                    },
                ))

                if all_voted:
                    # Process round 2 and complete the poll!
                    final_results = await _process_round_2_votes(db, active_poll)
                    active_poll.phase = PollPhase.COMPLETED
                    from datetime import datetime
                    active_poll.completed_at = datetime.utcnow()
                    await db.commit()

                    response["phase_advanced"] = True
                    response["next_phase"] = "completed"
                    response["final_results"] = final_results

                    # Broadcast final results with excitement!
                    await ws_manager.broadcast(request.session_id, WSEvent(
                        type=WSEventType.VOTE_COMPLETE,
                        data={
                            "type": "poll_complete",
                            "poll_id": active_poll.poll_id,
                            "question": active_poll.question,
                            "poll_results": final_results,
                        },
                    ))

                return response

            elif active_poll and active_poll.phase == PollPhase.SYNTHESIS:
                # This is a poll synthesis response - extract options
                content = request.content
                framing = ""
                options = []

                # Parse FRAMING and OPTIONS from content
                lines = content.split('\n')
                in_options = False
                for line in lines:
                    line = line.strip()
                    if line.upper().startswith('FRAMING:'):
                        framing = line[8:].strip()
                    elif line.upper().startswith('OPTIONS:'):
                        in_options = True
                    elif in_options and line:
                        # Remove numbering like "1.", "2.", etc.
                        import re
                        clean = re.sub(r'^\d+[\.\)]\s*', '', line)
                        if clean:
                            options.append(clean)

                # Save options to poll
                for option_text in options:
                    option = PollOption(
                        poll_id=active_poll.id,
                        option_text=option_text,
                        proposed_by=request.persona_name,
                    )
                    db.add(option)

                await db.commit()

                # Check if all personas have submitted
                personas_result = await db.execute(
                    select(SessionPersona).where(SessionPersona.session_id == request.session_id)
                )
                all_personas = {sp.persona_name for sp in personas_result.scalars().all()}

                options_result = await db.execute(
                    select(PollOption).where(PollOption.poll_id == active_poll.id)
                )
                all_options = list(options_result.scalars().all())
                submitted_personas = {opt.proposed_by for opt in all_options}

                all_submitted = submitted_personas >= all_personas

                # Broadcast synthesis received
                await ws_manager.broadcast(request.session_id, WSEvent(
                    type=WSEventType.SYSTEM_MESSAGE,
                    data={
                        "type": "poll_synthesis",
                        "poll_id": active_poll.poll_id,
                        "persona_name": request.persona_name,
                        "framing": framing,
                        "options_count": len(options),
                        "all_submitted": all_submitted,
                    },
                ))

                response = {
                    "status": "poll_synthesis_submitted",
                    "poll_id": active_poll.poll_id,
                    "persona_name": request.persona_name,
                    "options_added": len(options),
                    "all_submitted": all_submitted,
                }

                # If all submitted, advance to vote round 1
                if all_submitted:
                    active_poll.phase = PollPhase.VOTE_ROUND_1
                    await db.commit()

                    # Get deduplicated options
                    unique_options = _deduplicate_options(all_options)

                    response["phase_advanced"] = True
                    response["next_phase"] = "vote_round_1"
                    response["options_for_voting"] = [
                        {"id": opt.id, "text": opt.option_text}
                        for opt in unique_options
                    ]

                    await ws_manager.broadcast(request.session_id, WSEvent(
                        type=WSEventType.SYSTEM_MESSAGE,
                        data={
                            "type": "poll_phase_change",
                            "poll_id": active_poll.poll_id,
                            "new_phase": "vote_round_1",
                            "options": response["options_for_voting"],
                        },
                    ))

                return response

        # Normal response (not poll mode)
        result = await mcp_server.execute_tool("submit_persona_response", {
            "session_id": request.session_id,
            "persona_name": request.persona_name,
            "content": request.content,
            "round_number": request.round_number,
        })
        return result
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }


@router.post("/mcp/submit-vote")
async def submit_mcp_vote(request: SubmitVoteRequest):
    """Submit a vote generated by Claude Code for a persona."""
    from ...db.database import AsyncSessionLocal
    from ...db.models import Vote, VoteType, PendingVoteRequest
    from ..websocket.chat_handler import manager as ws_manager, WSEvent, WSEventType
    from sqlalchemy import select

    try:
        # Map vote string to enum
        vote_map = {
            "agree": VoteType.AGREE,
            "disagree": VoteType.DISAGREE,
            "abstain": VoteType.ABSTAIN,
        }
        vote_type = vote_map.get(request.vote.lower(), VoteType.ABSTAIN)

        async with AsyncSessionLocal() as db:
            # Get the pending vote request
            pending_result = await db.execute(
                select(PendingVoteRequest)
                .where(PendingVoteRequest.proposal_id == request.proposal_id)
                .where(PendingVoteRequest.session_id == request.session_id)
            )
            pending_vote = pending_result.scalar_one_or_none()

            if not pending_vote:
                return {"status": "error", "error": "Vote request not found"}

            # Save the vote
            vote = Vote(
                session_id=request.session_id,
                proposal=pending_vote.proposal,
                proposal_id=request.proposal_id,
                persona_name=request.persona_name,
                vote=vote_type,
                reasoning=request.reasoning,
                confidence=request.confidence,
                rank=request.rank,  # For ranked choice voting
            )
            db.add(vote)
            await db.commit()

        # Broadcast vote received
        await ws_manager.broadcast(request.session_id, WSEvent(
            type=WSEventType.VOTE_RECEIVED,
            data={
                "proposal_id": request.proposal_id,
                "persona_name": request.persona_name,
                "vote": request.vote,
                "confidence": request.confidence,
                "reasoning": request.reasoning,
            },
        ))

        # Check if all votes are in
        await _check_vote_completion(request.session_id, request.proposal_id)

        return {
            "status": "vote_submitted",
            "session_id": request.session_id,
            "proposal_id": request.proposal_id,
            "persona_name": request.persona_name,
            "vote": request.vote,
        }

    except Exception as e:
        return {"status": "error", "error": str(e)}


async def _check_vote_completion(session_id: int, proposal_id: str):
    """Check if all personas have voted and broadcast completion if so."""
    from ...db.database import AsyncSessionLocal
    from ...db.models import Session, SessionPersona, Vote, PendingVoteRequest
    from ..websocket.chat_handler import manager as ws_manager, WSEvent, WSEventType
    from sqlalchemy import select
    from datetime import datetime
    from collections import defaultdict

    async with AsyncSessionLocal() as db:
        # Get session to check if poll_mode
        session_result = await db.execute(
            select(Session).where(Session.id == session_id)
        )
        session = session_result.scalar_one_or_none()
        is_poll_mode = session and (session.config or {}).get("poll_mode", False)

        # Get all personas for session
        personas_result = await db.execute(
            select(SessionPersona).where(SessionPersona.session_id == session_id)
        )
        all_personas = {sp.persona_name for sp in personas_result.scalars().all()}

        # Get votes for this proposal
        votes_result = await db.execute(
            select(Vote)
            .where(Vote.session_id == session_id)
            .where(Vote.proposal_id == proposal_id)
        )
        votes = list(votes_result.scalars().all())
        voted_personas = {v.persona_name for v in votes}

        # Check if all have voted
        if voted_personas >= all_personas:
            # All voted - analyze and broadcast completion
            agree_count = sum(1 for v in votes if v.vote.value == "agree")
            disagree_count = sum(1 for v in votes if v.vote.value == "disagree")
            abstain_count = sum(1 for v in votes if v.vote.value == "abstain")

            total = len(votes)
            voting_count = agree_count + disagree_count

            agreement_score = agree_count / voting_count if voting_count > 0 else 0.5
            consensus_reached = agreement_score > 0.5 or (disagree_count / max(voting_count, 1)) > 0.5

            majority_vote = None
            if agree_count > disagree_count:
                majority_vote = "agree"
            elif disagree_count > agree_count:
                majority_vote = "disagree"

            dissenting_personas = []
            if majority_vote:
                for v in votes:
                    if v.vote.value != majority_vote and v.vote.value != "abstain":
                        dissenting_personas.append(v.persona_name)

            # === POLL MODE: Calculate additional voting formats ===
            poll_results = None
            if is_poll_mode:
                poll_results = _calculate_poll_results(votes)

            # Mark pending vote as completed
            pending_result = await db.execute(
                select(PendingVoteRequest)
                .where(PendingVoteRequest.proposal_id == proposal_id)
            )
            pending_vote = pending_result.scalar_one_or_none()
            if pending_vote:
                pending_vote.status = "completed"
                pending_vote.completed_at = datetime.utcnow()
                await db.commit()

            # Get proposal text
            proposal = pending_vote.proposal if pending_vote else ""

            # Build response data
            response_data = {
                "proposal": proposal,
                "proposal_id": proposal_id,
                "consensus_reached": consensus_reached,
                "agreement_score": agreement_score,
                "majority_vote": majority_vote,
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
                        "rank": v.rank,
                    }
                    for v in votes
                ],
            }

            # Add poll results if in poll mode
            if poll_results:
                response_data["poll_results"] = poll_results

            # Broadcast vote complete
            await ws_manager.broadcast(session_id, WSEvent(
                type=WSEventType.VOTE_COMPLETE,
                data=response_data,
            ))


def _calculate_poll_results(votes: list) -> dict:
    """
    Calculate poll results in multiple formats:
    - Simple Majority: Winner is option with most first-choice votes
    - Caucus: Group personas by their vote into coalitions
    - Ranked Choice (Instant Runoff): Eliminate lowest, redistribute until majority
    """
    from collections import defaultdict

    # Group votes by persona (in case of ranked ballots)
    persona_votes = defaultdict(list)
    for v in votes:
        persona_votes[v.persona_name].append({
            "vote": v.vote.value,
            "rank": v.rank or 1,
            "confidence": v.confidence,
        })

    # Sort each persona's votes by rank
    for persona in persona_votes:
        persona_votes[persona].sort(key=lambda x: x["rank"])

    # === SIMPLE MAJORITY ===
    # Count first-choice votes only
    first_choice_counts = defaultdict(int)
    for persona, ranked_votes in persona_votes.items():
        if ranked_votes:
            first_choice = ranked_votes[0]["vote"]
            first_choice_counts[first_choice] += 1

    total_voters = len(persona_votes)
    simple_majority_winner = None
    simple_majority_votes = 0
    for option, count in first_choice_counts.items():
        if count > simple_majority_votes:
            simple_majority_votes = count
            simple_majority_winner = option

    simple_majority = {
        "winner": simple_majority_winner,
        "votes": simple_majority_votes,
        "total_voters": total_voters,
        "percentage": round((simple_majority_votes / total_voters * 100) if total_voters > 0 else 0, 1),
        "breakdown": dict(first_choice_counts),
    }

    # === CAUCUS ===
    # Group personas by their first-choice vote
    caucuses = defaultdict(list)
    for persona, ranked_votes in persona_votes.items():
        if ranked_votes:
            first_choice = ranked_votes[0]["vote"]
            caucuses[first_choice].append({
                "persona": persona,
                "confidence": ranked_votes[0]["confidence"],
            })

    caucus_results = {
        option: {
            "members": members,
            "count": len(members),
            "percentage": round((len(members) / total_voters * 100) if total_voters > 0 else 0, 1),
        }
        for option, members in caucuses.items()
    }

    # === RANKED CHOICE (Instant Runoff) ===
    # Simulate instant runoff voting
    ranked_choice = _instant_runoff_voting(persona_votes)

    return {
        "simple_majority": simple_majority,
        "caucus": caucus_results,
        "ranked_choice": ranked_choice,
    }


def _instant_runoff_voting(persona_votes: dict) -> dict:
    """
    Simulate instant runoff voting (ranked choice).
    Eliminate lowest vote-getter, redistribute their votes, repeat until majority.
    """
    from collections import defaultdict

    # Make a working copy of ballots (list of ranked options per persona)
    ballots = {}
    for persona, ranked_votes in persona_votes.items():
        ballots[persona] = [v["vote"] for v in ranked_votes]

    rounds = []
    eliminated = set()
    winner = None

    while not winner:
        # Count first-choice votes (excluding eliminated options)
        counts = defaultdict(int)
        for persona, ballot in ballots.items():
            # Find first non-eliminated choice
            for choice in ballot:
                if choice not in eliminated:
                    counts[choice] += 1
                    break

        if not counts:
            break

        total_votes = sum(counts.values())
        round_data = {
            "counts": dict(counts),
            "total": total_votes,
            "eliminated": None,
        }

        # Check for majority
        for option, count in counts.items():
            if count > total_votes / 2:
                winner = option
                round_data["winner"] = winner
                rounds.append(round_data)
                break

        if winner:
            break

        # No majority - eliminate lowest
        if counts:
            min_votes = min(counts.values())
            # Find option(s) with min votes
            lowest = [opt for opt, cnt in counts.items() if cnt == min_votes]
            # Eliminate one (first alphabetically for determinism)
            to_eliminate = sorted(lowest)[0]
            eliminated.add(to_eliminate)
            round_data["eliminated"] = to_eliminate
            rounds.append(round_data)

        # Safety check - if only one option left, they win
        remaining = set(counts.keys()) - eliminated
        if len(remaining) == 1:
            winner = list(remaining)[0]
        elif len(remaining) == 0:
            break

        # Prevent infinite loop
        if len(rounds) > 50:
            break

    return {
        "winner": winner,
        "rounds": rounds,
        "total_rounds": len(rounds),
    }


@router.get("/mcp/pending")
async def get_pending_mcp_responses():
    """
    Get all sessions with pending MCP responses for multi-round discussions.

    Claude Code polls this every 15 seconds. Returns:
    - Which personas need to respond
    - Full conversation history so they can respond to each other
    - Current round number (1=initial response, 2+=discussion rounds)
    - Pending votes that need responses
    - Active polls and their phase information
    """
    from ...db.database import AsyncSessionLocal
    from ...db.models import Session, SessionPersona, Message, PendingVoteRequest, Vote, Poll, PollOption, PollVote, PollPhase
    from sqlalchemy import select, func

    pending_sessions = []
    pending_votes = []
    pending_polls = []

    async with AsyncSessionLocal() as db:
        # ===== ACTIVE POLLS =====
        polls_result = await db.execute(
            select(Poll).where(Poll.phase != PollPhase.COMPLETED)
        )
        active_polls = list(polls_result.scalars().all())

        for poll in active_polls:
            # Get personas for this session
            personas_result = await db.execute(
                select(SessionPersona).where(SessionPersona.session_id == poll.session_id)
            )
            all_personas = [sp.persona_name for sp in personas_result.scalars().all()]

            # Get session name
            session_result = await db.execute(
                select(Session).where(Session.id == poll.session_id)
            )
            session = session_result.scalar_one_or_none()

            # Determine who has submitted based on phase
            if poll.phase == PollPhase.SYNTHESIS:
                options_result = await db.execute(
                    select(PollOption).where(PollOption.poll_id == poll.id)
                )
                options = list(options_result.scalars().all())
                submitted = {opt.proposed_by for opt in options}
                pending = [p for p in all_personas if p not in submitted]

                if pending:
                    pending_polls.append({
                        "session_id": poll.session_id,
                        "session_name": session.name if session else "Unknown",
                        "poll_id": poll.poll_id,
                        "question": poll.question,
                        "phase": "synthesis",
                        "pending_personas": pending,
                        "submitted_personas": list(submitted),
                        "instructions": (
                            "POLL SYNTHESIS PHASE: Analyze the question and propose solutions.\n\n"
                            "Your response MUST include:\n"
                            "1. FRAMING: How you interpret/frame the question (1-2 sentences)\n"
                            "2. OPTIONS: 2-5 specific solutions/options you propose\n\n"
                            "Format:\n"
                            "FRAMING: [Your interpretation]\n"
                            "OPTIONS:\n"
                            "1. [First option]\n"
                            "2. [Second option]\n"
                            "3. [Third option]\n"
                            "..."
                        ),
                    })

            elif poll.phase == PollPhase.VOTE_ROUND_1:
                # Get options to vote on
                options_result = await db.execute(
                    select(PollOption).where(PollOption.poll_id == poll.id)
                )
                options = [{"id": opt.id, "text": opt.option_text} for opt in options_result.scalars().all()]

                # Get who has voted
                votes_result = await db.execute(
                    select(PollVote)
                    .where(PollVote.poll_id == poll.id)
                    .where(PollVote.vote_round == 1)
                )
                voted = {v.persona_name for v in votes_result.scalars().all()}
                pending = [p for p in all_personas if p not in voted]

                if pending:
                    pending_polls.append({
                        "session_id": poll.session_id,
                        "session_name": session.name if session else "Unknown",
                        "poll_id": poll.poll_id,
                        "question": poll.question,
                        "phase": "vote_round_1",
                        "pending_personas": pending,
                        "voted_personas": list(voted),
                        "options": options,
                        "instructions": (
                            "POLL VOTE ROUND 1: Rank ALL options from most preferred (1) to least.\n\n"
                            "This uses ranked choice voting to narrow to the top 5 options.\n\n"
                            "Format your response:\n"
                            "RANKINGS:\n"
                            "1. [option_id] - [brief reason]\n"
                            "2. [option_id] - [brief reason]\n"
                            "...(rank all options)"
                        ),
                    })

            elif poll.phase == PollPhase.VOTE_ROUND_2:
                # Get top 5 options
                options_result = await db.execute(
                    select(PollOption)
                    .where(PollOption.poll_id == poll.id)
                    .where(PollOption.is_active == True)
                )
                options = [{"id": opt.id, "text": opt.option_text, "score": opt.round_1_score} for opt in options_result.scalars().all()]

                # Get who has voted
                votes_result = await db.execute(
                    select(PollVote)
                    .where(PollVote.poll_id == poll.id)
                    .where(PollVote.vote_round == 2)
                )
                voted = {v.persona_name for v in votes_result.scalars().all()}
                pending = [p for p in all_personas if p not in voted]

                if pending:
                    pending_polls.append({
                        "session_id": poll.session_id,
                        "session_name": session.name if session else "Unknown",
                        "poll_id": poll.poll_id,
                        "question": poll.question,
                        "phase": "vote_round_2",
                        "pending_personas": pending,
                        "voted_personas": list(voted),
                        "top_5_options": options,
                        "instructions": (
                            "POLL VOTE ROUND 2 (FINAL): Vote on each top-5 option.\n\n"
                            "For EACH option, indicate:\n"
                            "- VOTE: AGREE / DISAGREE / ABSTAIN\n"
                            "- CONFIDENCE: 0.0 to 1.0\n"
                            "- REASON: Brief explanation\n\n"
                            "Format:\n"
                            "OPTION [id]: [AGREE/DISAGREE/ABSTAIN] (confidence: X.X) - [reason]\n"
                            "...(for all 5 options)"
                        ),
                    })
        # ===== PENDING VOTES =====
        # Get all pending vote requests
        vote_requests_result = await db.execute(
            select(PendingVoteRequest)
            .where(PendingVoteRequest.status == "pending")
        )
        vote_requests = list(vote_requests_result.scalars().all())

        for vote_req in vote_requests:
            # Get personas for this session
            personas_result = await db.execute(
                select(SessionPersona).where(SessionPersona.session_id == vote_req.session_id)
            )
            all_personas = [sp.persona_name for sp in personas_result.scalars().all()]

            # Get existing votes for this proposal
            existing_votes_result = await db.execute(
                select(Vote)
                .where(Vote.session_id == vote_req.session_id)
                .where(Vote.proposal_id == vote_req.proposal_id)
            )
            existing_votes = list(existing_votes_result.scalars().all())
            voted_personas = {v.persona_name for v in existing_votes}

            # Find personas that haven't voted yet
            pending_persona_votes = [p for p in all_personas if p not in voted_personas]

            if pending_persona_votes:
                # Get session for context
                session_result = await db.execute(
                    select(Session).where(Session.id == vote_req.session_id)
                )
                session = session_result.scalar_one_or_none()

                pending_votes.append({
                    "session_id": vote_req.session_id,
                    "session_name": session.name if session else "Unknown",
                    "proposal_id": vote_req.proposal_id,
                    "proposal": vote_req.proposal,
                    "pending_personas": pending_persona_votes,
                    "votes_received": [
                        {
                            "persona_name": v.persona_name,
                            "vote": v.vote.value,
                            "confidence": v.confidence,
                        }
                        for v in existing_votes
                    ],
                    "instructions": (
                        "Vote on this proposal. Respond with:\n"
                        "VOTE: [AGREE/DISAGREE/ABSTAIN]\n"
                        "CONFIDENCE: [0.0-1.0]\n"
                        "REASONING: [Your reasoning in 1-2 sentences]"
                    ),
                })
        # Get all sessions with mcp_mode enabled
        result = await db.execute(
            select(Session).where(Session.status != "completed")
        )
        sessions = result.scalars().all()

        for session in sessions:
            config = session.config or {}
            if not config.get("mcp_mode"):
                continue

            # ===== AUTO-CREATE POLL IF POLL_MODE ENABLED =====
            if config.get("poll_mode"):
                # Get the last user message
                last_user_result = await db.execute(
                    select(Message)
                    .where(Message.session_id == session.id)
                    .where(Message.role == "user")
                    .order_by(Message.turn_number.desc())
                    .limit(1)
                )
                last_user_msg = last_user_result.scalar_one_or_none()

                if last_user_msg:
                    # Check if there's already a poll created AFTER this user message
                    # This prevents creating duplicate polls for the same user message
                    existing_poll_result = await db.execute(
                        select(Poll)
                        .where(Poll.session_id == session.id)
                        .where(Poll.created_at >= last_user_msg.created_at)
                    )
                    existing_poll = existing_poll_result.scalar_one_or_none()

                    if not existing_poll:
                        # Auto-create a poll for this user message
                        import uuid
                        poll_id = str(uuid.uuid4())[:8]
                        new_poll = Poll(
                            session_id=session.id,
                            poll_id=poll_id,
                            question=last_user_msg.content,
                            phase=PollPhase.SYNTHESIS,
                        )
                        db.add(new_poll)
                        await db.commit()
                        # Poll auto-created for poll_mode session

                # Skip normal discussion handling - poll mode handles everything via pending_polls
                continue

            max_rounds = config.get("max_rounds", 3)  # Default 3 rounds
            min_rounds = config.get("min_rounds", 3)  # Minimum rounds before consensus check

            # Get personas for this session
            personas_result = await db.execute(
                select(SessionPersona).where(SessionPersona.session_id == session.id)
            )
            personas = [p.persona_name for p in personas_result.scalars().all()]

            if not personas:
                continue

            # Get the last user message turn
            last_user_result = await db.execute(
                select(Message)
                .where(Message.session_id == session.id)
                .where(Message.role == "user")
                .order_by(Message.turn_number.desc())
                .limit(1)
            )
            last_user_msg = last_user_result.scalar_one_or_none()

            if not last_user_msg:
                continue

            turn_number = last_user_msg.turn_number

            # Get all messages for this turn to determine current round
            turn_messages_result = await db.execute(
                select(Message)
                .where(Message.session_id == session.id)
                .where(Message.turn_number == turn_number)
                .order_by(Message.round_number, Message.created_at)
            )
            turn_messages = list(turn_messages_result.scalars().all())

            # Determine current round by checking which personas have responded
            # Round N is complete when all personas have responded in round N
            current_round = 1
            for round_num in range(1, max_rounds + 1):
                round_responses = [
                    m for m in turn_messages
                    if m.role == "assistant" and (m.round_number or 1) == round_num
                ]
                responded_in_round = {m.persona_name for m in round_responses}

                if responded_in_round >= set(personas):
                    # This round is complete, move to next
                    current_round = round_num + 1
                else:
                    # This round is incomplete
                    current_round = round_num
                    break

            # Check if we've hit max rounds
            if current_round > max_rounds:
                continue  # Discussion complete for this turn

            # Check for early termination at min_rounds if consensus reached
            if current_round > min_rounds:
                # Check if previous round showed consensus
                prev_round_responses = [
                    m.content for m in turn_messages
                    if m.role == "assistant" and (m.round_number or 1) == current_round - 1
                ]
                if prev_round_responses and _detect_consensus(prev_round_responses):
                    continue  # Consensus reached, no more rounds needed

            # Get personas that have responded in current round
            current_round_responses = [
                m for m in turn_messages
                if m.role == "assistant" and (m.round_number or 1) == current_round
            ]
            responded = {m.persona_name for m in current_round_responses}

            # Find pending personas for this round
            pending = [p for p in personas if p not in responded]

            if pending:
                # Build conversation history for context
                history = []
                for msg in turn_messages:
                    history.append({
                        "role": msg.role,
                        "persona_name": msg.persona_name,
                        "content": msg.content,
                        "round_number": msg.round_number or 1,
                    })

                # Get problem statement for context
                problem_statement = session.problem_statement or ""

                # Check if we're past min_rounds (consensus checking active)
                consensus_mode = current_round > min_rounds

                # Build config instructions
                config_instructions = []
                if config.get("require_citations"):
                    config_instructions.append("**CITATIONS REQUIRED**: You MUST cite sources for all factual claims using [Author, Year] or [Source Name] format.")
                if config.get("steelman_mode"):
                    config_instructions.append("**STEELMAN MODE**: Present the strongest version of opposing viewpoints before critiquing.")
                if config.get("devil_advocate"):
                    config_instructions.append("**DEVIL'S ADVOCATE**: Challenge consensus and surface counter-arguments.")
                if config.get("fact_check"):
                    config_instructions.append("**FACT CHECK**: Flag claims that need verification and note uncertainty.")
                if config.get("assumption_surfacing"):
                    config_instructions.append("**ASSUMPTION SURFACING**: Explicitly identify and question underlying assumptions.")
                if config.get("blind_spot_detection"):
                    config_instructions.append("**BLIND SPOT DETECTION**: Look for overlooked perspectives and blind spots.")

                pending_sessions.append({
                    "session_id": session.id,
                    "session_name": session.name,
                    "turn_number": turn_number,
                    "round_number": current_round,
                    "min_rounds": min_rounds,
                    "max_rounds": max_rounds,
                    "consensus_mode": consensus_mode,
                    "user_message": last_user_msg.content,
                    "problem_statement": problem_statement,
                    "pending_personas": pending,
                    "conversation_history": history,
                    "instructions": _get_round_instructions(current_round, max_rounds, min_rounds, consensus_mode),
                    "config_instructions": config_instructions,
                })

    return {
        "pending_count": sum(len(s["pending_personas"]) for s in pending_sessions),
        "pending_vote_count": sum(len(v["pending_personas"]) for v in pending_votes),
        "pending_poll_count": sum(len(p["pending_personas"]) for p in pending_polls),
        "sessions": pending_sessions,
        "votes": pending_votes,
        "polls": pending_polls,
    }


def _detect_consensus(responses: list[str]) -> bool:
    """
    Detect if personas have reached consensus based on their responses.

    Looks for:
    - Agreement phrases ("I agree", "we all seem to", "consensus", etc.)
    - Synthesis language ("in summary", "we've concluded", "final thoughts")
    - Low conflict indicators (absence of strong disagreement)

    Returns True if consensus appears to be reached.
    """
    if not responses or len(responses) < 2:
        return False

    # Agreement indicators
    agreement_phrases = [
        "i agree", "we agree", "consensus", "we all", "we've reached",
        "common ground", "shared understanding", "alignment", "in agreement",
        "as we've established", "we've concluded", "synthesis", "converge",
        "unanimous", "together we", "collectively", "unified view"
    ]

    # Strong disagreement indicators
    disagreement_phrases = [
        "strongly disagree", "fundamentally wrong", "completely oppose",
        "cannot accept", "reject this", "no consensus", "divided on",
        "irreconcilable", "stark contrast", "opposite view"
    ]

    # Count indicators across all responses
    agreement_count = 0
    disagreement_count = 0

    for response in responses:
        lower_response = response.lower()

        for phrase in agreement_phrases:
            if phrase in lower_response:
                agreement_count += 1

        for phrase in disagreement_phrases:
            if phrase in lower_response:
                disagreement_count += 1

    # Consensus if agreement indicators outweigh disagreement significantly
    # And at least half the responses show agreement signals
    min_agreement_threshold = len(responses) // 2

    return (
        agreement_count >= min_agreement_threshold and
        agreement_count > disagreement_count * 2
    )


@router.post("/trigger-processing/{session_id}")
async def trigger_session_processing(session_id: int):
    """
    Manually trigger the orchestrator to process pending user messages.

    Use this when a session was created with a problem_statement but
    the orchestrator wasn't automatically triggered (e.g., for non-MCP providers).
    """
    from ...db.database import AsyncSessionLocal
    from ...db.models import Session, SessionPersona, Message
    from ...core.orchestrator import get_orchestrator
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        # Get session
        result = await db.execute(
            select(Session).where(Session.id == session_id)
        )
        session = result.scalar_one_or_none()

        if not session:
            return {"status": "error", "error": "Session not found"}

        # Get personas for this session
        personas_result = await db.execute(
            select(SessionPersona).where(SessionPersona.session_id == session_id)
        )
        personas = [p.persona_name for p in personas_result.scalars().all()]

        # Get the last user message
        msg_result = await db.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .where(Message.role == "user")
            .order_by(Message.turn_number.desc())
            .limit(1)
        )
        last_user_msg = msg_result.scalar_one_or_none()

        if not last_user_msg:
            return {"status": "error", "error": "No user message found"}

        # Check which personas have already responded for this turn
        assistant_result = await db.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .where(Message.role == "assistant")
            .where(Message.turn_number == last_user_msg.turn_number)
        )
        existing_responses = assistant_result.scalars().all()
        responded_personas = {r.persona_name for r in existing_responses}
        pending_personas = [p for p in personas if p not in responded_personas]

        if not pending_personas:
            return {
                "status": "skipped",
                "message": "All personas have already responded for this turn",
                "response_count": len(existing_responses),
            }

    # Trigger the orchestrator
    orchestrator = get_orchestrator(session_id)

    # Run in background so we can return immediately
    import asyncio
    asyncio.create_task(
        orchestrator.process_user_message(
            content=last_user_msg.content,
            turn_number=last_user_msg.turn_number,
        )
    )

    return {
        "status": "triggered",
        "session_id": session_id,
        "turn_number": last_user_msg.turn_number,
        "pending_personas": pending_personas,
        "message": f"Processing triggered for: {last_user_msg.content[:50]}...",
    }


def _get_round_instructions(round_number: int, max_rounds: int, min_rounds: int = 3, consensus_mode: bool = False) -> str:
    """Get instructions for personas based on current round."""
    if round_number == 1:
        return (
            "This is Round 1 (Initial Response). Respond directly to the user's question/topic. "
            "Share your unique perspective based on your expertise and worldview."
        )
    elif round_number == max_rounds:
        return (
            f"This is Round {round_number} (Final Round). Review what other personas have said. "
            "Offer your final thoughts, areas of agreement/disagreement, and any synthesis. "
            "This is the last round of discussion."
        )
    elif consensus_mode:
        return (
            f"This is Round {round_number} (Consensus Check). We're past the minimum {min_rounds} rounds. "
            "If you've reached consensus with the others, signal it clearly. "
            "If important disagreements remain, continue the discussion. "
            "The discussion will end early if consensus is detected, or continue to round {max_rounds}."
        )
    else:
        return (
            f"This is Round {round_number} of {min_rounds} minimum (Discussion Round). "
            "Read what the other personas said. Respond to their points - agree, disagree, "
            "build on their ideas, challenge assumptions, or offer new perspectives. "
            "Engage with specific points others made."
        )


# ==================== MULTI-PHASE POLL MODE ====================


class StartPollRequest(BaseModel):
    """Request to start a new multi-phase poll."""
    session_id: int
    question: str
    parent_poll_id: Optional[str] = None  # For sub-polls of complex questions


class SubmitSynthesisRequest(BaseModel):
    """Request to submit a synthesis response with proposed options."""
    session_id: int
    poll_id: str
    persona_name: str
    framing: str  # How the persona frames/interprets the question
    proposed_options: list[str]  # Options this persona proposes


class SubmitPollVoteRequest(BaseModel):
    """Request to submit a poll vote (round 1 or 2)."""
    session_id: int
    poll_id: str
    persona_name: str
    vote_round: int  # 1 or 2
    rankings: list[dict]  # [{"option_id": 1, "rank": 1}, ...] for round 1
    # For round 2: [{"option_id": 1, "vote": "agree/disagree/abstain", "confidence": 0.9}]


@router.post("/poll/start")
async def start_poll(request: StartPollRequest):
    """
    Start a new multi-phase poll.

    Phase 1 (Synthesis): Personas analyze the question and propose solutions.
    After all respond, options are collected and presented for voting.
    """
    from ...db.database import AsyncSessionLocal
    from ...db.models import Poll, PollPhase, Session
    from sqlalchemy import select
    import uuid

    async with AsyncSessionLocal() as db:
        # Verify session exists and is in poll mode
        session_result = await db.execute(
            select(Session).where(Session.id == request.session_id)
        )
        session = session_result.scalar_one_or_none()

        if not session:
            return {"status": "error", "error": "Session not found"}

        config = session.config or {}
        if not config.get("poll_mode"):
            return {"status": "error", "error": "Session is not in poll mode"}

        # Create the poll
        poll_id = str(uuid.uuid4())[:8]
        poll = Poll(
            session_id=request.session_id,
            poll_id=poll_id,
            question=request.question,
            phase=PollPhase.SYNTHESIS,
            parent_poll_id=request.parent_poll_id,
        )
        db.add(poll)
        await db.commit()

        return {
            "status": "poll_started",
            "poll_id": poll_id,
            "phase": "synthesis",
            "question": request.question,
            "instructions": (
                "SYNTHESIS PHASE: Each persona should:\n"
                "1. Frame/interpret the question from their perspective\n"
                "2. Propose 2-5 specific options/solutions\n"
                "3. Briefly explain the rationale for each option\n\n"
                "Format your response as:\n"
                "FRAMING: [How you interpret/frame the question]\n"
                "OPTIONS:\n"
                "1. [Option text]\n"
                "2. [Option text]\n"
                "..."
            ),
        }


@router.post("/poll/submit-synthesis")
async def submit_poll_synthesis(request: SubmitSynthesisRequest):
    """
    Submit a synthesis response from a persona.
    Extracts proposed options and stores them.
    """
    from ...db.database import AsyncSessionLocal
    from ...db.models import Poll, PollOption, PollPhase, SessionPersona
    from ..websocket.chat_handler import manager as ws_manager, WSEvent, WSEventType
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        # Get the poll
        poll_result = await db.execute(
            select(Poll).where(Poll.poll_id == request.poll_id)
        )
        poll = poll_result.scalar_one_or_none()

        if not poll:
            return {"status": "error", "error": "Poll not found"}

        if poll.phase != PollPhase.SYNTHESIS:
            return {"status": "error", "error": f"Poll is not in synthesis phase (current: {poll.phase})"}

        # Add proposed options
        for option_text in request.proposed_options:
            option = PollOption(
                poll_id=poll.id,
                option_text=option_text.strip(),
                proposed_by=request.persona_name,
            )
            db.add(option)

        await db.commit()

        # Check if all personas have submitted
        personas_result = await db.execute(
            select(SessionPersona).where(SessionPersona.session_id == poll.session_id)
        )
        all_personas = {sp.persona_name for sp in personas_result.scalars().all()}

        options_result = await db.execute(
            select(PollOption).where(PollOption.poll_id == poll.id)
        )
        all_options = list(options_result.scalars().all())
        submitted_personas = {opt.proposed_by for opt in all_options}

        all_submitted = submitted_personas >= all_personas

        # Broadcast synthesis received
        await ws_manager.broadcast(request.session_id, WSEvent(
            type=WSEventType.SYSTEM_MESSAGE,
            data={
                "type": "poll_synthesis",
                "poll_id": request.poll_id,
                "persona_name": request.persona_name,
                "framing": request.framing,
                "options_count": len(request.proposed_options),
                "all_submitted": all_submitted,
            },
        ))

        response = {
            "status": "synthesis_submitted",
            "poll_id": request.poll_id,
            "persona_name": request.persona_name,
            "options_added": len(request.proposed_options),
            "all_submitted": all_submitted,
        }

        # If all submitted, advance to vote round 1
        if all_submitted:
            poll.phase = PollPhase.VOTE_ROUND_1
            await db.commit()

            # Get deduplicated options for voting
            unique_options = _deduplicate_options(all_options)

            response["phase_advanced"] = True
            response["next_phase"] = "vote_round_1"
            response["options_for_voting"] = [
                {"id": opt.id, "text": opt.option_text, "proposed_by": opt.proposed_by}
                for opt in unique_options
            ]
            response["instructions"] = (
                "VOTE ROUND 1: Rank ALL options from most preferred (1) to least preferred.\n"
                "This round uses ranked choice voting to narrow down to the top 5 options.\n\n"
                "Format: RANKINGS: 1=[option_id], 2=[option_id], 3=[option_id], ..."
            )

            # Broadcast phase change
            await ws_manager.broadcast(request.session_id, WSEvent(
                type=WSEventType.SYSTEM_MESSAGE,
                data={
                    "type": "poll_phase_change",
                    "poll_id": request.poll_id,
                    "new_phase": "vote_round_1",
                    "options": response["options_for_voting"],
                },
            ))

        return response


def _deduplicate_options(options: list) -> list:
    """
    Deduplicate similar options using simple text similarity.
    Returns a list of unique options.
    """
    # Simple deduplication: lowercase comparison, remove very similar options
    seen = {}
    unique = []

    for opt in options:
        normalized = opt.option_text.lower().strip()
        # Check if we've seen something very similar
        is_duplicate = False
        for seen_text in seen:
            if _text_similarity(normalized, seen_text) > 0.8:
                is_duplicate = True
                break

        if not is_duplicate:
            seen[normalized] = opt
            unique.append(opt)

    return unique


def _text_similarity(a: str, b: str) -> float:
    """Simple text similarity using word overlap."""
    words_a = set(a.split())
    words_b = set(b.split())
    if not words_a or not words_b:
        return 0.0
    intersection = len(words_a & words_b)
    union = len(words_a | words_b)
    return intersection / union if union > 0 else 0.0


@router.post("/poll/submit-vote")
async def submit_poll_vote(request: SubmitPollVoteRequest):
    """
    Submit a poll vote for round 1 or round 2.

    Round 1: Ranked choice to narrow to top 5
    Round 2: Final vote with all 3 methods shown
    """
    from ...db.database import AsyncSessionLocal
    from ...db.models import Poll, PollOption, PollVote, PollPhase, SessionPersona
    from ..websocket.chat_handler import manager as ws_manager, WSEvent, WSEventType
    from sqlalchemy import select
    from datetime import datetime

    async with AsyncSessionLocal() as db:
        # Get the poll
        poll_result = await db.execute(
            select(Poll).where(Poll.poll_id == request.poll_id)
        )
        poll = poll_result.scalar_one_or_none()

        if not poll:
            return {"status": "error", "error": "Poll not found"}

        expected_phase = PollPhase.VOTE_ROUND_1 if request.vote_round == 1 else PollPhase.VOTE_ROUND_2
        if poll.phase != expected_phase:
            return {"status": "error", "error": f"Poll is not in vote round {request.vote_round}"}

        # Save votes
        for ranking in request.rankings:
            vote = PollVote(
                poll_id=poll.id,
                option_id=ranking["option_id"],
                persona_name=request.persona_name,
                vote_round=request.vote_round,
                rank=ranking.get("rank"),
                vote_value=ranking.get("vote"),
                confidence=ranking.get("confidence", 1.0),
                reasoning=ranking.get("reasoning"),
            )
            db.add(vote)

        await db.commit()

        # Check if all personas have voted
        personas_result = await db.execute(
            select(SessionPersona).where(SessionPersona.session_id == poll.session_id)
        )
        all_personas = {sp.persona_name for sp in personas_result.scalars().all()}

        votes_result = await db.execute(
            select(PollVote)
            .where(PollVote.poll_id == poll.id)
            .where(PollVote.vote_round == request.vote_round)
        )
        all_votes = list(votes_result.scalars().all())
        voted_personas = {v.persona_name for v in all_votes}

        all_voted = voted_personas >= all_personas

        response = {
            "status": "vote_submitted",
            "poll_id": request.poll_id,
            "vote_round": request.vote_round,
            "persona_name": request.persona_name,
            "all_voted": all_voted,
        }

        if all_voted:
            if request.vote_round == 1:
                # Process round 1: narrow to top 5 using ranked choice
                top_5 = await _process_round_1_votes(db, poll)

                poll.phase = PollPhase.VOTE_ROUND_2
                await db.commit()

                response["phase_advanced"] = True
                response["next_phase"] = "vote_round_2"
                response["top_5_options"] = top_5
                response["instructions"] = (
                    "VOTE ROUND 2 (FINAL): Vote on each of the top 5 options.\n"
                    "For each option, indicate: AGREE, DISAGREE, or ABSTAIN\n"
                    "Include confidence (0.0-1.0) and brief reasoning.\n\n"
                    "Results will show: Simple Majority, Caucus groupings, and Ranked Choice."
                )

                # Broadcast phase change
                await ws_manager.broadcast(request.session_id, WSEvent(
                    type=WSEventType.SYSTEM_MESSAGE,
                    data={
                        "type": "poll_phase_change",
                        "poll_id": request.poll_id,
                        "new_phase": "vote_round_2",
                        "top_5_options": top_5,
                    },
                ))

            else:
                # Process round 2: final results in all 3 formats
                final_results = await _process_round_2_votes(db, poll)

                poll.phase = PollPhase.COMPLETED
                poll.completed_at = datetime.utcnow()
                await db.commit()

                response["phase_advanced"] = True
                response["next_phase"] = "completed"
                response["final_results"] = final_results

                # Broadcast final results
                await ws_manager.broadcast(request.session_id, WSEvent(
                    type=WSEventType.VOTE_COMPLETE,
                    data={
                        "type": "poll_complete",
                        "poll_id": request.poll_id,
                        "question": poll.question,
                        "poll_results": final_results,
                    },
                ))

        return response


async def _process_round_1_votes(db, poll) -> list:
    """
    Process round 1 votes using ranked choice to get top 5 options.
    """
    from ...db.models import PollVote, PollOption
    from sqlalchemy import select
    from collections import defaultdict

    # Get all round 1 votes
    votes_result = await db.execute(
        select(PollVote)
        .where(PollVote.poll_id == poll.id)
        .where(PollVote.vote_round == 1)
    )
    votes = list(votes_result.scalars().all())

    # Get all options
    options_result = await db.execute(
        select(PollOption).where(PollOption.poll_id == poll.id)
    )
    all_options = {opt.id: opt for opt in options_result.scalars().all()}

    # Group votes by persona
    persona_ballots = defaultdict(list)
    for v in votes:
        persona_ballots[v.persona_name].append({
            "option_id": v.option_id,
            "rank": v.rank or 999,
        })

    # Sort each ballot by rank
    for persona in persona_ballots:
        persona_ballots[persona].sort(key=lambda x: x["rank"])

    # Calculate scores using Borda count (simple ranked aggregation)
    option_scores = defaultdict(float)
    total_options = len(all_options)

    for persona, ballot in persona_ballots.items():
        for item in ballot:
            # Borda: top choice gets N points, second gets N-1, etc.
            rank = item["rank"]
            points = max(0, total_options - rank + 1)
            option_scores[item["option_id"]] += points

    # Sort by score and take top 5
    sorted_options = sorted(option_scores.items(), key=lambda x: x[1], reverse=True)
    top_5_ids = [opt_id for opt_id, score in sorted_options[:5]]

    # Mark non-top-5 as inactive
    for opt_id, opt in all_options.items():
        opt.is_active = opt_id in top_5_ids
        if opt_id in dict(sorted_options):
            opt.round_1_score = dict(sorted_options)[opt_id]

    await db.commit()

    # Return top 5 for next round
    return [
        {
            "id": opt_id,
            "text": all_options[opt_id].option_text,
            "proposed_by": all_options[opt_id].proposed_by,
            "score": option_scores[opt_id],
        }
        for opt_id in top_5_ids
    ]


async def _process_round_2_votes(db, poll) -> dict:
    """
    Process round 2 votes and return results in all 3 formats.
    """
    from ...db.models import PollVote, PollOption
    from sqlalchemy import select
    from collections import defaultdict

    # Get all round 2 votes
    votes_result = await db.execute(
        select(PollVote)
        .where(PollVote.poll_id == poll.id)
        .where(PollVote.vote_round == 2)
    )
    votes = list(votes_result.scalars().all())

    # Get active options (top 5)
    options_result = await db.execute(
        select(PollOption)
        .where(PollOption.poll_id == poll.id)
        .where(PollOption.is_active == True)
    )
    options = {opt.id: opt for opt in options_result.scalars().all()}

    # Group votes by option
    option_votes = defaultdict(list)
    for v in votes:
        option_votes[v.option_id].append({
            "persona": v.persona_name,
            "vote": v.vote_value,
            "confidence": v.confidence,
            "reasoning": v.reasoning,
        })

    # === SIMPLE MAJORITY ===
    # For each option, count agrees vs disagrees
    simple_majority = {}
    for opt_id, opt in options.items():
        opt_votes = option_votes.get(opt_id, [])
        agrees = sum(1 for v in opt_votes if v["vote"] == "agree")
        disagrees = sum(1 for v in opt_votes if v["vote"] == "disagree")
        abstains = sum(1 for v in opt_votes if v["vote"] == "abstain")
        total = len(opt_votes)

        simple_majority[opt.option_text] = {
            "agrees": agrees,
            "disagrees": disagrees,
            "abstains": abstains,
            "total": total,
            "approval_rate": round((agrees / total * 100) if total > 0 else 0, 1),
        }

    # Find winner (highest approval)
    sm_winner = max(simple_majority.items(), key=lambda x: x[1]["approval_rate"])

    # === CAUCUS ===
    # Group personas by their voting pattern
    caucuses = defaultdict(list)
    persona_patterns = {}

    for v in votes:
        if v.persona_name not in persona_patterns:
            persona_patterns[v.persona_name] = {}
        persona_patterns[v.persona_name][v.option_id] = v.vote_value

    # Create pattern signatures and group
    for persona, pattern in persona_patterns.items():
        # Create a sorted tuple of (option_id, vote) as signature
        sig = tuple(sorted((k, v) for k, v in pattern.items()))
        caucuses[sig].append(persona)

    # Convert to readable format
    caucus_results = []
    for sig, members in caucuses.items():
        pattern_desc = ", ".join(
            f"{options[opt_id].option_text[:20]}={vote}"
            for opt_id, vote in sig if opt_id in options
        )
        caucus_results.append({
            "pattern": pattern_desc,
            "members": members,
            "count": len(members),
        })

    # === RANKED CHOICE (Instant Runoff) on top 5 ===
    # Use Round 1 rankings filtered to top 5 options for proper IRV
    top_5_ids = set(options.keys())

    # Get Round 1 rankings for these options
    round1_result = await db.execute(
        select(PollVote)
        .where(PollVote.poll_id == poll.id)
        .where(PollVote.vote_round == 1)
        .where(PollVote.option_id.in_(top_5_ids))
    )
    round1_votes = list(round1_result.scalars().all())

    # Build ballots: persona -> list of option_ids sorted by rank
    persona_ballots = defaultdict(list)
    for v in round1_votes:
        persona_ballots[v.persona_name].append((v.rank or 999, v.option_id))

    # Sort each ballot by rank and extract just option IDs
    for persona in persona_ballots:
        persona_ballots[persona].sort(key=lambda x: x[0])
        persona_ballots[persona] = [opt_id for _, opt_id in persona_ballots[persona]]

    # Run Instant Runoff Voting
    eliminated = set()
    irv_rounds = []
    winner = None

    while not winner and len(eliminated) < len(top_5_ids) - 1:
        # Count first-choice votes (excluding eliminated)
        first_choice_counts = defaultdict(int)
        for persona, ballot in persona_ballots.items():
            for opt_id in ballot:
                if opt_id not in eliminated:
                    first_choice_counts[opt_id] += 1
                    break

        if not first_choice_counts:
            break

        total_votes = sum(first_choice_counts.values())
        round_data = {
            "counts": {options[opt_id].option_text: count for opt_id, count in first_choice_counts.items()},
            "total": total_votes,
            "eliminated": None,
        }

        # Check for majority
        for opt_id, count in first_choice_counts.items():
            if count > total_votes / 2:
                winner = opt_id
                round_data["winner"] = options[opt_id].option_text
                round_data["winner_votes"] = count
                round_data["winner_pct"] = round(count / total_votes * 100, 1)
                irv_rounds.append(round_data)
                break

        if winner:
            break

        # No majority - eliminate option with fewest votes
        min_votes = min(first_choice_counts.values())
        lowest = [opt for opt, cnt in first_choice_counts.items() if cnt == min_votes]
        # Tie-breaker: eliminate alphabetically first by option text
        to_eliminate = min(lowest, key=lambda x: options[x].option_text)
        eliminated.add(to_eliminate)
        round_data["eliminated"] = options[to_eliminate].option_text
        round_data["eliminated_votes"] = min_votes
        irv_rounds.append(round_data)

        # Check if only one remains
        remaining = set(first_choice_counts.keys()) - eliminated
        if len(remaining) == 1:
            winner = list(remaining)[0]
            # Add final round showing winner
            final_count = sum(1 for p, b in persona_ballots.items()
                            for opt in b if opt == winner and opt not in eliminated)
            irv_rounds.append({
                "counts": {options[winner].option_text: total_votes},
                "total": total_votes,
                "winner": options[winner].option_text,
                "winner_votes": total_votes,
                "winner_pct": 100.0,
            })

    ranked_choice = {
        "winner": options[winner].option_text if winner else None,
        "winner_id": winner,
        "total_rounds": len(irv_rounds),
        "rounds": irv_rounds,
    }

    return {
        "simple_majority": {
            "winner": sm_winner[0],
            "winner_approval": sm_winner[1]["approval_rate"],
            "breakdown": simple_majority,
        },
        "caucus": caucus_results,
        "ranked_choice": ranked_choice,
        "vote_details": [
            {
                "option": options[v.option_id].option_text if v.option_id in options else "Unknown",
                "persona": v.persona_name,
                "vote": v.vote_value,
                "confidence": v.confidence,
                "reasoning": v.reasoning,
            }
            for v in votes
        ],
    }


@router.get("/poll/{poll_id}/status")
async def get_poll_status(poll_id: str):
    """Get the current status of a poll."""
    from ...db.database import AsyncSessionLocal
    from ...db.models import Poll, PollOption, PollVote, SessionPersona
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        poll_result = await db.execute(
            select(Poll).where(Poll.poll_id == poll_id)
        )
        poll = poll_result.scalar_one_or_none()

        if not poll:
            return {"status": "error", "error": "Poll not found"}

        # Get options
        options_result = await db.execute(
            select(PollOption).where(PollOption.poll_id == poll.id)
        )
        options = list(options_result.scalars().all())

        # Get votes
        votes_result = await db.execute(
            select(PollVote).where(PollVote.poll_id == poll.id)
        )
        votes = list(votes_result.scalars().all())

        # Get personas
        personas_result = await db.execute(
            select(SessionPersona).where(SessionPersona.session_id == poll.session_id)
        )
        personas = [p.persona_name for p in personas_result.scalars().all()]

        # Determine who has submitted for current phase
        if poll.phase.value == "synthesis":
            submitted = {opt.proposed_by for opt in options}
        elif poll.phase.value == "vote_round_1":
            submitted = {v.persona_name for v in votes if v.vote_round == 1}
        elif poll.phase.value == "vote_round_2":
            submitted = {v.persona_name for v in votes if v.vote_round == 2}
        else:
            submitted = set(personas)

        pending = [p for p in personas if p not in submitted]

        return {
            "poll_id": poll_id,
            "question": poll.question,
            "phase": poll.phase.value,
            "options_count": len(options),
            "active_options": len([o for o in options if o.is_active]),
            "total_personas": len(personas),
            "submitted_personas": list(submitted),
            "pending_personas": pending,
            "votes_count": len(votes),
        }
