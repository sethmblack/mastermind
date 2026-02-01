"""Tests for the orchestrator module."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from src.core.orchestrator import (
    Orchestrator,
    OrchestratorState,
    PersonaState,
    get_orchestrator,
    remove_orchestrator,
    _orchestrators,
)
from src.db.models import SessionPhase, SessionStatus, TurnMode
from src.core.turn_manager import TurnManager
from src.core.consensus_engine import ConsensusEngine


class TestOrchestratorState:
    """Tests for OrchestratorState enum."""

    def test_orchestrator_states(self):
        """Test all orchestrator states exist."""
        assert OrchestratorState.IDLE == "idle"
        assert OrchestratorState.RUNNING == "running"
        assert OrchestratorState.PAUSED == "paused"
        assert OrchestratorState.STOPPED == "stopped"
        assert OrchestratorState.VOTING == "voting"


class TestPersonaState:
    """Tests for PersonaState dataclass."""

    def test_create_persona_state(self):
        """Test creating a PersonaState."""
        mock_persona = MagicMock()
        mock_sp = MagicMock()
        mock_provider = MagicMock()
        mock_cm = MagicMock()

        state = PersonaState(
            persona=mock_persona,
            session_persona=mock_sp,
            provider=mock_provider,
            context_manager=mock_cm,
        )
        assert state.total_input_tokens == 0
        assert state.total_output_tokens == 0
        assert state.message_count == 0

    def test_persona_state_defaults(self):
        """Test PersonaState default values."""
        state = PersonaState(
            persona=MagicMock(),
            session_persona=MagicMock(),
            provider=MagicMock(),
            context_manager=MagicMock(),
        )
        assert state.total_input_tokens == 0
        assert state.total_output_tokens == 0
        assert state.message_count == 0


class TestOrchestrator:
    """Tests for Orchestrator class."""

    def test_create_orchestrator(self):
        """Test creating an orchestrator."""
        orch = Orchestrator(session_id=1)
        assert orch.session_id == 1
        assert orch.state == OrchestratorState.IDLE
        assert orch._initialized is False

    def test_orchestrator_initial_state(self):
        """Test orchestrator initial state."""
        orch = Orchestrator(session_id=123)
        assert orch.turn_manager is None
        assert orch.consensus_engine is None
        assert orch.personas == {}
        assert orch.current_turn == 0

    @pytest.mark.asyncio
    async def test_pause(self):
        """Test pausing orchestrator."""
        orch = Orchestrator(session_id=1)
        await orch.pause()
        assert orch.state == OrchestratorState.PAUSED

    @pytest.mark.asyncio
    async def test_resume_from_paused(self):
        """Test resuming from paused state."""
        orch = Orchestrator(session_id=1)
        orch.state = OrchestratorState.PAUSED
        await orch.resume()
        assert orch.state == OrchestratorState.RUNNING

    @pytest.mark.asyncio
    async def test_resume_from_non_paused(self):
        """Test resuming from non-paused state does nothing."""
        orch = Orchestrator(session_id=1)
        orch.state = OrchestratorState.RUNNING
        await orch.resume()
        assert orch.state == OrchestratorState.RUNNING

    @pytest.mark.asyncio
    async def test_stop(self):
        """Test stopping orchestrator."""
        orch = Orchestrator(session_id=1)

        # Mock the database call
        with patch("src.core.orchestrator.AsyncSessionLocal") as mock_session_cls:
            mock_session = AsyncMock()
            mock_session_cls.return_value.__aenter__.return_value = mock_session
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_session.execute.return_value = mock_result

            await orch.stop()

        assert orch.state == OrchestratorState.STOPPED


class TestOrchestratorRegistry:
    """Tests for orchestrator registry functions."""

    def test_get_orchestrator_creates_new(self):
        """Test getting orchestrator creates new if not exists."""
        # Clear registry
        _orchestrators.clear()

        orch = get_orchestrator(999)
        assert orch is not None
        assert orch.session_id == 999
        assert 999 in _orchestrators

        # Cleanup
        _orchestrators.clear()

    def test_get_orchestrator_returns_existing(self):
        """Test getting orchestrator returns existing."""
        _orchestrators.clear()

        orch1 = get_orchestrator(888)
        orch2 = get_orchestrator(888)
        assert orch1 is orch2

        _orchestrators.clear()

    def test_remove_orchestrator(self):
        """Test removing orchestrator from registry."""
        _orchestrators.clear()

        get_orchestrator(777)
        assert 777 in _orchestrators

        remove_orchestrator(777)
        assert 777 not in _orchestrators

    def test_remove_nonexistent_orchestrator(self):
        """Test removing nonexistent orchestrator does nothing."""
        _orchestrators.clear()
        remove_orchestrator(666)  # Should not raise
        assert 666 not in _orchestrators


class TestOrchestratorInitialize:
    """Tests for orchestrator initialization."""

    @pytest.mark.asyncio
    async def test_initialize_skips_if_already_initialized(self):
        """Test initialize skips if already done."""
        orch = Orchestrator(session_id=1)
        orch._initialized = True

        # Should return immediately without database calls
        await orch.initialize()
        assert orch._initialized is True

    @pytest.mark.asyncio
    async def test_initialize_raises_on_missing_session(self):
        """Test initialize raises error if session not found."""
        orch = Orchestrator(session_id=99999)

        with patch("src.core.orchestrator.AsyncSessionLocal") as mock_session_cls:
            mock_session = AsyncMock()
            mock_session_cls.return_value.__aenter__.return_value = mock_session
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_session.execute.return_value = mock_result

            with pytest.raises(ValueError, match="Session 99999 not found"):
                await orch.initialize()

    @pytest.mark.asyncio
    async def test_initialize_loads_session_data(self):
        """Test initialize loads session data correctly."""
        orch = Orchestrator(session_id=1)

        # Create mock session
        mock_session = MagicMock()
        mock_session.id = 1
        mock_session.config = {"test": True}
        mock_session.turn_mode = TurnMode.ROUND_ROBIN

        # Create mock session personas
        mock_sp1 = MagicMock()
        mock_sp1.persona_name = "einstein"
        mock_sp1.provider = "anthropic"
        mock_sp1.model = "claude-sonnet-4-20250514"
        mock_sp1.context_budget = 50000

        mock_personas = [mock_sp1]

        # Mock the loader
        mock_persona = MagicMock()
        mock_persona.name = "einstein"
        mock_loader = MagicMock()
        mock_loader.get_persona.return_value = mock_persona

        # Mock provider
        mock_provider = MagicMock()

        with patch("src.core.orchestrator.AsyncSessionLocal") as mock_session_cls:
            mock_db = AsyncMock()
            mock_session_cls.return_value.__aenter__.return_value = mock_db

            # Setup execute calls
            mock_session_result = MagicMock()
            mock_session_result.scalar_one_or_none.return_value = mock_session

            mock_personas_result = MagicMock()
            mock_personas_result.scalars.return_value.all.return_value = mock_personas

            mock_msg_result = MagicMock()
            mock_msg_result.scalar_one_or_none.return_value = None

            mock_db.execute = AsyncMock(side_effect=[
                mock_session_result,
                mock_personas_result,
                mock_msg_result,
            ])

            with patch("src.core.orchestrator.get_persona_loader", return_value=mock_loader):
                with patch("src.core.orchestrator.get_provider", return_value=mock_provider):
                    await orch.initialize()

        assert orch._initialized is True
        assert orch.session == mock_session
        assert "einstein" in orch.personas

    @pytest.mark.asyncio
    async def test_start_discussion(self):
        """Test starting a discussion."""
        orch = Orchestrator(session_id=1)
        orch._initialized = True
        orch.session = MagicMock()
        orch.personas = {"einstein": MagicMock()}
        orch.state = OrchestratorState.IDLE

        with patch("src.core.orchestrator.AsyncSessionLocal") as mock_session_cls:
            mock_db = AsyncMock()
            mock_session_cls.return_value.__aenter__.return_value = mock_db
            mock_db.add = MagicMock()
            mock_db.commit = AsyncMock()

            await orch.start_discussion()

        assert orch.state == OrchestratorState.RUNNING

    @pytest.mark.asyncio
    async def test_start_discussion_already_running(self):
        """Test starting discussion when already running."""
        orch = Orchestrator(session_id=1)
        orch._initialized = True
        orch.state = OrchestratorState.RUNNING

        await orch.start_discussion()

        # State should still be running
        assert orch.state == OrchestratorState.RUNNING

    @pytest.mark.asyncio
    async def test_advance_phase(self):
        """Test advancing session phase."""
        orch = Orchestrator(session_id=1)
        orch._initialized = True

        mock_session = MagicMock()
        mock_session.phase = SessionPhase.DISCOVERY
        mock_session.version = 1

        with patch("src.core.orchestrator.AsyncSessionLocal") as mock_session_cls:
            mock_db = AsyncMock()
            mock_session_cls.return_value.__aenter__.return_value = mock_db

            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_session
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_db.add = MagicMock()
            mock_db.commit = AsyncMock()

            with patch("src.core.orchestrator.ws_manager") as mock_ws:
                mock_ws.broadcast = AsyncMock()

                await orch.advance_phase(SessionPhase.IDEATION)

        assert mock_session.phase == SessionPhase.IDEATION
        assert mock_session.version == 2


class TestOrchestratorProcessUserMessage:
    """Tests for processing user messages."""

    @pytest.mark.asyncio
    async def test_process_user_message_parallel_mode(self):
        """Test processing user message in parallel mode."""
        orch = Orchestrator(session_id=1)
        orch._initialized = True

        # Create mock session with PARALLEL mode
        mock_session = MagicMock()
        mock_session.id = 1
        mock_session.turn_mode = TurnMode.PARALLEL
        mock_session.phase = SessionPhase.DISCOVERY
        mock_session.problem_statement = "Test problem"
        mock_session.config = {}
        orch.session = mock_session
        orch.state = OrchestratorState.RUNNING

        # Create mock personas
        mock_persona = MagicMock()
        mock_persona.name = "einstein"

        mock_sp = MagicMock()
        mock_sp.provider = "anthropic"
        mock_sp.model = "claude-sonnet-4-20250514"

        mock_provider = MagicMock()
        mock_cm = MagicMock()

        orch.personas = {
            "einstein": PersonaState(
                persona=mock_persona,
                session_persona=mock_sp,
                provider=mock_provider,
                context_manager=mock_cm,
            )
        }

        # Mock turn manager
        orch.turn_manager = MagicMock()

        # Mock _generate_persona_response to avoid actual API calls
        orch._generate_persona_response = AsyncMock()
        orch._get_conversation_history = AsyncMock(return_value=[])

        await orch.process_user_message("Test message", turn_number=1)

        # In parallel mode, all personas should be called
        orch._generate_persona_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_user_message_round_robin_mode(self):
        """Test processing user message in round robin mode."""
        orch = Orchestrator(session_id=1)
        orch._initialized = True

        mock_session = MagicMock()
        mock_session.id = 1
        mock_session.turn_mode = TurnMode.ROUND_ROBIN
        mock_session.phase = SessionPhase.DISCOVERY
        mock_session.problem_statement = "Test"
        mock_session.config = {}
        orch.session = mock_session
        orch.state = OrchestratorState.RUNNING

        mock_persona = MagicMock()
        mock_sp = MagicMock()
        mock_sp.provider = "anthropic"
        mock_sp.model = "claude-sonnet-4-20250514"
        mock_provider = MagicMock()
        mock_cm = MagicMock()

        orch.personas = {
            "einstein": PersonaState(
                persona=mock_persona,
                session_persona=mock_sp,
                provider=mock_provider,
                context_manager=mock_cm,
            )
        }

        mock_turn_manager = MagicMock()
        mock_turn_manager.get_next_speakers.return_value = ["einstein"]
        orch.turn_manager = mock_turn_manager

        orch._generate_persona_response = AsyncMock()
        orch._get_conversation_history = AsyncMock(return_value=[])

        await orch.process_user_message("Test", turn_number=1)

        # Should call get_next_speakers
        mock_turn_manager.get_next_speakers.assert_called_once()
        orch._generate_persona_response.assert_called_once()


class TestOrchestratorGeneratePersonaResponse:
    """Tests for generating persona responses."""

    @pytest.mark.asyncio
    async def test_generate_response_unknown_persona(self):
        """Test generating response for unknown persona logs warning."""
        orch = Orchestrator(session_id=1)
        orch._initialized = True
        orch.personas = {}

        # Should not raise, just log warning
        await orch._generate_persona_response("unknown", [], 1)

    @pytest.mark.asyncio
    async def test_generate_response_with_streaming(self):
        """Test generating response with streaming."""
        orch = Orchestrator(session_id=1)
        orch._initialized = True

        mock_session = MagicMock()
        mock_session.id = 1
        mock_session.phase = SessionPhase.DISCOVERY
        mock_session.turn_mode = TurnMode.ROUND_ROBIN
        mock_session.problem_statement = "Test problem"
        mock_session.config = {}
        orch.session = mock_session
        orch.config = {}  # Set orchestrator config

        mock_persona = MagicMock()
        mock_persona.name = "einstein"

        mock_sp = MagicMock()
        mock_sp.provider = "anthropic"
        mock_sp.model = "claude-sonnet-4-20250514"

        # Create mock provider with streaming
        mock_provider = MagicMock()

        async def mock_stream(*args, **kwargs):
            yield MagicMock(content="Hello", is_finished=False)
            yield MagicMock(content=" world", is_finished=False)
            yield MagicMock(content="", is_finished=True, input_tokens=10, output_tokens=5)

        mock_provider.generate_stream = mock_stream
        mock_provider.calculate_cost = MagicMock(return_value=0.001)

        mock_cm = MagicMock()

        orch.personas = {
            "einstein": PersonaState(
                persona=mock_persona,
                session_persona=mock_sp,
                provider=mock_provider,
                context_manager=mock_cm,
            )
        }

        mock_turn_manager = MagicMock()
        orch.turn_manager = mock_turn_manager

        # Mock WebSocket and DB calls
        with patch("src.core.orchestrator.send_turn_start", new_callable=AsyncMock):
            with patch("src.core.orchestrator.send_persona_thinking", new_callable=AsyncMock):
                with patch("src.core.orchestrator.send_persona_chunk", new_callable=AsyncMock):
                    with patch("src.core.orchestrator.send_persona_done", new_callable=AsyncMock):
                        with patch("src.core.orchestrator.send_turn_end", new_callable=AsyncMock):
                            with patch("src.core.orchestrator.send_token_update", new_callable=AsyncMock):
                                with patch("src.core.orchestrator.AsyncSessionLocal") as mock_session_cls:
                                    mock_db = AsyncMock()
                                    mock_session_cls.return_value.__aenter__.return_value = mock_db
                                    mock_db.add = MagicMock()
                                    mock_db.commit = AsyncMock()

                                    with patch("src.core.orchestrator.ContextBuilder") as mock_builder:
                                        mock_builder_instance = MagicMock()
                                        mock_builder_instance.build_system_prompt.return_value = "System prompt"
                                        mock_builder.return_value = mock_builder_instance

                                        await orch._generate_persona_response("einstein", [], 1)

        # Verify persona stats updated
        assert orch.personas["einstein"].message_count == 1
        mock_turn_manager.mark_speaker_done.assert_called_once_with("einstein")


class TestOrchestratorRequestVote:
    """Tests for voting."""

    @pytest.mark.asyncio
    async def test_request_vote(self):
        """Test requesting a vote."""
        orch = Orchestrator(session_id=1)
        orch._initialized = True
        orch.personas = {"einstein": MagicMock()}

        mock_consensus = MagicMock()
        mock_consensus.collect_votes = AsyncMock(return_value=[])
        mock_consensus.analyze_votes = AsyncMock(return_value={
            "consensus_reached": True,
            "agreement_score": 1.0,
        })
        orch.consensus_engine = mock_consensus

        with patch("src.core.orchestrator.ws_manager") as mock_ws:
            mock_ws.broadcast = AsyncMock()
            await orch.request_vote("Should we use TDD?")

        assert orch.state == OrchestratorState.RUNNING
        mock_consensus.collect_votes.assert_called_once()
        mock_consensus.analyze_votes.assert_called_once()


class TestOrchestratorGetConversationHistory:
    """Tests for getting conversation history."""

    @pytest.mark.asyncio
    async def test_get_conversation_history(self):
        """Test getting conversation history."""
        orch = Orchestrator(session_id=1)

        mock_msg = MagicMock()
        mock_msg.role = "user"
        mock_msg.content = "Hello"

        with patch("src.core.orchestrator.AsyncSessionLocal") as mock_session_cls:
            mock_db = AsyncMock()
            mock_session_cls.return_value.__aenter__.return_value = mock_db
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = [mock_msg]
            mock_db.execute.return_value = mock_result

            history = await orch._get_conversation_history()

        assert len(history) == 1
        assert history[0] == mock_msg


class TestOrchestratorStop:
    """Tests for stopping orchestrator."""

    @pytest.mark.asyncio
    async def test_stop_updates_session_status(self):
        """Test that stop updates session status."""
        orch = Orchestrator(session_id=1)

        mock_session = MagicMock()

        with patch("src.core.orchestrator.AsyncSessionLocal") as mock_session_cls:
            mock_db = AsyncMock()
            mock_session_cls.return_value.__aenter__.return_value = mock_db
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_session
            mock_db.execute.return_value = mock_result
            mock_db.commit = AsyncMock()

            await orch.stop()

        assert orch.state == OrchestratorState.STOPPED
        mock_session.status = SessionStatus.PAUSED
