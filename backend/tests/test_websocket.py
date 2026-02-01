"""Tests for WebSocket handler."""

import pytest
import json
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime
from src.api.websocket.chat_handler import (
    WSEvent,
    WSEventType,
    ConnectionManager,
    manager,
    send_persona_thinking,
    send_persona_chunk,
    send_persona_done,
    send_token_update,
    send_turn_start,
    send_turn_end,
    handle_event,
    process_user_message,
    change_session_phase,
)
from src.db.models import SessionPhase


class TestWSEventType:
    """Tests for WSEventType enum."""

    def test_connection_events(self):
        """Test connection event types."""
        assert WSEventType.CONNECTED == "connected"
        assert WSEventType.DISCONNECTED == "disconnected"
        assert WSEventType.ERROR == "error"

    def test_user_events(self):
        """Test user event types."""
        assert WSEventType.USER_MESSAGE == "user_message"
        assert WSEventType.START_DISCUSSION == "start_discussion"
        assert WSEventType.PAUSE_DISCUSSION == "pause_discussion"
        assert WSEventType.RESUME_DISCUSSION == "resume_discussion"
        assert WSEventType.STOP_DISCUSSION == "stop_discussion"
        assert WSEventType.CHANGE_PHASE == "change_phase"
        assert WSEventType.VOTE_REQUEST == "vote_request"

    def test_agent_events(self):
        """Test agent event types."""
        assert WSEventType.PERSONA_THINKING == "persona_thinking"
        assert WSEventType.PERSONA_CHUNK == "persona_chunk"
        assert WSEventType.PERSONA_DONE == "persona_done"
        assert WSEventType.PERSONA_ERROR == "persona_error"

    def test_turn_events(self):
        """Test turn event types."""
        assert WSEventType.TURN_START == "turn_start"
        assert WSEventType.TURN_END == "turn_end"
        assert WSEventType.SPEAKER_QUEUE == "speaker_queue"

    def test_consensus_events(self):
        """Test consensus event types."""
        assert WSEventType.CONSENSUS_UPDATE == "consensus_update"
        assert WSEventType.VOTE_RECEIVED == "vote_received"
        assert WSEventType.VOTE_COMPLETE == "vote_complete"

    def test_metrics_events(self):
        """Test metrics event types."""
        assert WSEventType.TOKEN_UPDATE == "token_update"
        assert WSEventType.BUDGET_WARNING == "budget_warning"

    def test_session_events(self):
        """Test session event types."""
        assert WSEventType.PHASE_CHANGE == "phase_change"
        assert WSEventType.SESSION_UPDATE == "session_update"


class TestWSEvent:
    """Tests for WSEvent dataclass."""

    def test_create_ws_event(self):
        """Test creating a WSEvent."""
        event = WSEvent(
            type=WSEventType.CONNECTED,
            data={"session_id": 1},
        )
        assert event.type == WSEventType.CONNECTED
        assert event.data == {"session_id": 1}

    def test_ws_event_default_data(self):
        """Test WSEvent with default data."""
        event = WSEvent(type=WSEventType.ERROR)
        assert event.data == {}

    def test_ws_event_timestamp(self):
        """Test WSEvent has timestamp."""
        event = WSEvent(type=WSEventType.CONNECTED)
        assert event.timestamp is not None

    def test_ws_event_to_json(self):
        """Test converting WSEvent to JSON."""
        event = WSEvent(
            type=WSEventType.USER_MESSAGE,
            data={"content": "Hello"},
        )
        json_str = event.to_json()
        parsed = json.loads(json_str)
        assert parsed["type"] == "user_message"
        assert parsed["data"]["content"] == "Hello"
        assert "timestamp" in parsed


