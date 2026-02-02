"""
MCP Auto-Responder Worker

Automatically generates persona responses when MCP mode is enabled.
Runs as a background task, polling for pending work and generating responses
using the Anthropic API.
"""

import asyncio
import logging
import os
from typing import Optional

import anthropic
import httpx

from ..personas.loader import get_persona_loader

logger = logging.getLogger(__name__)

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
CHECK_INTERVAL = int(os.getenv("MCP_CHECK_INTERVAL", "5"))

# Global flag to control the worker
_worker_running = False
_worker_task: Optional[asyncio.Task] = None


def generate_persona_response(
    persona_name: str,
    display_name: str,
    system_prompt: str,
    user_message: str,
    conversation_history: list,
    round_number: int,
    instructions: str,
) -> str:
    """Generate a response for a persona using the Anthropic API."""

    # Build conversation context
    messages = []

    # Add conversation history - format other personas' messages
    for msg in conversation_history:
        if msg["role"] == "user":
            messages.append({
                "role": "user",
                "content": msg["content"]
            })
        elif msg["role"] == "assistant":
            speaker = msg.get("persona_name", "Unknown")
            if speaker != persona_name:
                messages.append({
                    "role": "user",
                    "content": f"[{speaker} said]: {msg['content']}"
                })

    # Add the current instruction
    if round_number == 1:
        messages.append({
            "role": "user",
            "content": f"Topic: {user_message}\n\nRespond as {display_name}. Share your unique perspective in 2-3 paragraphs."
        })
    else:
        messages.append({
            "role": "user",
            "content": f"{instructions}\n\nRespond as {display_name} to the points made by others. 2-3 paragraphs."
        })

    # Ensure we have at least one message
    if not messages:
        messages.append({
            "role": "user",
            "content": f"Topic: {user_message}\n\nRespond as {display_name}."
        })

    try:
        client = anthropic.Anthropic()

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=system_prompt,
            messages=messages
        )

        return response.content[0].text

    except Exception as e:
        logger.error(f"Error generating response for {persona_name}: {e}")
        raise


async def process_pending_work():
    """Check for and process any pending MCP work."""

    async with httpx.AsyncClient() as client:
        # Get pending work
        try:
            response = await client.get(f"{API_BASE_URL}/api/config/mcp/pending")
            pending = response.json()
        except Exception as e:
            logger.error(f"Error fetching pending work: {e}")
            return

        if pending.get("pending_count", 0) == 0:
            return

        logger.info(f"🤖 Auto-responder: Found {pending['pending_count']} pending personas")

        loader = get_persona_loader()

        for session_data in pending.get("sessions", []):
            session_id = session_data["session_id"]
            round_number = session_data["round_number"]
            max_rounds = session_data["max_rounds"]
            user_message = session_data["user_message"]
            conversation_history = session_data.get("conversation_history", [])
            instructions = session_data.get("instructions", "")
            pending_personas = session_data["pending_personas"]

            logger.info(f"Processing session {session_id}, round {round_number}/{max_rounds}: {pending_personas}")

            # Generate responses for each pending persona
            for persona_name in pending_personas:
                try:
                    persona = loader.get_persona(persona_name)
                    if not persona:
                        logger.error(f"Persona not found: {persona_name}")
                        continue

                    logger.info(f"Generating response for {persona.display_name}...")

                    # Generate the response (sync call, but it's I/O bound to Anthropic)
                    content = generate_persona_response(
                        persona_name=persona_name,
                        display_name=persona.display_name,
                        system_prompt=persona.get_system_prompt(),
                        user_message=user_message,
                        conversation_history=conversation_history,
                        round_number=round_number,
                        instructions=instructions,
                    )

                    # Submit the response
                    submit_response = await client.post(
                        f"{API_BASE_URL}/api/config/mcp/submit-response",
                        json={
                            "session_id": session_id,
                            "persona_name": persona_name,
                            "content": content,
                            "round_number": round_number,
                        }
                    )

                    result = submit_response.json()
                    logger.info(f"✅ Submitted response for {persona.display_name}: {result.get('status')}")

                except Exception as e:
                    logger.error(f"❌ Error processing {persona_name}: {e}")


async def worker_loop(check_interval: int = 5):
    """Main worker loop that polls for pending work."""
    global _worker_running

    logger.info(f"🚀 MCP Auto-Responder started (checking every {check_interval}s)")

    while _worker_running:
        try:
            await process_pending_work()
        except Exception as e:
            logger.error(f"Error in worker loop: {e}")

        await asyncio.sleep(check_interval)

    logger.info("MCP Auto-Responder stopped")


async def start_worker_async(check_interval: int = 5):
    """Start the auto-responder worker (async version)."""
    global _worker_running, _worker_task

    if _worker_running:
        logger.warning("Worker already running")
        return

    # Check if ANTHROPIC_API_KEY is set
    if not os.getenv("ANTHROPIC_API_KEY"):
        logger.warning("⚠️ ANTHROPIC_API_KEY not set - MCP Auto-Responder disabled")
        return

    _worker_running = True
    _worker_task = asyncio.create_task(worker_loop(check_interval))
    logger.info("✅ MCP Auto-Responder worker started")


def stop_worker():
    """Stop the auto-responder worker."""
    global _worker_running, _worker_task

    _worker_running = False
    if _worker_task:
        _worker_task.cancel()
        _worker_task = None
    logger.info("MCP Auto-Responder worker stopped")


def is_worker_running() -> bool:
    """Check if the worker is running."""
    return _worker_running
