"""Tests for adversarial mode module."""

import pytest
from src.core.modes.adversarial import (
    DebateRole,
    DebatePosition,
    AdversarialMode,
)


class TestDebateRole:
    """Tests for DebateRole enum."""

    def test_debate_roles_exist(self):
        """Test all debate roles exist."""
        assert DebateRole.PROPONENT == "proponent"
        assert DebateRole.OPPONENT == "opponent"
        assert DebateRole.JUDGE == "judge"
        assert DebateRole.STEELMAN == "steelman"
        assert DebateRole.SKEPTIC == "skeptic"

    def test_debate_role_is_string(self):
        """Test DebateRole values are strings."""
        assert isinstance(DebateRole.PROPONENT.value, str)
        assert isinstance(DebateRole.OPPONENT.value, str)


class TestDebatePosition:
    """Tests for DebatePosition dataclass."""

    def test_create_debate_position(self):
        """Test creating a DebatePosition."""
        position = DebatePosition(
            statement="AI will benefit humanity",
            proponent="einstein",
            opponent="feynman",
        )
        assert position.statement == "AI will benefit humanity"
        assert position.proponent == "einstein"
        assert position.opponent == "feynman"
        assert position.judge is None

    def test_debate_position_with_judge(self):
        """Test DebatePosition with judge."""
        position = DebatePosition(
            statement="Testing is important",
            proponent="a",
            opponent="b",
            judge="c",
        )
        assert position.judge == "c"


