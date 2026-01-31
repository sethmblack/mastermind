"""Turn management for multi-agent conversations."""

import logging
import random
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

from ..db.models import TurnMode

logger = logging.getLogger(__name__)


@dataclass
class SpeakerState:
    """State of a speaker in the turn rotation."""
    name: str
    turns_taken: int = 0
    last_spoke_at_turn: int = -1
    is_moderator: bool = False
    is_active: bool = True
    interrupt_priority: int = 0  # Higher = more likely to interrupt


class TurnManager:
    """
    Manages turn-taking in multi-agent conversations.

    Supports multiple modes:
    - ROUND_ROBIN: Speakers take turns in order
    - MODERATOR: A moderator persona controls who speaks
    - FREE_FORM: Any persona can speak, weighted by relevance
    - INTERRUPT: Personas can interrupt based on urgency
    - PARALLEL: All personas respond simultaneously
    """

    def __init__(
        self,
        mode: TurnMode,
        personas: List[str],
        moderator: Optional[str] = None,
    ):
        self.mode = mode
        self.moderator = moderator
        self.current_index = 0
        self.turn_count = 0

        # Initialize speaker states
        self.speakers: Dict[str, SpeakerState] = {}
        for name in personas:
            self.speakers[name] = SpeakerState(
                name=name,
                is_moderator=(name == moderator),
            )

        # Queue for ordered modes
        self.speaker_queue: List[str] = list(personas)
        if moderator and moderator in self.speaker_queue:
            # Put moderator first
            self.speaker_queue.remove(moderator)
            self.speaker_queue.insert(0, moderator)

        # Interrupt queue for interrupt mode
        self.interrupt_queue: List[str] = []

    def get_next_speakers(
        self,
        user_message: Optional[str] = None,
        max_speakers: int = 1,
    ) -> List[str]:
        """
        Get the next speaker(s) based on the current mode.

        Args:
            user_message: The user's message (for relevance scoring)
            max_speakers: Maximum number of speakers to return

        Returns:
            List of persona names who should speak next
        """
        if self.mode == TurnMode.ROUND_ROBIN:
            return self._get_round_robin_speakers(max_speakers)

        elif self.mode == TurnMode.MODERATOR:
            return self._get_moderator_speakers(max_speakers)

        elif self.mode == TurnMode.FREE_FORM:
            return self._get_free_form_speakers(user_message, max_speakers)

        elif self.mode == TurnMode.INTERRUPT:
            return self._get_interrupt_speakers(user_message, max_speakers)

        elif self.mode == TurnMode.PARALLEL:
            return list(self.speakers.keys())

        return list(self.speakers.keys())[:max_speakers]

    def _get_round_robin_speakers(self, max_speakers: int) -> List[str]:
        """Get speakers in round-robin order."""
        active_speakers = [
            name for name, state in self.speakers.items()
            if state.is_active
        ]

        if not active_speakers:
            return []

        speakers = []
        for _ in range(min(max_speakers, len(active_speakers))):
            if self.current_index >= len(self.speaker_queue):
                self.current_index = 0
                self.turn_count += 1

            speaker = self.speaker_queue[self.current_index]
            if speaker in active_speakers:
                speakers.append(speaker)

            self.current_index += 1

        return speakers

    def _get_moderator_speakers(self, max_speakers: int) -> List[str]:
        """Get speakers with moderator controlling the flow."""
        # If there's a pending queue from moderator, use it
        if self.interrupt_queue:
            speakers = self.interrupt_queue[:max_speakers]
            self.interrupt_queue = self.interrupt_queue[max_speakers:]
            return speakers

        # Otherwise, moderator speaks first, then round-robin
        if self.moderator and self.speakers[self.moderator].is_active:
            # Check if moderator has spoken recently
            mod_state = self.speakers[self.moderator]
            if mod_state.last_spoke_at_turn < self.turn_count:
                return [self.moderator]

        # Fall back to round-robin for non-moderator speakers
        non_mod_speakers = [
            name for name in self.speaker_queue
            if name != self.moderator and self.speakers[name].is_active
        ]

        if not non_mod_speakers:
            return []

        idx = self.current_index % len(non_mod_speakers)
        return [non_mod_speakers[idx]]

    def _get_free_form_speakers(
        self,
        user_message: Optional[str],
        max_speakers: int,
    ) -> List[str]:
        """Get speakers based on relevance and activity."""
        active_speakers = [
            (name, state) for name, state in self.speakers.items()
            if state.is_active
        ]

        if not active_speakers:
            return []

        # Score speakers based on how long since they spoke
        scored = []
        for name, state in active_speakers:
            # Base score: turns since last spoke
            turns_silent = self.turn_count - state.last_spoke_at_turn
            score = min(turns_silent, 5)  # Cap at 5

            # Bonus for lower total turns taken (encourage balance)
            if state.turns_taken < self.turn_count / len(active_speakers):
                score += 1

            scored.append((score, name))

        # Sort by score (higher = more likely to speak)
        scored.sort(reverse=True)

        # Add some randomness - don't always pick the highest scorer
        if len(scored) > 1 and random.random() < 0.3:
            # 30% chance to pick second-highest instead
            scored[0], scored[1] = scored[1], scored[0]

        return [name for _, name in scored[:max_speakers]]

    def _get_interrupt_speakers(
        self,
        user_message: Optional[str],
        max_speakers: int,
    ) -> List[str]:
        """Get speakers who might interrupt based on urgency."""
        # Check interrupt queue first
        if self.interrupt_queue:
            speakers = self.interrupt_queue[:max_speakers]
            self.interrupt_queue = self.interrupt_queue[max_speakers:]
            return speakers

        # Otherwise, similar to free-form but with interrupt priority
        active_speakers = [
            (name, state) for name, state in self.speakers.items()
            if state.is_active
        ]

        scored = []
        for name, state in active_speakers:
            score = state.interrupt_priority
            turns_silent = self.turn_count - state.last_spoke_at_turn
            score += min(turns_silent, 3)
            scored.append((score, name))

        scored.sort(reverse=True)
        return [name for _, name in scored[:max_speakers]]

    def mark_speaker_done(self, speaker_name: str):
        """Mark a speaker as having completed their turn."""
        if speaker_name in self.speakers:
            state = self.speakers[speaker_name]
            state.turns_taken += 1
            state.last_spoke_at_turn = self.turn_count

    def add_to_queue(self, speaker_name: str, priority: bool = False):
        """Add a speaker to the queue (for moderator/interrupt modes)."""
        if speaker_name not in self.speakers:
            return

        if priority:
            self.interrupt_queue.insert(0, speaker_name)
        else:
            self.interrupt_queue.append(speaker_name)

    def set_interrupt_priority(self, speaker_name: str, priority: int):
        """Set interrupt priority for a speaker."""
        if speaker_name in self.speakers:
            self.speakers[speaker_name].interrupt_priority = priority

    def set_speaker_active(self, speaker_name: str, active: bool):
        """Enable or disable a speaker."""
        if speaker_name in self.speakers:
            self.speakers[speaker_name].is_active = active

    def get_speaker_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all speakers."""
        return {
            name: {
                "turns_taken": state.turns_taken,
                "last_spoke_at_turn": state.last_spoke_at_turn,
                "is_moderator": state.is_moderator,
                "is_active": state.is_active,
            }
            for name, state in self.speakers.items()
        }

    def reset(self):
        """Reset the turn manager state."""
        self.current_index = 0
        self.turn_count = 0
        self.interrupt_queue = []
        for state in self.speakers.values():
            state.turns_taken = 0
            state.last_spoke_at_turn = -1
