"""Adversarial mode for structured debate and opposition."""

import random
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum


class DebateRole(str, Enum):
    """Roles in an adversarial debate."""
    PROPONENT = "proponent"  # Argues for the position
    OPPONENT = "opponent"  # Argues against
    JUDGE = "judge"  # Evaluates arguments
    STEELMAN = "steelman"  # Strengthens opposing arguments
    SKEPTIC = "skeptic"  # Questions everything


@dataclass
class DebatePosition:
    """A position in a debate."""
    statement: str
    proponent: str
    opponent: str
    judge: Optional[str] = None


class AdversarialMode:
    """
    Adversarial debate mode for rigorous examination of ideas.

    Features:
    - Structured debate with assigned roles
    - Steelmanning: representing opposing views at their best
    - Red team / blue team exercises
    - Socratic questioning
    - Forced perspective-taking
    """

    def __init__(
        self,
        enabled: bool = True,
        require_steelman: bool = True,
        personas: Optional[List[str]] = None,
    ):
        self.enabled = enabled
        self.require_steelman = require_steelman
        self.personas = personas or []
        self.current_debate: Optional[DebatePosition] = None
        self.role_assignments: Dict[str, DebateRole] = {}
        self.debate_history: List[Dict[str, Any]] = []

    def setup_debate(
        self,
        statement: str,
        personas: Optional[List[str]] = None,
    ) -> Dict[str, DebateRole]:
        """Set up a new debate with role assignments."""
        available_personas = personas or self.personas

        if len(available_personas) < 2:
            raise ValueError("Need at least 2 personas for adversarial debate")

        # Randomly assign roles
        shuffled = available_personas.copy()
        random.shuffle(shuffled)

        self.role_assignments = {}
        self.role_assignments[shuffled[0]] = DebateRole.PROPONENT
        self.role_assignments[shuffled[1]] = DebateRole.OPPONENT

        if len(shuffled) > 2:
            self.role_assignments[shuffled[2]] = DebateRole.JUDGE

        if len(shuffled) > 3:
            self.role_assignments[shuffled[3]] = DebateRole.STEELMAN

        if len(shuffled) > 4:
            self.role_assignments[shuffled[4]] = DebateRole.SKEPTIC

        self.current_debate = DebatePosition(
            statement=statement,
            proponent=shuffled[0],
            opponent=shuffled[1],
            judge=shuffled[2] if len(shuffled) > 2 else None,
        )

        return self.role_assignments

    def get_role_prompt(self, persona_name: str) -> Optional[str]:
        """Get the adversarial role prompt for a persona."""
        if not self.enabled or persona_name not in self.role_assignments:
            return None

        role = self.role_assignments[persona_name]
        statement = self.current_debate.statement if self.current_debate else "the topic at hand"

        prompts = {
            DebateRole.PROPONENT: f"""
You are arguing IN FAVOR of the following position:
"{statement}"

Your role is to:
- Present the strongest possible case for this position
- Use evidence, logic, and compelling reasoning
- Anticipate and preemptively address counterarguments
- Remain persuasive while being intellectually honest
""",
            DebateRole.OPPONENT: f"""
You are arguing AGAINST the following position:
"{statement}"

Your role is to:
- Present the strongest possible case against this position
- Identify weaknesses, flaws, and problems with the argument
- Propose alternative viewpoints or solutions
- Challenge assumptions and evidence
- Remain intellectually rigorous, not just contrarian
""",
            DebateRole.JUDGE: f"""
You are the JUDGE evaluating arguments about:
"{statement}"

Your role is to:
- Evaluate the strength of arguments from both sides
- Identify which points are well-supported vs. weak
- Note logical fallacies or unsupported claims
- Summarize the state of the debate fairly
- Do NOT take a side - evaluate objectively
""",
            DebateRole.STEELMAN: f"""
You are the STEELMAN for:
"{statement}"

Your role is to:
- Take the OPPOSING view to what you might naturally believe
- Present that opposing view in its STRONGEST possible form
- Help the group understand the best version of the counterargument
- Find the most charitable interpretation of opposing positions
- This helps ensure we're not attacking strawmen
""",
            DebateRole.SKEPTIC: f"""
You are the SKEPTIC examining:
"{statement}"

Your role is to:
- Question EVERYTHING - from both sides
- Ask probing questions that expose weak assumptions
- Request evidence and clarification
- Challenge both the proponent and opponent
- Don't accept claims at face value
- Use Socratic questioning
""",
        }

        return prompts.get(role)

    def get_steelman_prompt(self, position_to_steelman: str) -> str:
        """Get a prompt for steelmanning a specific position."""
        return f"""
Before criticizing or disagreeing, you must first STEELMAN this position:
"{position_to_steelman}"

A steelman is the STRONGEST possible version of an argument.
- What's the most charitable interpretation?
- What evidence could support this view?
- What would a thoughtful proponent say?

Present this steelman first, THEN you may offer your actual response.
"""

    def get_red_team_prompt(self, proposal: str) -> str:
        """Get a prompt for red-teaming a proposal."""
        return f"""
You are RED TEAMING this proposal:
"{proposal}"

Your job is to attack this proposal ruthlessly but constructively:
- What could go wrong?
- What are the hidden assumptions?
- How could this fail?
- What are we not considering?
- What would critics say?
- What are the second-order effects?

Be thorough and creative in finding weaknesses.
"""

    def get_socratic_prompt(self, claim: str) -> str:
        """Get a Socratic questioning prompt."""
        return f"""
Use SOCRATIC QUESTIONING to examine this claim:
"{claim}"

Ask probing questions such as:
- What do we mean by [key terms]?
- What evidence supports this?
- What would change your mind?
- What are you assuming?
- What are the implications if this is true?
- Are there counterexamples?

Don't answer these questions yourself - pose them to advance the discussion.
"""

    def record_debate_round(
        self,
        proponent_arg: str,
        opponent_arg: str,
        judge_evaluation: Optional[str] = None,
    ):
        """Record a round of debate."""
        self.debate_history.append({
            "statement": self.current_debate.statement if self.current_debate else None,
            "proponent_arg": proponent_arg,
            "opponent_arg": opponent_arg,
            "judge_evaluation": judge_evaluation,
            "roles": self.role_assignments.copy(),
        })

    def swap_roles(self):
        """Swap proponent and opponent roles for perspective-taking."""
        if not self.current_debate:
            return

        # Swap the main roles
        proponent = self.current_debate.proponent
        opponent = self.current_debate.opponent

        self.current_debate.proponent = opponent
        self.current_debate.opponent = proponent

        if proponent in self.role_assignments:
            self.role_assignments[proponent] = DebateRole.OPPONENT
        if opponent in self.role_assignments:
            self.role_assignments[opponent] = DebateRole.PROPONENT

    def get_debate_summary(self) -> Dict[str, Any]:
        """Get a summary of the current debate state."""
        return {
            "enabled": self.enabled,
            "current_statement": self.current_debate.statement if self.current_debate else None,
            "roles": {
                name: role.value
                for name, role in self.role_assignments.items()
            },
            "rounds_completed": len(self.debate_history),
            "require_steelman": self.require_steelman,
        }

    def reset(self):
        """Reset adversarial mode state."""
        self.current_debate = None
        self.role_assignments = {}
        self.debate_history = []
