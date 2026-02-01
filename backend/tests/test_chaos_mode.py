"""Tests for chaos mode module."""

import pytest
from unittest.mock import patch
from src.core.modes.chaos import ChaosEvent, ChaosMode, CHAOS_EVENTS


class TestChaosEvent:
    """Tests for ChaosEvent dataclass."""

    def test_create_chaos_event(self):
        """Test creating a ChaosEvent."""
        event = ChaosEvent(
            name="test_event",
            description="A test event",
            prompt_injection="Do something creative!",
            probability=0.2,
        )
        assert event.name == "test_event"
        assert event.description == "A test event"
        assert event.prompt_injection == "Do something creative!"
        assert event.probability == 0.2

    def test_chaos_event_default_probability(self):
        """Test ChaosEvent default probability."""
        event = ChaosEvent(
            name="test",
            description="test",
            prompt_injection="test",
        )
        assert event.probability == 0.1


class TestChaosEventsPredefined:
    """Tests for predefined CHAOS_EVENTS."""

    def test_chaos_events_exist(self):
        """Test that predefined chaos events exist."""
        assert len(CHAOS_EVENTS) > 0

    def test_devil_advocate_event(self):
        """Test devil's advocate event exists."""
        event = next((e for e in CHAOS_EVENTS if e.name == "devil_advocate"), None)
        assert event is not None
        assert "devil's advocate" in event.prompt_injection.lower()
        assert event.probability == 0.15

    def test_wild_idea_event(self):
        """Test wild idea event exists."""
        event = next((e for e in CHAOS_EVENTS if e.name == "wild_idea"), None)
        assert event is not None
        assert "creative" in event.prompt_injection.lower() or "unconventional" in event.prompt_injection.lower()

    def test_historical_parallel_event(self):
        """Test historical parallel event exists."""
        event = next((e for e in CHAOS_EVENTS if e.name == "historical_parallel"), None)
        assert event is not None
        assert "history" in event.prompt_injection.lower()

    def test_all_events_have_required_fields(self):
        """Test all events have required fields."""
        for event in CHAOS_EVENTS:
            assert event.name is not None
            assert event.description is not None
            assert event.prompt_injection is not None
            assert 0 < event.probability <= 1