class TestConnectionManager:
    """Tests for ConnectionManager class."""

    def test_create_connection_manager(self):
        """Test creating a ConnectionManager."""
        cm = ConnectionManager()
        assert cm.active_connections == {}
        assert cm.discussion_states == {}

    @pytest.mark.asyncio
    async def test_connect(self):
        """Test connecting a WebSocket."""
        cm = ConnectionManager()
        mock_ws = AsyncMock()

        await cm.connect(mock_ws, session_id=1)

        assert 1 in cm.active_connections
        assert mock_ws in cm.active_connections[1]
        mock_ws.accept.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_multiple(self):
        """Test connecting multiple WebSockets to same session."""
        cm = ConnectionManager()
        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()

        await cm.connect(mock_ws1, session_id=1)
        await cm.connect(mock_ws2, session_id=1)

        assert len(cm.active_connections[1]) == 2

    def test_disconnect(self):
        """Test disconnecting a WebSocket."""
        cm = ConnectionManager()
        mock_ws = MagicMock()
        cm.active_connections[1] = {mock_ws}

        cm.disconnect(mock_ws, session_id=1)

        assert 1 not in cm.active_connections

    def test_disconnect_one_of_many(self):
        """Test disconnecting one WebSocket from session with multiple."""
        cm = ConnectionManager()
        mock_ws1 = MagicMock()
        mock_ws2 = MagicMock()
        cm.active_connections[1] = {mock_ws1, mock_ws2}

        cm.disconnect(mock_ws1, session_id=1)

        assert 1 in cm.active_connections
        assert mock_ws2 in cm.active_connections[1]

    def test_disconnect_nonexistent(self):
        """Test disconnecting from nonexistent session."""
        cm = ConnectionManager()
        mock_ws = MagicMock()

        # Should not raise
        cm.disconnect(mock_ws, session_id=999)

    @pytest.mark.asyncio
    async def test_send_personal(self):
        """Test sending to specific connection."""
        cm = ConnectionManager()
        mock_ws = AsyncMock()
        event = WSEvent(type=WSEventType.CONNECTED, data={"test": True})

        await cm.send_personal(mock_ws, event)

        mock_ws.send_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_personal_handles_error(self):
        """Test send_personal handles errors gracefully."""
        cm = ConnectionManager()
        mock_ws = AsyncMock()
        mock_ws.send_text.side_effect = Exception("Connection closed")

        # Should not raise
        await cm.send_personal(mock_ws, WSEvent(type=WSEventType.ERROR))

    @pytest.mark.asyncio
    async def test_broadcast(self):
        """Test broadcasting to all connections in session."""
        cm = ConnectionManager()
        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()
        cm.active_connections[1] = {mock_ws1, mock_ws2}

        event = WSEvent(type=WSEventType.USER_MESSAGE, data={"content": "Hello"})
        await cm.broadcast(1, event)

        mock_ws1.send_text.assert_called_once()
        mock_ws2.send_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_no_connections(self):
        """Test broadcast with no connections."""
        cm = ConnectionManager()

        # Should not raise
        await cm.broadcast(999, WSEvent(type=WSEventType.ERROR))

    @pytest.mark.asyncio
    async def test_broadcast_cleans_disconnected(self):
        """Test broadcast removes disconnected clients."""
        cm = ConnectionManager()
        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()
        mock_ws2.send_text.side_effect = Exception("Disconnected")
        cm.active_connections[1] = {mock_ws1, mock_ws2}

        await cm.broadcast(1, WSEvent(type=WSEventType.USER_MESSAGE))

        # Disconnected client should be removed
        assert mock_ws1 in cm.active_connections[1]
        assert mock_ws2 not in cm.active_connections[1]


class TestGlobalManager:
    """Tests for global connection manager."""

    def test_global_manager_exists(self):
        """Test global manager is initialized."""
        assert manager is not None
        assert isinstance(manager, ConnectionManager)


