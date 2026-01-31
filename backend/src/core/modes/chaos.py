"""Chaos mode for injecting unpredictability into discussions."""

import random
from typing import List, Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class ChaosEvent:
    """A chaos event to inject into the discussion."""
    name: str
    description: str
    prompt_injection: str
    probability: float = 0.1


# Predefined chaos events
CHAOS_EVENTS = [
    ChaosEvent(
        name="devil_advocate",
        description="Temporarily become a devil's advocate",
        prompt_injection="""
For this response only, take on the role of devil's advocate.
Challenge the prevailing view and argue the opposite position,
even if you don't personally agree with it. Be provocative but constructive.
""",
        probability=0.15,
    ),
    ChaosEvent(
        name="wild_idea",
        description="Propose a wild, unconventional idea",
        prompt_injection="""
For this response, propose the most creative and unconventional idea you can think of.
Don't worry about practicality - we're brainstorming. What if we threw out all constraints?
""",
        probability=0.1,
    ),
    ChaosEvent(
        name="historical_parallel",
        description="Draw a historical parallel",
        prompt_injection="""
For this response, draw an interesting parallel from history.
How does this problem relate to challenges faced in the past?
What can we learn from historical approaches?
""",
        probability=0.1,
    ),
    ChaosEvent(
        name="stakeholder_perspective",
        description="Consider an overlooked stakeholder",
        prompt_injection="""
For this response, consider a stakeholder or perspective that hasn't been discussed.
Who else might be affected by this? What would they think?
""",
        probability=0.1,
    ),
    ChaosEvent(
        name="worst_case",
        description="Explore worst-case scenarios",
        prompt_injection="""
For this response, explore the worst-case scenarios.
What could go catastrophically wrong? What are we not considering?
Be a pessimist for a moment.
""",
        probability=0.08,
    ),
    ChaosEvent(
        name="simplify_radically",
        description="Propose radical simplification",
        prompt_injection="""
For this response, propose a radically simpler approach.
What if we did 10% of the work for 90% of the value?
What's the MVP version of this idea?
""",
        probability=0.1,
    ),
    ChaosEvent(
        name="cross_domain",
        description="Apply ideas from another field",
        prompt_injection="""
For this response, apply ideas from a completely different field.
How would a chef/architect/athlete/musician approach this problem?
What can we steal from other domains?
""",
        probability=0.1,
    ),
    ChaosEvent(
        name="first_principles",
        description="Go back to first principles",
        prompt_injection="""
For this response, go back to first principles.
Forget everything we've discussed. What are the fundamental truths here?
What would we do if we were starting from scratch?
""",
        probability=0.08,
    ),
    ChaosEvent(
        name="future_self",
        description="Perspective from the future",
        prompt_injection="""
For this response, imagine you're looking back on this decision from 10 years in the future.
What would your future self wish you had considered?
What will matter in the long run?
""",
        probability=0.08,
    ),
    ChaosEvent(
        name="constraint_flip",
        description="Flip a key constraint",
        prompt_injection="""
For this response, flip one of the key constraints we've been assuming.
What if we had unlimited budget? What if we had to do this tomorrow?
What if the opposite of our assumption were true?
""",
        probability=0.1,
    ),
]


class ChaosMode:
    """
    Chaos injection for keeping discussions dynamic and avoiding groupthink.

    Randomly injects prompts that encourage:
    - Unconventional thinking
    - Challenge of assumptions
    - New perspectives
    - Creative exploration
    """

    def __init__(
        self,
        enabled: bool = True,
        intensity: float = 1.0,  # Multiplier for probabilities
        custom_events: Optional[List[ChaosEvent]] = None,
    ):
        self.enabled = enabled
        self.intensity = intensity
        self.events = CHAOS_EVENTS + (custom_events or [])
        self.event_history: List[str] = []

    def should_inject(self, turn_number: int) -> bool:
        """Determine if chaos should be injected this turn."""
        if not self.enabled:
            return False

        # Don't inject on first few turns
        if turn_number < 3:
            return False

        # Base probability that increases slightly over time
        base_prob = 0.15 + (turn_number * 0.01)  # Up to ~0.3 by turn 15
        base_prob *= self.intensity

        return random.random() < base_prob

    def get_injection(self, turn_number: int) -> Optional[str]:
        """Get a chaos injection prompt if triggered."""
        if not self.should_inject(turn_number):
            return None

        # Select event based on probabilities
        roll = random.random()
        cumulative = 0.0

        for event in self.events:
            cumulative += event.probability * self.intensity
            if roll < cumulative:
                self.event_history.append(event.name)
                return event.prompt_injection

        # If no event triggered, return None
        return None

    def get_specific_injection(self, event_name: str) -> Optional[str]:
        """Get a specific chaos injection by name."""
        for event in self.events:
            if event.name == event_name:
                self.event_history.append(event.name)
                return event.prompt_injection
        return None

    def add_custom_event(
        self,
        name: str,
        description: str,
        prompt_injection: str,
        probability: float = 0.1,
    ):
        """Add a custom chaos event."""
        self.events.append(ChaosEvent(
            name=name,
            description=description,
            prompt_injection=prompt_injection,
            probability=probability,
        ))

    def get_available_events(self) -> List[Dict[str, Any]]:
        """Get list of available chaos events."""
        return [
            {
                "name": e.name,
                "description": e.description,
                "probability": e.probability,
            }
            for e in self.events
        ]

    def get_history(self) -> List[str]:
        """Get history of injected events."""
        return self.event_history.copy()

    def reset(self):
        """Reset chaos mode state."""
        self.event_history = []
