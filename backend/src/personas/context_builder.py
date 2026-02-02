"""Context builder for constructing prompts and managing conversation context."""

import logging
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

try:
    import tiktoken
except ImportError:
    tiktoken = None

from ..db.models import SessionPhase, TurnMode

logger = logging.getLogger(__name__)


@dataclass
class ContextMessage:
    """A message in the conversation context."""
    role: str
    content: str
    persona_name: Optional[str] = None


class ContextBuilder:
    """Builds context and prompts for AI interactions."""

    def __init__(self, model: str = "gpt-4"):
        """Initialize with a model for token counting."""
        self.model = model
        self.encoding = self._get_encoding(model)

    def _get_encoding(self, model: str):
        """Get tiktoken encoding for the model."""
        if tiktoken is None:
            return None

        try:
            return tiktoken.encoding_for_model(model)
        except KeyError:
            # Fallback to cl100k_base for unknown models
            try:
                return tiktoken.get_encoding("cl100k_base")
            except Exception:
                return None

    def count_tokens(self, text: str) -> int:
        """Count tokens in a text string."""
        if not text:
            return 0

        if self.encoding:
            return len(self.encoding.encode(text))

        # Fallback: rough estimate of ~4 chars per token
        return len(text) // 4

    def build_system_prompt(
        self,
        persona,
        session_config: Dict[str, Any],
        current_phase: SessionPhase,
        turn_mode: TurnMode,
        other_personas: List[str],
        problem_statement: Optional[str] = None,
    ) -> str:
        """Build the system prompt for a persona."""
        parts = []

        # Base persona prompt
        parts.append(persona.get_system_prompt())

        # Problem context
        if problem_statement:
            parts.append(f"\n## Current Problem\n\n{problem_statement}")

        # Phase instructions
        phase_instr = self._get_phase_instructions(current_phase)
        parts.append(f"\n## Current Phase: {current_phase.value.title()}\n\n{phase_instr}")

        # Turn mode instructions
        turn_instr = self._get_turn_mode_instructions(turn_mode)
        parts.append(f"\n## Discussion Mode: {turn_mode.value.replace('_', ' ').title()}\n\n{turn_instr}")

        # Other personas in the session
        if other_personas:
            parts.append(f"\n## Other Participants\n\nYou are discussing with: {', '.join(other_personas)}")

        # Config-based special instructions
        config_instr = self._build_config_instructions(session_config)
        if config_instr:
            parts.append(f"\n## Special Instructions\n\n{config_instr}")

        return "\n".join(parts)

    def _get_phase_instructions(self, phase: SessionPhase) -> str:
        """Get instructions for the current phase."""
        instructions = {
            SessionPhase.DISCOVERY: (
                "Focus on understanding the problem deeply. Ask clarifying questions, "
                "identify key constraints, and surface assumptions that need validation."
            ),
            SessionPhase.IDEATION: (
                "Generate diverse ideas and possibilities. Build on others' suggestions, "
                "explore unconventional approaches, and don't self-censor at this stage."
            ),
            SessionPhase.EVALUATION: (
                "Critically assess the ideas proposed. Consider feasibility, risks, "
                "trade-offs, and alignment with goals. Be constructive but thorough."
            ),
            SessionPhase.DECISION: (
                "Work toward consensus on the best path forward. State your position "
                "clearly and be willing to adjust based on compelling arguments."
            ),
            SessionPhase.ACTION: (
                "Focus on concrete next steps and implementation. Define specific actions, "
                "ownership, and timelines. Be practical and actionable."
            ),
            SessionPhase.SYNTHESIS: (
                "Summarize the key insights and conclusions from the discussion. "
                "Capture areas of agreement, remaining questions, and lessons learned."
            ),
        }
        return instructions.get(phase, "Participate constructively in the discussion.")

    def _get_turn_mode_instructions(self, turn_mode: TurnMode) -> str:
        """Get instructions for the turn-taking mode."""
        instructions = {
            TurnMode.ROUND_ROBIN: (
                "Speak in turn rotation. Wait for your turn to contribute, "
                "then provide your perspective before passing to the next participant."
            ),
            TurnMode.MODERATOR: (
                "A moderator will call on speakers. Wait to be addressed by the moderator "
                "before contributing. The moderator ensures balanced participation."
            ),
            TurnMode.FREE_FORM: (
                "Respond naturally as the conversation flows. Jump in when you have "
                "something valuable to add. Avoid dominating - leave space for others."
            ),
            TurnMode.INTERRUPT: (
                "Feel free to interject and challenge ideas in real-time. "
                "Push back on weak arguments and demand evidence. Be direct but respectful."
            ),
            TurnMode.PARALLEL: (
                "Work independently alongside other participants. Each persona develops "
                "their perspective in parallel before sharing with the group."
            ),
        }
        return instructions.get(turn_mode, "Participate in the discussion.")

    def _build_config_instructions(self, config: Dict[str, Any]) -> str:
        """Build special instructions based on session config."""
        instructions = []

        if config.get("require_citations"):
            instructions.append(
                "**CITATIONS REQUIRED**: Back up claims with specific sources, data, "
                "or examples. Cite your sources explicitly."
            )

        if config.get("steelman_mode"):
            instructions.append(
                "**STEELMAN MODE**: Present the strongest version of opposing arguments. "
                "Give ideas the best possible interpretation before critiquing."
            )

        if config.get("devil_advocate"):
            instructions.append(
                "**DEVIL'S ADVOCATE**: Actively challenge emerging consensus. "
                "Find weaknesses in popular positions and voice unpopular perspectives."
            )

        if config.get("fact_check"):
            instructions.append(
                "**FACT CHECK**: Flag claims that need verification. "
                "Distinguish between established facts, reasonable inferences, and speculation."
            )

        if config.get("assumption_surfacing"):
            instructions.append(
                "**SURFACE ASSUMPTIONS**: Explicitly identify assumptions underlying "
                "your reasoning and others' arguments. Question hidden premises."
            )

        if config.get("blind_spot_detection"):
            instructions.append(
                "**BLIND SPOT DETECTION**: Point out overlooked perspectives, "
                "stakeholders, or considerations that haven't been addressed."
            )

        if config.get("time_box_minutes"):
            minutes = config["time_box_minutes"]
            instructions.append(f"**TIME CONSTRAINT**: This discussion is timeboxed to {minutes} minutes.")

        return "\n\n".join(instructions)

    def build_messages(
        self,
        conversation_history: List[Any],
        budget: int,
        system_prompt: str,
        include_all_recent: int = 5,
    ) -> List[ContextMessage]:
        """
        Build a list of messages that fits within the token budget.

        Args:
            conversation_history: List of message objects with role, content, persona_name
            budget: Maximum token budget for messages
            system_prompt: The system prompt (used to calculate available budget)
            include_all_recent: Number of recent messages to always include

        Returns:
            List of ContextMessage objects
        """
        if not conversation_history:
            return []

        # Calculate available budget after system prompt
        system_tokens = self.count_tokens(system_prompt)
        available_budget = budget - system_tokens

        if available_budget <= 0:
            return []

        # Split into recent and older messages
        recent_count = min(include_all_recent, len(conversation_history))
        recent_messages = conversation_history[-recent_count:] if recent_count > 0 else []
        older_messages = conversation_history[:-recent_count] if recent_count < len(conversation_history) else []

        result = []
        tokens_used = 0

        # First, try to add all recent messages
        recent_to_add = []
        for msg in recent_messages:
            content = getattr(msg, 'content', str(msg))
            msg_tokens = self.count_tokens(content)
            if tokens_used + msg_tokens <= available_budget:
                recent_to_add.append(ContextMessage(
                    role=getattr(msg, 'role', 'user'),
                    content=content,
                    persona_name=getattr(msg, 'persona_name', None),
                ))
                tokens_used += msg_tokens
            else:
                # Can't fit this recent message, truncate
                break

        # Then add older messages from most recent to oldest
        older_to_add = []
        for msg in reversed(older_messages):
            content = getattr(msg, 'content', str(msg))
            msg_tokens = self.count_tokens(content)
            if tokens_used + msg_tokens <= available_budget:
                older_to_add.append(ContextMessage(
                    role=getattr(msg, 'role', 'user'),
                    content=content,
                    persona_name=getattr(msg, 'persona_name', None),
                ))
                tokens_used += msg_tokens
            else:
                # Budget exceeded, stop adding older messages
                break

        # Combine: older messages (reversed back to chronological) + recent
        result = list(reversed(older_to_add)) + recent_to_add

        return result

    def format_message_for_context(
        self,
        message: ContextMessage,
        include_persona_label: bool = True,
    ) -> str:
        """Format a message for inclusion in context."""
        if include_persona_label and message.persona_name:
            return f"[{message.persona_name}] {message.content}"
        return message.content

    def estimate_response_tokens(self, prompt_tokens: int) -> int:
        """
        Estimate the expected response token count based on prompt length.

        Returns a value between 200 and 2000 tokens.
        """
        # Shorter prompts tend to get longer responses
        # Longer prompts tend to get more focused responses
        if prompt_tokens < 500:
            return 500
        elif prompt_tokens < 2000:
            return 400
        elif prompt_tokens < 5000:
            return 300
        else:
            return 200