class TestHelperFunctions:
    """Tests for helper broadcast functions."""

    @pytest.mark.asyncio
    async def test_send_persona_thinking(self):
        """Test send_persona_thinking."""
        with patch.object(manager, "broadcast", new_callable=AsyncMock) as mock_broadcast:
            await send_persona_thinking(1, "einstein")

            mock_broadcast.assert_called_once()
            call_args = mock_broadcast.call_args
            assert call_args[0][0] == 1  # session_id
            event = call_args[0][1]
            assert event.type == WSEventType.PERSONA_THINKING
            assert event.data["persona_name"] == "einstein"

    @pytest.mark.asyncio
    async def test_send_persona_chunk(self):
        """Test send_persona_chunk."""
        with patch.object(manager, "broadcast", new_callable=AsyncMock) as mock_broadcast:
            await send_persona_chunk(1, "einstein", "Hello ")

            mock_broadcast.assert_called_once()
            event = mock_broadcast.call_args[0][1]
            assert event.type == WSEventType.PERSONA_CHUNK
            assert event.data["chunk"] == "Hello "

    @pytest.mark.asyncio
    async def test_send_persona_done(self):
        """Test send_persona_done."""
        with patch.object(manager, "broadcast", new_callable=AsyncMock) as mock_broadcast:
            await send_persona_done(
                session_id=1,
                persona_name="einstein",
                full_content="Hello there!",
                input_tokens=100,
                output_tokens=50,
            )

            mock_broadcast.assert_called_once()
            event = mock_broadcast.call_args[0][1]
            assert event.type == WSEventType.PERSONA_DONE
            assert event.data["content"] == "Hello there!"
            assert event.data["input_tokens"] == 100
            assert event.data["output_tokens"] == 50

    @pytest.mark.asyncio
    async def test_send_token_update(self):
        """Test send_token_update."""
        with patch.object(manager, "broadcast", new_callable=AsyncMock) as mock_broadcast:
            usage = {
                "persona_name": "einstein",
                "input_tokens": 100,
                "output_tokens": 50,
                "cost": 0.005,
            }
            await send_token_update(1, usage)

            mock_broadcast.assert_called_once()
            event = mock_broadcast.call_args[0][1]
            assert event.type == WSEventType.TOKEN_UPDATE
            assert event.data == usage

    @pytest.mark.asyncio
    async def test_send_turn_start(self):
        """Test send_turn_start."""
        with patch.object(manager, "broadcast", new_callable=AsyncMock) as mock_broadcast:
            await send_turn_start(1, "einstein", 5)

            mock_broadcast.assert_called_once()
            event = mock_broadcast.call_args[0][1]
            assert event.type == WSEventType.TURN_START
            assert event.data["persona_name"] == "einstein"
            assert event.data["turn_number"] == 5

    @pytest.mark.asyncio
    async def test_send_turn_end(self):
        """Test send_turn_end."""
        with patch.object(manager, "broadcast", new_callable=AsyncMock) as mock_broadcast:
            await send_turn_end(1, "einstein", 5)

            mock_broadcast.assert_called_once()
            event = mock_broadcast.call_args[0][1]
            assert event.type == WSEventType.TURN_END
            assert event.data["persona_name"] == "einstein"
            assert event.data["turn_number"] == 5


