"""Tests for context builder module."""

import pytest
from unittest.mock import MagicMock
from src.personas.context_builder import ContextBuilder, ContextMessage
from src.db.models import SessionPhase, TurnMode


class TestContextMessage:
    """Tests for ContextMessage dataclass."""

    def test_create_context_message(self):
        """Test creating a ContextMessage."""
        msg = ContextMessage(
            role="user",
            content="Hello",
            persona_name="einstein",
        )
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.persona_name == "einstein"

    def test_context_message_without_persona(self):
        """Test ContextMessage without persona name."""
        msg = ContextMessage(role="user", content="Test")
        assert msg.persona_name is None


class TestContextBuilder:
    """Tests for ContextBuilder class."""

    def test_create_context_builder(self):
        """Test creating a ContextBuilder."""
        builder = ContextBuilder(model="gpt-4")
        assert builder.model == "gpt-4"

    def test_create_with_unknown_model(self):
        """Test creating with unknown model uses fallback encoding."""
        builder = ContextBuilder(model="unknown-model-xyz")
        # Should not raise, uses fallback encoding
        assert builder.encoding is not None

    def test_count_tokens(self):
        """Test counting tokens."""
        builder = ContextBuilder()
        count = builder.count_tokens("Hello, world!")
        assert isinstance(count, int)
        assert count > 0

    def test_count_tokens_empty(self):
        """Test counting tokens for empty string."""
        builder = ContextBuilder()
        count = builder.count_tokens("")
        assert count == 0

    def test_count_tokens_long_text(self):
        """Test counting tokens for long text."""
        builder = ContextBuilder()
        text = "word " * 1000
        count = builder.count_tokens(text)
        assert count > 500

    def test_build_system_prompt(self):
        """Test building system prompt."""
        builder = ContextBuilder()

        mock_persona = MagicMock()
        mock_persona.get_system_prompt.return_value = "You are Einstein."

        prompt = builder.build_system_prompt(
            persona=mock_persona,
            session_config={},
            current_phase=SessionPhase.DISCOVERY,
            turn_mode=TurnMode.ROUND_ROBIN,
            other_personas=["feynman", "curie"],
            problem_statement="How to achieve world peace?",
        )

        assert "Einstein" in prompt
        assert "world peace" in prompt
        assert "Discovery" in prompt
        assert "Round Robin" in prompt
        assert "feynman" in prompt

    def test_build_system_prompt_without_problem(self):
        """Test building system prompt without problem statement."""
        builder = ContextBuilder()

        mock_persona = MagicMock()
        mock_persona.get_system_prompt.return_value = "You are helpful."

        prompt = builder.build_system_prompt(
            persona=mock_persona,
            session_config={},
            current_phase=SessionPhase.IDEATION,
            turn_mode=TurnMode.FREE_FORM,
            other_personas=[],
        )

        assert "helpful" in prompt
        assert "Ideation" in prompt

    def test_get_phase_instructions(self):
        """Test getting phase instructions."""
        builder = ContextBuilder()

        # Discovery phase
        instr = builder._get_phase_instructions(SessionPhase.DISCOVERY)
        assert "understanding the problem" in instr.lower() or "clarifying questions" in instr.lower()

        # Ideation phase
        instr = builder._get_phase_instructions(SessionPhase.IDEATION)
        assert "ideas" in instr.lower() or "generate" in instr.lower()

        # Evaluation phase
        instr = builder._get_phase_instructions(SessionPhase.EVALUATION)
        assert "assess" in instr.lower() or "critically" in instr.lower()

        # Decision phase
        instr = builder._get_phase_instructions(SessionPhase.DECISION)
        assert "consensus" in instr.lower() or "position" in instr.lower()

        # Action phase
        instr = builder._get_phase_instructions(SessionPhase.ACTION)
        assert "next steps" in instr.lower() or "concrete" in instr.lower()

        # Synthesis phase
        instr = builder._get_phase_instructions(SessionPhase.SYNTHESIS)
        assert "summarize" in instr.lower() or "insights" in instr.lower()

    def test_get_turn_mode_instructions(self):
        """Test getting turn mode instructions."""
        builder = ContextBuilder()

        # Round robin
        instr = builder._get_turn_mode_instructions(TurnMode.ROUND_ROBIN)
        assert "turn" in instr.lower() or "rotation" in instr.lower()

        # Moderator
        instr = builder._get_turn_mode_instructions(TurnMode.MODERATOR)
        assert "moderator" in instr.lower()

        # Free form
        instr = builder._get_turn_mode_instructions(TurnMode.FREE_FORM)
        assert "respond" in instr.lower()

        # Interrupt
        instr = builder._get_turn_mode_instructions(TurnMode.INTERRUPT)
        assert "interject" in instr.lower() or "interrupt" in instr.lower() or "challenge" in instr.lower()

        # Parallel
        instr = builder._get_turn_mode_instructions(TurnMode.PARALLEL)
        assert "independently" in instr.lower() or "parallel" in instr.lower() or "alongside" in instr.lower()

    def test_build_config_instructions(self):
        """Test building config instructions."""
        builder = ContextBuilder()

        config = {
            "require_citations": True,
            "steelman_mode": True,
            "devil_advocate": True,
            "fact_check": True,
            "assumption_surfacing": True,
            "blind_spot_detection": True,
            "time_box_minutes": 30,
        }

        instr = builder._build_config_instructions(config)

        assert "cite" in instr.lower()
        assert "steelman" in instr.lower() or "strongest version" in instr.lower()
        assert "challenge" in instr.lower() or "devil" in instr.lower() or "consensus" in instr.lower()
        assert "verification" in instr.lower() or "flag" in instr.lower()
        assert "assumption" in instr.lower()
        assert "blind spot" in instr.lower() or "overlooked" in instr.lower()
        assert "30 minutes" in instr

    def test_build_config_instructions_empty(self):
        """Test building config instructions with empty config."""
        builder = ContextBuilder()
        instr = builder._build_config_instructions({})
        assert instr == ""

    def test_build_messages(self):
        """Test building messages list."""
        builder = ContextBuilder()

        # Create mock messages
        mock_msgs = [
            MagicMock(role="user", content="Hello", persona_name=None),
            MagicMock(role="assistant", content="Hi there!", persona_name="einstein"),
            MagicMock(role="user", content="How are you?", persona_name=None),
        ]

        messages = builder.build_messages(
            conversation_history=mock_msgs,
            budget=10000,
            system_prompt="You are helpful.",
            include_all_recent=5,
        )

        assert len(messages) == 3

    def test_build_messages_respects_budget(self):
        """Test that build_messages respects token budget."""
        builder = ContextBuilder()

        # Create many messages
        mock_msgs = [
            MagicMock(role="user", content="A" * 1000, persona_name=None)
            for _ in range(50)
        ]

        messages = builder.build_messages(
            conversation_history=mock_msgs,
            budget=500,  # Very small budget
            system_prompt="You are helpful.",
            include_all_recent=3,
        )

        # Should have fewer messages due to budget
        assert len(messages) < 50

    def test_build_messages_zero_budget(self):
        """Test build_messages with zero available budget."""
        builder = ContextBuilder()

        mock_msgs = [
            MagicMock(role="user", content="Test", persona_name=None),
        ]

        # Very long system prompt leaves no budget
        messages = builder.build_messages(
            conversation_history=mock_msgs,
            budget=100,
            system_prompt="A" * 10000,  # Exceeds budget
        )

        assert len(messages) == 0

    def test_format_message_for_context(self):
        """Test formatting message for context."""
        builder = ContextBuilder()

        msg = ContextMessage(role="assistant", content="Hello!", persona_name="einstein")
        formatted = builder.format_message_for_context(msg)

        assert "[einstein]" in formatted
        assert "Hello!" in formatted

    def test_format_message_without_persona_label(self):
        """Test formatting message without persona label."""
        builder = ContextBuilder()

        msg = ContextMessage(role="assistant", content="Hello!", persona_name="einstein")
        formatted = builder.format_message_for_context(msg, include_persona_label=False)

        assert "[einstein]" not in formatted
        assert formatted == "Hello!"

    def test_format_message_no_persona_name(self):
        """Test formatting message with no persona name."""
        builder = ContextBuilder()

        msg = ContextMessage(role="user", content="Hello!")
        formatted = builder.format_message_for_context(msg)

        assert formatted == "Hello!"

    def test_estimate_response_tokens(self):
        """Test estimating response tokens."""
        builder = ContextBuilder()

        # Short prompt
        estimate = builder.estimate_response_tokens(100)
        assert estimate >= 200  # Minimum

        # Medium prompt
        estimate = builder.estimate_response_tokens(2000)
        assert 200 <= estimate <= 2000

        # Long prompt
        estimate = builder.estimate_response_tokens(10000)
        assert estimate <= 2000  # Maximum

    def test_build_system_prompt_with_empty_config_instructions(self):
        """Test build_system_prompt when config exists but returns empty instructions."""
        builder = ContextBuilder()

        mock_persona = MagicMock()
        mock_persona.get_system_prompt.return_value = "You are helpful."

        # Config with values that don't generate instructions (all False)
        config = {
            "require_citations": False,
            "some_other_key": "value",
        }

        prompt = builder.build_system_prompt(
            persona=mock_persona,
            session_config=config,
            current_phase=SessionPhase.DISCOVERY,
            turn_mode=TurnMode.ROUND_ROBIN,
            other_personas=[],
        )

        # Should not have "Special Instructions" section if empty
        assert "helpful" in prompt

    def test_build_messages_truncate_recent_when_exceeds(self):
        """Test build_messages truncates recent messages when they exceed budget."""
        builder = ContextBuilder()

        # Create large recent messages
        mock_msgs = [
            MagicMock(role="user", content="A" * 2000, persona_name=None)
            for _ in range(10)
        ]

        # Budget allows only some of the recent messages
        messages = builder.build_messages(
            conversation_history=mock_msgs,
            budget=3000,
            system_prompt="Sys",
            include_all_recent=10,  # Want all 10 as recent but budget is small
        )

        # Should truncate - not all 10 messages
        assert len(messages) < 10
        # Should still have some messages
        assert len(messages) > 0

    def test_build_messages_includes_older_messages(self):
        """Test build_messages includes older messages when budget allows."""
        builder = ContextBuilder()

        # Create messages - some old, some recent
        mock_msgs = [
            MagicMock(role="user", content=f"Old message {i}", persona_name=None)
            for i in range(5)
        ] + [
            MagicMock(role="assistant", content=f"Recent {i}", persona_name="bot")
            for i in range(3)
        ]

        messages = builder.build_messages(
            conversation_history=mock_msgs,
            budget=50000,  # Large budget
            system_prompt="System",
            include_all_recent=3,  # Last 3 are recent
        )

        # Should include all 8 messages
        assert len(messages) == 8

    def test_build_messages_older_break_on_budget(self):
        """Test build_messages stops adding older messages when budget exceeded."""
        builder = ContextBuilder()

        # Create mix of small recent and large old messages
        old_msgs = [
            MagicMock(role="user", content="A" * 5000, persona_name=None)
            for _ in range(5)
        ]
        recent_msgs = [
            MagicMock(role="user", content="Small", persona_name=None)
            for _ in range(2)
        ]
        mock_msgs = old_msgs + recent_msgs

        messages = builder.build_messages(
            conversation_history=mock_msgs,
            budget=4000,
            system_prompt="Sys",
            include_all_recent=2,
        )

        # Should have recent 2 but not all old ones
        assert len(messages) >= 2
        assert len(messages) < 7