class TestAdversarialMode:
    """Tests for AdversarialMode class."""

    def test_create_adversarial_mode(self):
        """Test creating an AdversarialMode."""
        mode = AdversarialMode()
        assert mode.enabled is True
        assert mode.require_steelman is True
        assert mode.personas == []
        assert mode.current_debate is None
        assert mode.role_assignments == {}
        assert mode.debate_history == []

    def test_create_adversarial_mode_disabled(self):
        """Test creating a disabled AdversarialMode."""
        mode = AdversarialMode(enabled=False)
        assert mode.enabled is False

    def test_create_adversarial_mode_with_personas(self):
        """Test creating AdversarialMode with personas."""
        mode = AdversarialMode(personas=["einstein", "feynman", "curie"])
        assert len(mode.personas) == 3

    def test_setup_debate_minimum_personas(self):
        """Test setup_debate requires at least 2 personas."""
        mode = AdversarialMode()
        with pytest.raises(ValueError, match="Need at least 2 personas"):
            mode.setup_debate("test statement", personas=["only_one"])

    def test_setup_debate_two_personas(self):
        """Test setup_debate with 2 personas."""
        mode = AdversarialMode()
        roles = mode.setup_debate(
            "AI is beneficial",
            personas=["einstein", "feynman"]
        )

        assert len(roles) == 2
        assert DebateRole.PROPONENT in roles.values()
        assert DebateRole.OPPONENT in roles.values()
        assert mode.current_debate is not None
        assert mode.current_debate.statement == "AI is beneficial"

    def test_setup_debate_three_personas(self):
        """Test setup_debate with 3 personas includes judge."""
        mode = AdversarialMode()
        roles = mode.setup_debate(
            "Test statement",
            personas=["a", "b", "c"]
        )

        assert len(roles) == 3
        assert DebateRole.JUDGE in roles.values()
        assert mode.current_debate.judge is not None

    def test_setup_debate_four_personas(self):
        """Test setup_debate with 4 personas includes steelman."""
        mode = AdversarialMode()
        roles = mode.setup_debate(
            "Test",
            personas=["a", "b", "c", "d"]
        )

        assert len(roles) == 4
        assert DebateRole.STEELMAN in roles.values()

    def test_setup_debate_five_personas(self):
        """Test setup_debate with 5 personas includes skeptic."""
        mode = AdversarialMode()
        roles = mode.setup_debate(
            "Test",
            personas=["a", "b", "c", "d", "e"]
        )

        assert len(roles) == 5
        assert DebateRole.SKEPTIC in roles.values()

    def test_setup_debate_uses_default_personas(self):
        """Test setup_debate uses default personas."""
        mode = AdversarialMode(personas=["x", "y", "z"])
        roles = mode.setup_debate("Test")

        assert len(roles) == 3
        assert all(name in ["x", "y", "z"] for name in roles.keys())

    def test_get_role_prompt_disabled(self):
        """Test get_role_prompt when disabled."""
        mode = AdversarialMode(enabled=False)
        mode.setup_debate("Test", personas=["a", "b"])
        result = mode.get_role_prompt("a")
        assert result is None

    def test_get_role_prompt_not_assigned(self):
        """Test get_role_prompt for non-assigned persona."""
        mode = AdversarialMode()
        mode.setup_debate("Test", personas=["a", "b"])
        result = mode.get_role_prompt("c")
        assert result is None

    def test_get_role_prompt_proponent(self):
        """Test get_role_prompt for proponent."""
        mode = AdversarialMode()
        mode.setup_debate("AI is good", personas=["a", "b"])

        proponent = None
        for name, role in mode.role_assignments.items():
            if role == DebateRole.PROPONENT:
                proponent = name
                break

        prompt = mode.get_role_prompt(proponent)
        assert prompt is not None
        assert "IN FAVOR" in prompt
        assert "AI is good" in prompt

    def test_get_role_prompt_opponent(self):
        """Test get_role_prompt for opponent."""
        mode = AdversarialMode()
        mode.setup_debate("AI is good", personas=["a", "b"])

        opponent = None
        for name, role in mode.role_assignments.items():
            if role == DebateRole.OPPONENT:
                opponent = name
                break

        prompt = mode.get_role_prompt(opponent)
        assert prompt is not None
        assert "AGAINST" in prompt
        assert "AI is good" in prompt

    def test_get_role_prompt_judge(self):
        """Test get_role_prompt for judge."""
        mode = AdversarialMode()
        mode.setup_debate("Test", personas=["a", "b", "c"])

        judge = None
        for name, role in mode.role_assignments.items():
            if role == DebateRole.JUDGE:
                judge = name
                break

        prompt = mode.get_role_prompt(judge)
        assert prompt is not None
        assert "JUDGE" in prompt
        assert "evaluate" in prompt.lower()

    def test_get_role_prompt_steelman(self):
        """Test get_role_prompt for steelman."""
        mode = AdversarialMode()
        mode.setup_debate("Test", personas=["a", "b", "c", "d"])

        steelman = None
        for name, role in mode.role_assignments.items():
            if role == DebateRole.STEELMAN:
                steelman = name
                break

        prompt = mode.get_role_prompt(steelman)
        assert prompt is not None
        assert "STEELMAN" in prompt

    def test_get_role_prompt_skeptic(self):
        """Test get_role_prompt for skeptic."""
        mode = AdversarialMode()
        mode.setup_debate("Test", personas=["a", "b", "c", "d", "e"])

        skeptic = None
        for name, role in mode.role_assignments.items():
            if role == DebateRole.SKEPTIC:
                skeptic = name
                break

        prompt = mode.get_role_prompt(skeptic)
        assert prompt is not None
        assert "SKEPTIC" in prompt
        assert "question" in prompt.lower()

    def test_get_role_prompt_no_debate(self):
        """Test get_role_prompt with no current debate uses fallback."""
        mode = AdversarialMode()
        mode.role_assignments["test"] = DebateRole.PROPONENT
        mode.current_debate = None

        prompt = mode.get_role_prompt("test")
        assert prompt is not None
        assert "the topic at hand" in prompt

    def test_get_steelman_prompt(self):
        """Test get_steelman_prompt."""
        mode = AdversarialMode()
        prompt = mode.get_steelman_prompt("TDD is wasteful")

        assert "STEELMAN" in prompt
        assert "TDD is wasteful" in prompt
        assert "strongest" in prompt.lower()

    def test_get_red_team_prompt(self):
        """Test get_red_team_prompt."""
        mode = AdversarialMode()
        prompt = mode.get_red_team_prompt("Use microservices")

        assert "RED TEAM" in prompt
        assert "Use microservices" in prompt
        assert "go wrong" in prompt.lower()

    def test_get_socratic_prompt(self):
        """Test get_socratic_prompt."""
        mode = AdversarialMode()
        prompt = mode.get_socratic_prompt("Tests are important")

        assert "SOCRATIC" in prompt
        assert "Tests are important" in prompt
        assert "questions" in prompt.lower()

    def test_record_debate_round(self):
        """Test recording a debate round."""
        mode = AdversarialMode()
        mode.setup_debate("Test", personas=["a", "b", "c"])

        mode.record_debate_round(
            proponent_arg="Arguments for...",
            opponent_arg="Arguments against...",
            judge_evaluation="Both sides made valid points",
        )

        assert len(mode.debate_history) == 1
        record = mode.debate_history[0]
        assert record["proponent_arg"] == "Arguments for..."
        assert record["opponent_arg"] == "Arguments against..."
        assert record["judge_evaluation"] == "Both sides made valid points"
        assert record["statement"] == "Test"

    def test_record_debate_round_no_judge(self):
        """Test recording a debate round without judge evaluation."""
        mode = AdversarialMode()
        mode.setup_debate("Test", personas=["a", "b"])

        mode.record_debate_round(
            proponent_arg="For",
            opponent_arg="Against",
        )

        assert mode.debate_history[0]["judge_evaluation"] is None

    def test_swap_roles(self):
        """Test swapping proponent and opponent roles."""
        mode = AdversarialMode()
        mode.setup_debate("Test", personas=["a", "b"])

        original_proponent = mode.current_debate.proponent
        original_opponent = mode.current_debate.opponent

        mode.swap_roles()

        assert mode.current_debate.proponent == original_opponent
        assert mode.current_debate.opponent == original_proponent
        assert mode.role_assignments[original_proponent] == DebateRole.OPPONENT
        assert mode.role_assignments[original_opponent] == DebateRole.PROPONENT

    def test_swap_roles_no_debate(self):
        """Test swap_roles with no current debate."""
        mode = AdversarialMode()
        mode.swap_roles()  # Should not raise

    def test_get_debate_summary(self):
        """Test getting debate summary."""
        mode = AdversarialMode()
        mode.setup_debate("AI is good", personas=["a", "b", "c"])
        mode.record_debate_round("for", "against", "judge says")

        summary = mode.get_debate_summary()

        assert summary["enabled"] is True
        assert summary["current_statement"] == "AI is good"
        assert len(summary["roles"]) == 3
        assert summary["rounds_completed"] == 1
        assert summary["require_steelman"] is True

    def test_get_debate_summary_no_debate(self):
        """Test getting debate summary with no active debate."""
        mode = AdversarialMode()
        summary = mode.get_debate_summary()

        assert summary["enabled"] is True
        assert summary["current_statement"] is None
        assert summary["roles"] == {}
        assert summary["rounds_completed"] == 0

    def test_reset(self):
        """Test resetting adversarial mode."""
        mode = AdversarialMode()
        mode.setup_debate("Test", personas=["a", "b"])
        mode.record_debate_round("for", "against")

        mode.reset()

        assert mode.current_debate is None
        assert mode.role_assignments == {}
        assert mode.debate_history == []