class TestHandleEvent:
    """Tests for handle_event function."""

    @pytest.mark.asyncio
    async def test_handle_user_message(self):
        """Test handling user message event."""
        mock_ws = AsyncMock()

        with patch("src.api.websocket.chat_handler.process_user_message", new_callable=AsyncMock) as mock_process:
            await handle_event(
                mock_ws,
                session_id=1,
                event_type="user_message",
                event_data={"content": "Hello"}
            )

            mock_process.assert_called_once_with(1, "Hello")

    @pytest.mark.asyncio
    async def test_handle_user_message_empty_content(self):
        """Test handling user message with empty content."""
        mock_ws = AsyncMock()

        with patch("src.api.websocket.chat_handler.process_user_message", new_callable=AsyncMock) as mock_process:
            await handle_event(
                mock_ws,
                session_id=1,
                event_type="user_message",
                event_data={"content": ""}
            )

            # Should not process empty messages
            mock_process.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_start_discussion(self):
        """Test handling start discussion event."""
        mock_ws = AsyncMock()
        mock_orchestrator = MagicMock()
        mock_orchestrator.start_discussion = AsyncMock()

        with patch("src.core.orchestrator.get_orchestrator", return_value=mock_orchestrator):
            await handle_event(
                mock_ws,
                session_id=1,
                event_type="start_discussion",
                event_data={}
            )

            mock_orchestrator.start_discussion.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_pause_discussion(self):
        """Test handling pause discussion event."""
        mock_ws = AsyncMock()
        mock_orchestrator = MagicMock()
        mock_orchestrator.pause = AsyncMock()

        with patch("src.core.orchestrator.get_orchestrator", return_value=mock_orchestrator):
            await handle_event(
                mock_ws,
                session_id=1,
                event_type="pause_discussion",
                event_data={}
            )

            mock_orchestrator.pause.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_resume_discussion(self):
        """Test handling resume discussion event."""
        mock_ws = AsyncMock()
        mock_orchestrator = MagicMock()
        mock_orchestrator.resume = AsyncMock()

        with patch("src.core.orchestrator.get_orchestrator", return_value=mock_orchestrator):
            await handle_event(
                mock_ws,
                session_id=1,
                event_type="resume_discussion",
                event_data={}
            )

            mock_orchestrator.resume.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_stop_discussion(self):
        """Test handling stop discussion event."""
        mock_ws = AsyncMock()
        mock_orchestrator = MagicMock()
        mock_orchestrator.stop = AsyncMock()

        with patch("src.core.orchestrator.get_orchestrator", return_value=mock_orchestrator):
            await handle_event(
                mock_ws,
                session_id=1,
                event_type="stop_discussion",
                event_data={}
            )

            mock_orchestrator.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_change_phase(self):
        """Test handling change phase event."""
        mock_ws = AsyncMock()

        with patch("src.api.websocket.chat_handler.change_session_phase", new_callable=AsyncMock) as mock_change:
            await handle_event(
                mock_ws,
                session_id=1,
                event_type="change_phase",
                event_data={"phase": "ideation"}
            )

            mock_change.assert_called_once_with(1, SessionPhase.IDEATION)

    @pytest.mark.asyncio
    async def test_handle_change_phase_no_phase(self):
        """Test handling change phase with no phase specified."""
        mock_ws = AsyncMock()

        with patch("src.api.websocket.chat_handler.change_session_phase", new_callable=AsyncMock) as mock_change:
            await handle_event(
                mock_ws,
                session_id=1,
                event_type="change_phase",
                event_data={}
            )

            # Should not change phase without a phase specified
            mock_change.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_vote_request(self):
        """Test handling vote request event."""
        mock_ws = AsyncMock()
        mock_orchestrator = MagicMock()
        mock_orchestrator.request_vote = AsyncMock()

        with patch("src.core.orchestrator.get_orchestrator", return_value=mock_orchestrator):
            await handle_event(
                mock_ws,
                session_id=1,
                event_type="vote_request",
                event_data={"proposal": "Use TDD"}
            )

            mock_orchestrator.request_vote.assert_called_once_with("Use TDD")

    @pytest.mark.asyncio
    async def test_handle_vote_request_no_proposal(self):
        """Test handling vote request with no proposal."""
        mock_ws = AsyncMock()
        mock_orchestrator = MagicMock()
        mock_orchestrator.request_vote = AsyncMock()

        with patch("src.core.orchestrator.get_orchestrator", return_value=mock_orchestrator):
            await handle_event(
                mock_ws,
                session_id=1,
                event_type="vote_request",
                event_data={}
            )

            # Should not request vote without proposal
            mock_orchestrator.request_vote.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_unknown_event(self):
        """Test handling unknown event type."""
        mock_ws = AsyncMock()

        with patch.object(manager, "send_personal", new_callable=AsyncMock) as mock_send:
            await handle_event(
                mock_ws,
                session_id=1,
                event_type="unknown_event",
                event_data={}
            )

            mock_send.assert_called_once()
            event = mock_send.call_args[0][1]
            assert event.type == WSEventType.ERROR
            assert "Unknown event type" in event.data["message"]

    @pytest.mark.asyncio
    async def test_handle_event_error(self):
        """Test handling event that raises an error."""
        mock_ws = AsyncMock()

        with patch("src.core.orchestrator.get_orchestrator", side_effect=Exception("Test error")):
            with patch.object(manager, "send_personal", new_callable=AsyncMock) as mock_send:
                await handle_event(
                    mock_ws,
                    session_id=1,
                    event_type="start_discussion",
                    event_data={}
                )

                mock_send.assert_called_once()
                event = mock_send.call_args[0][1]
                assert event.type == WSEventType.ERROR


