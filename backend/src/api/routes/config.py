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

    try:
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


@router.get("/mcp/pending")
async def get_pending_mcp_responses():
    """
    Get all sessions with pending MCP responses for multi-round discussions.

    Claude Code polls this every 15 seconds. Returns:
    - Which personas need to respond
    - Full conversation history so they can respond to each other
    - Current round number (1=initial response, 2+=discussion rounds)
    """
    from ...db.database import AsyncSessionLocal
    from ...db.models import Session, SessionPersona, Message
    from sqlalchemy import select, func

    pending_sessions = []

    async with AsyncSessionLocal() as db:
        # Get all sessions with mcp_mode enabled
        result = await db.execute(
            select(Session).where(Session.status != "completed")
        )
        sessions = result.scalars().all()

        for session in sessions:
            config = session.config or {}
            if not config.get("mcp_mode"):
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
                })

    return {
        "pending_count": sum(len(s["pending_personas"]) for s in pending_sessions),
        "sessions": pending_sessions,
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