class TestChaosMode:
    """Tests for ChaosMode class."""

    def test_create_chaos_mode(self):
        """Test creating a ChaosMode."""
        mode = ChaosMode()
        assert mode.enabled is True
        assert mode.intensity == 1.0
        assert len(mode.events) == len(CHAOS_EVENTS)
        assert mode.event_history == []

    def test_create_chaos_mode_disabled(self):
        """Test creating a disabled ChaosMode."""
        mode = ChaosMode(enabled=False)
        assert mode.enabled is False

    def test_create_chaos_mode_with_intensity(self):
        """Test creating ChaosMode with custom intensity."""
        mode = ChaosMode(intensity=0.5)
        assert mode.intensity == 0.5

    def test_create_chaos_mode_with_custom_events(self):
        """Test creating ChaosMode with custom events."""
        custom = [
            ChaosEvent(
                name="custom_test",
                description="Custom event",
                prompt_injection="Custom prompt",
            )
        ]
        mode = ChaosMode(custom_events=custom)
        assert len(mode.events) == len(CHAOS_EVENTS) + 1
        assert any(e.name == "custom_test" for e in mode.events)

    def test_should_inject_disabled(self):
        """Test should_inject returns False when disabled."""
        mode = ChaosMode(enabled=False)
        assert mode.should_inject(10) is False

    def test_should_inject_early_turns(self):
        """Test should_inject returns False for early turns."""
        mode = ChaosMode(enabled=True)
        assert mode.should_inject(0) is False
        assert mode.should_inject(1) is False
        assert mode.should_inject(2) is False

    def test_should_inject_later_turns(self):
        """Test should_inject can return True for later turns."""
        mode = ChaosMode(enabled=True, intensity=10.0)  # High intensity

        # Run many iterations - with high intensity, at least some should inject
        results = [mode.should_inject(10) for _ in range(100)]
        assert any(results)  # At least one should be True

    def test_should_inject_respects_intensity(self):
        """Test that intensity affects injection probability."""
        mode_low = ChaosMode(intensity=0.1)
        mode_high = ChaosMode(intensity=5.0)

        # Run many trials
        low_results = sum(mode_low.should_inject(10) for _ in range(100))
        high_results = sum(mode_high.should_inject(10) for _ in range(100))

        # High intensity should generally produce more injections
        # (statistical, but very likely with these settings)
        assert high_results >= low_results

    def test_get_injection_when_disabled(self):
        """Test get_injection returns None when disabled."""
        mode = ChaosMode(enabled=False)
        result = mode.get_injection(10)
        assert result is None

    def test_get_injection_early_turn(self):
        """Test get_injection returns None for early turns."""
        mode = ChaosMode()
        result = mode.get_injection(1)
        assert result is None

    @patch('src.core.modes.chaos.random.random')
    def test_get_injection_triggers_event(self, mock_random):
        """Test get_injection can trigger an event."""
        mode = ChaosMode(intensity=1.0)

        # First call for should_inject, second for event selection
        mock_random.side_effect = [0.0, 0.0]  # Always trigger, select first event

        result = mode.get_injection(5)
        assert result is not None
        assert len(mode.event_history) == 1

    @patch('src.core.modes.chaos.random.random')
    def test_get_injection_no_event_triggered(self, mock_random):
        """Test get_injection when no event triggered by roll."""
        mode = ChaosMode(intensity=0.01)  # Very low intensity

        # First call passes should_inject, second roll is too high
        mock_random.side_effect = [0.0, 0.99]  # Trigger check, but no event

        result = mode.get_injection(5)
        # With very low intensity, cumulative probability may not reach 0.99
        # So result should be None
        assert result is None

    def test_get_specific_injection_exists(self):
        """Test get_specific_injection for existing event."""
        mode = ChaosMode()
        result = mode.get_specific_injection("devil_advocate")
        assert result is not None
        assert "devil's advocate" in result.lower()
        assert "devil_advocate" in mode.event_history

    def test_get_specific_injection_not_exists(self):
        """Test get_specific_injection for non-existing event."""
        mode = ChaosMode()
        result = mode.get_specific_injection("nonexistent_event")
        assert result is None

    def test_add_custom_event(self):
        """Test adding a custom event."""
        mode = ChaosMode()
        initial_count = len(mode.events)

        mode.add_custom_event(
            name="new_event",
            description="New custom event",
            prompt_injection="New prompt",
            probability=0.25,
        )

        assert len(mode.events) == initial_count + 1
        added = next(e for e in mode.events if e.name == "new_event")
        assert added.probability == 0.25

    def test_get_available_events(self):
        """Test getting available events."""
        mode = ChaosMode()
        events = mode.get_available_events()

        assert len(events) == len(CHAOS_EVENTS)
        for event in events:
            assert "name" in event
            assert "description" in event
            assert "probability" in event

    def test_get_history(self):
        """Test getting event history."""
        mode = ChaosMode()
        assert mode.get_history() == []

        mode.get_specific_injection("devil_advocate")
        mode.get_specific_injection("wild_idea")

        history = mode.get_history()
        assert len(history) == 2
        assert "devil_advocate" in history
        assert "wild_idea" in history

    def test_get_history_returns_copy(self):
        """Test get_history returns a copy."""
        mode = ChaosMode()
        mode.get_specific_injection("devil_advocate")

        history = mode.get_history()
        history.append("fake_event")

        assert "fake_event" not in mode.event_history

    def test_reset(self):
        """Test resetting chaos mode."""
        mode = ChaosMode()
        mode.get_specific_injection("devil_advocate")
        mode.get_specific_injection("wild_idea")
        assert len(mode.event_history) == 2

        mode.reset()
        assert mode.event_history == []