class TestProcessUserMessage:
    """Tests for process_user_message function."""

    @pytest.mark.asyncio
    async def test_process_user_message_no_session(self):
        """Test processing message when session doesn't exist."""
        with patch("src.api.websocket.chat_handler.AsyncSessionLocal") as mock_session_cls:
            mock_db = AsyncMock()
            mock_session_cls.return_value.__aenter__.return_value = mock_db

            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_db.execute.return_value = mock_result

            # Should return early without error
            await process_user_message(999, "Hello")

    @pytest.mark.asyncio
    async def test_process_user_message_with_session(self):
        """Test processing message with existing session."""
        mock_session = MagicMock()
        mock_session.id = 1
        mock_session.phase = SessionPhase.DISCOVERY

        with patch("src.api.websocket.chat_handler.AsyncSessionLocal") as mock_session_cls:
            mock_db = AsyncMock()
            mock_session_cls.return_value.__aenter__.return_value = mock_db

            # First execute returns session, second returns last message
            mock_session_result = MagicMock()
            mock_session_result.scalar_one_or_none.return_value = mock_session

            mock_msg_result = MagicMock()
            mock_msg_result.scalar_one_or_none.return_value = None

            mock_db.execute = AsyncMock(side_effect=[mock_session_result, mock_msg_result])
            mock_db.add = MagicMock()
            mock_db.commit = AsyncMock()

            with patch.object(manager, "broadcast", new_callable=AsyncMock):
                mock_orchestrator = MagicMock()
                mock_orchestrator.process_user_message = AsyncMock()

                with patch("src.core.orchestrator.get_orchestrator", return_value=mock_orchestrator):
                    await process_user_message(1, "Hello")

                    mock_orchestrator.process_user_message.assert_called_once_with("Hello", 1)


class TestChangeSessionPhase:
    """Tests for change_session_phase function."""

    @pytest.mark.asyncio
    async def test_change_phase_no_session(self):
        """Test changing phase when session doesn't exist."""
        with patch("src.api.websocket.chat_handler.AsyncSessionLocal") as mock_session_cls:
            mock_db = AsyncMock()
            mock_session_cls.return_value.__aenter__.return_value = mock_db

            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_db.execute = AsyncMock(return_value=mock_result)

            # Should return early without error
            await change_session_phase(999, SessionPhase.IDEATION)

    @pytest.mark.asyncio
    async def test_change_phase_with_session(self):
        """Test changing phase with existing session."""
        mock_session = MagicMock()
        mock_session.id = 1
        mock_session.phase = SessionPhase.DISCOVERY
        mock_session.version = 1

        with patch("src.api.websocket.chat_handler.AsyncSessionLocal") as mock_session_cls:
            mock_db = AsyncMock()
            mock_session_cls.return_value.__aenter__.return_value = mock_db

            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_session
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_db.add = MagicMock()
            mock_db.commit = AsyncMock()

            with patch.object(manager, "broadcast", new_callable=AsyncMock) as mock_broadcast:
                await change_session_phase(1, SessionPhase.IDEATION)

                # Session should be updated
                assert mock_session.phase == SessionPhase.IDEATION
                assert mock_session.version == 2

                # Audit log should be added
                mock_db.add.assert_called()

                # Broadcast should be called
                mock_broadcast.assert_called_once()
                event = mock_broadcast.call_args[0][1]
                assert event.type == WSEventType.PHASE_CHANGE
                assert event.data["new_phase"] == "ideation"
