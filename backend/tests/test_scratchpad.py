"""Tests for the scratchpad service."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime
from src.services.scratchpad import ScratchpadService, ScratchpadEntry


class TestScratchpadEntry:
    """Tests for ScratchpadEntry dataclass."""

    def test_create_scratchpad_entry(self):
        """Test creating a ScratchpadEntry."""
        now = datetime.now()
        entry = ScratchpadEntry(
            key="test_key",
            value="test_value",
            author="einstein",
            version=1,
            created_at=now,
            updated_at=None,
        )
        assert entry.key == "test_key"
        assert entry.value == "test_value"
        assert entry.author == "einstein"
        assert entry.version == 1

    def test_scratchpad_entry_with_update(self):
        """Test ScratchpadEntry with updated_at."""
        now = datetime.now()
        entry = ScratchpadEntry(
            key="key",
            value="value",
            author=None,
            version=2,
            created_at=now,
            updated_at=now,
        )
        assert entry.updated_at is not None


class TestScratchpadService:
    """Tests for ScratchpadService class."""

    def test_create_scratchpad_service(self):
        """Test creating a ScratchpadService."""
        service = ScratchpadService(session_id=1)
        assert service.session_id == 1
        assert service._cache == {}

    @pytest.mark.asyncio
    async def test_get_from_cache(self):
        """Test getting value from cache."""
        service = ScratchpadService(session_id=1)
        now = datetime.now()
        service._cache["test_key"] = ScratchpadEntry(
            key="test_key",
            value="cached_value",
            author=None,
            version=1,
            created_at=now,
            updated_at=None,
        )

        result = await service.get("test_key")
        assert result == "cached_value"

    @pytest.mark.asyncio
    async def test_get_from_database(self):
        """Test getting value from database when not cached."""
        service = ScratchpadService(session_id=1)

        with patch("src.services.scratchpad.AsyncSessionLocal") as mock_session_cls:
            mock_session = AsyncMock()
            mock_session_cls.return_value.__aenter__.return_value = mock_session

            mock_entry = MagicMock()
            mock_entry.key = "db_key"
            mock_entry.value = "db_value"
            mock_entry.author_persona = "feynman"
            mock_entry.version = 1
            mock_entry.created_at = datetime.now()
            mock_entry.updated_at = None

            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_entry
            mock_session.execute.return_value = mock_result

            result = await service.get("db_key")
            assert result == "db_value"
            assert "db_key" in service._cache

    @pytest.mark.asyncio
    async def test_get_returns_none_for_missing_key(self):
        """Test get returns None for missing key."""
        service = ScratchpadService(session_id=1)

        with patch("src.services.scratchpad.AsyncSessionLocal") as mock_session_cls:
            mock_session = AsyncMock()
            mock_session_cls.return_value.__aenter__.return_value = mock_session

            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_session.execute.return_value = mock_result

            result = await service.get("nonexistent")
            assert result is None

    @pytest.mark.asyncio
    async def test_set_creates_new_entry(self):
        """Test setting a new value."""
        service = ScratchpadService(session_id=1)

        with patch("src.services.scratchpad.AsyncSessionLocal") as mock_session_cls:
            mock_session = AsyncMock()
            mock_session_cls.return_value.__aenter__.return_value = mock_session

            # No existing entry
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_session.execute.return_value = mock_result

            # Mock the refresh to set attributes
            async def mock_refresh(entry):
                entry.key = "new_key"
                entry.value = "new_value"
                entry.author_persona = "einstein"
                entry.version = 1
                entry.created_at = datetime.now()
                entry.updated_at = None

            mock_session.refresh = mock_refresh

            result = await service.set("new_key", "new_value", author="einstein")
            assert result.key == "new_key"
            assert result.value == "new_value"
            assert result.version == 1

    @pytest.mark.asyncio
    async def test_set_increments_version(self):
        """Test setting value increments version."""
        service = ScratchpadService(session_id=1)

        with patch("src.services.scratchpad.AsyncSessionLocal") as mock_session_cls:
            mock_session = AsyncMock()
            mock_session_cls.return_value.__aenter__.return_value = mock_session

            # Existing entry with version 3
            mock_existing = MagicMock()
            mock_existing.version = 3

            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_existing
            mock_session.execute.return_value = mock_result

            async def mock_refresh(entry):
                entry.key = "key"
                entry.value = "value"
                entry.author_persona = None
                entry.version = 4  # Incremented
                entry.created_at = datetime.now()
                entry.updated_at = None

            mock_session.refresh = mock_refresh

            result = await service.set("key", "value")
            assert result.version == 4

    @pytest.mark.asyncio
    async def test_delete(self):
        """Test deleting a key."""
        service = ScratchpadService(session_id=1)

        with patch.object(service, "set", new_callable=AsyncMock) as mock_set:
            mock_set.return_value = MagicMock()
            result = await service.delete("key_to_delete")
            mock_set.assert_called_once_with("key_to_delete", "", author="system")

    @pytest.mark.asyncio
    async def test_get_all(self):
        """Test getting all entries."""
        service = ScratchpadService(session_id=1)

        with patch("src.services.scratchpad.AsyncSessionLocal") as mock_session_cls:
            mock_session = AsyncMock()
            mock_session_cls.return_value.__aenter__.return_value = mock_session

            mock_entry1 = MagicMock(key="key1", value="value1", version=2)
            mock_entry2 = MagicMock(key="key2", value="value2", version=1)
            mock_entry3 = MagicMock(key="key1", value="old_value", version=1)  # older version

            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = [mock_entry1, mock_entry2, mock_entry3]
            mock_session.execute.return_value = mock_result

            result = await service.get_all()
            assert "key1" in result
            assert "key2" in result
            assert result["key1"] == "value1"  # Latest version

    @pytest.mark.asyncio
    async def test_get_history(self):
        """Test getting version history."""
        service = ScratchpadService(session_id=1)

        with patch("src.services.scratchpad.AsyncSessionLocal") as mock_session_cls:
            mock_session = AsyncMock()
            mock_session_cls.return_value.__aenter__.return_value = mock_session

            now = datetime.now()
            mock_entries = [
                MagicMock(key="key", value="v2", author_persona="b", version=2, created_at=now, updated_at=None),
                MagicMock(key="key", value="v1", author_persona="a", version=1, created_at=now, updated_at=None),
            ]

            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = mock_entries
            mock_session.execute.return_value = mock_result

            result = await service.get_history("key")
            assert len(result) == 2
            assert result[0].version == 2
            assert result[1].version == 1

    @pytest.mark.asyncio
    async def test_append(self):
        """Test appending to existing value."""
        service = ScratchpadService(session_id=1)

        with patch.object(service, "get", new_callable=AsyncMock) as mock_get:
            with patch.object(service, "set", new_callable=AsyncMock) as mock_set:
                mock_get.return_value = "existing"
                mock_set.return_value = MagicMock(value="existing\nnew")

                result = await service.append("key", "new", author="test")
                mock_set.assert_called_once_with("key", "existing\nnew", "test")

    @pytest.mark.asyncio
    async def test_append_to_empty(self):
        """Test appending when no existing value."""
        service = ScratchpadService(session_id=1)

        with patch.object(service, "get", new_callable=AsyncMock) as mock_get:
            with patch.object(service, "set", new_callable=AsyncMock) as mock_set:
                mock_get.return_value = None
                mock_set.return_value = MagicMock(value="new")

                await service.append("key", "new")
                mock_set.assert_called_once_with("key", "new", None)

    @pytest.mark.asyncio
    async def test_increment(self):
        """Test incrementing a numeric value."""
        service = ScratchpadService(session_id=1)

        with patch.object(service, "get", new_callable=AsyncMock) as mock_get:
            with patch.object(service, "set", new_callable=AsyncMock) as mock_set:
                mock_get.return_value = "5"
                mock_set.return_value = MagicMock(value="6")

                await service.increment("counter")
                mock_set.assert_called_once_with("counter", "6", None)

    @pytest.mark.asyncio
    async def test_increment_from_zero(self):
        """Test incrementing when no existing value."""
        service = ScratchpadService(session_id=1)

        with patch.object(service, "get", new_callable=AsyncMock) as mock_get:
            with patch.object(service, "set", new_callable=AsyncMock) as mock_set:
                mock_get.return_value = None

                await service.increment("counter", amount=5)
                mock_set.assert_called_once_with("counter", "5", None)

    @pytest.mark.asyncio
    async def test_increment_invalid_value(self):
        """Test incrementing an invalid (non-numeric) value."""
        service = ScratchpadService(session_id=1)

        with patch.object(service, "get", new_callable=AsyncMock) as mock_get:
            with patch.object(service, "set", new_callable=AsyncMock) as mock_set:
                mock_get.return_value = "not_a_number"

                await service.increment("counter")
                mock_set.assert_called_once_with("counter", "1", None)

    @pytest.mark.asyncio
    async def test_add_decision(self):
        """Test adding a decision."""
        service = ScratchpadService(session_id=1)

        with patch.object(service, "append", new_callable=AsyncMock) as mock_append:
            await service.add_decision("Use TDD", author="einstein")
            mock_append.assert_called_once_with("decisions", "- Use TDD", "einstein")

    @pytest.mark.asyncio
    async def test_add_action_item(self):
        """Test adding an action item."""
        service = ScratchpadService(session_id=1)

        with patch.object(service, "append", new_callable=AsyncMock) as mock_append:
            await service.add_action_item("Write tests", assignee="feynman", author="curie")
            mock_append.assert_called_once_with("action_items", "- [ ] Write tests (@feynman)", "curie")

    @pytest.mark.asyncio
    async def test_add_action_item_no_assignee(self):
        """Test adding an action item without assignee."""
        service = ScratchpadService(session_id=1)

        with patch.object(service, "append", new_callable=AsyncMock) as mock_append:
            await service.add_action_item("Write tests")
            mock_append.assert_called_once_with("action_items", "- [ ] Write tests", None)

    @pytest.mark.asyncio
    async def test_add_key_insight(self):
        """Test adding a key insight."""
        service = ScratchpadService(session_id=1)

        with patch.object(service, "append", new_callable=AsyncMock) as mock_append:
            await service.add_key_insight("Testing is important")
            mock_append.assert_called_once_with("key_insights", "- Testing is important", None)

    @pytest.mark.asyncio
    async def test_add_open_question(self):
        """Test adding an open question."""
        service = ScratchpadService(session_id=1)

        with patch.object(service, "append", new_callable=AsyncMock) as mock_append:
            await service.add_open_question("What framework to use?")
            mock_append.assert_called_once_with("open_questions", "- What framework to use?", None)

    @pytest.mark.asyncio
    async def test_get_summary(self):
        """Test getting summary."""
        service = ScratchpadService(session_id=1)

        with patch.object(service, "get_all", new_callable=AsyncMock) as mock_get_all:
            mock_get_all.return_value = {
                "decisions": "- Decision 1\n- Decision 2",
                "action_items": "- [ ] Item 1",
                "key_insights": "",
                "other_key": "other_value",
            }

            result = await service.get_summary()
            assert result["session_id"] == 1
            assert result["entry_count"] == 4
            assert len(result["decisions"]) == 2
            assert len(result["action_items"]) == 1

    def test_clear_cache(self):
        """Test clearing cache."""
        service = ScratchpadService(session_id=1)
        service._cache["key"] = MagicMock()
        service.clear_cache()
        assert service._cache == {}
