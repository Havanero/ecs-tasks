"""Tests for the events module."""
from unittest.mock import AsyncMock, Mock

import pytest
from lambda_api.context import Context
from lambda_api.events import Event, EventEmitter
from lambda_api.types import EventType


def test_event_initialization():
    """Test event initialization."""
    context = Context()

    # Basic initialization
    event = Event(type=EventType.REQUEST_RECEIVED, context=context)

    assert event.type == EventType.REQUEST_RECEIVED
    assert event.context is context
    assert event.data == {}

    # With data
    event = Event(type=EventType.ERROR, context=context, data={"error": "Test error"})

    assert event.type == EventType.ERROR
    assert event.context is context
    assert event.data == {"error": "Test error"}


@pytest.mark.asyncio
async def test_event_emitter_initialization():
    """Test event emitter initialization."""
    emitter = EventEmitter()
    assert emitter.handlers == {}


@pytest.mark.asyncio
async def test_event_emitter_on():
    """Test event emitter on method."""
    emitter = EventEmitter()
    handler = AsyncMock()

    # Register handler
    emitter.on(EventType.REQUEST_RECEIVED, handler)

    # Verify handler was registered
    assert EventType.REQUEST_RECEIVED in emitter.handlers
    assert handler in emitter.handlers[EventType.REQUEST_RECEIVED]

    # Register another handler for same event
    handler2 = AsyncMock()
    emitter.on(EventType.REQUEST_RECEIVED, handler2)

    assert len(emitter.handlers[EventType.REQUEST_RECEIVED]) == 2
    assert handler2 in emitter.handlers[EventType.REQUEST_RECEIVED]

    # Register handler for different event
    handler3 = AsyncMock()
    emitter.on(EventType.ERROR, handler3)

    assert EventType.ERROR in emitter.handlers
    assert handler3 in emitter.handlers[EventType.ERROR]


@pytest.mark.asyncio
async def test_event_emitter_emit():
    """Test event emitter emit method."""
    emitter = EventEmitter()

    # Create mock handlers
    handler1 = AsyncMock()
    handler2 = AsyncMock()
    handler3 = AsyncMock()

    # Register handlers
    emitter.on(EventType.REQUEST_RECEIVED, handler1)
    emitter.on(EventType.REQUEST_RECEIVED, handler2)
    emitter.on(EventType.ERROR, handler3)

    # Create event
    context = Context()
    event = Event(
        type=EventType.REQUEST_RECEIVED, context=context, data={"test": "data"}
    )

    # Emit event
    await emitter.emit(event)

    # Verify handlers were called
    handler1.assert_called_once_with(event)
    handler2.assert_called_once_with(event)
    handler3.assert_not_called()

    # Emit event for different type
    error_event = Event(
        type=EventType.ERROR, context=context, data={"error": "Test error"}
    )

    # Reset mocks
    handler1.reset_mock()
    handler2.reset_mock()
    handler3.reset_mock()

    # Emit error event
    await emitter.emit(error_event)

    # Verify only error handler was called
    handler1.assert_not_called()
    handler2.assert_not_called()
    handler3.assert_called_once_with(error_event)


@pytest.mark.asyncio
async def test_event_emitter_emit_no_handlers():
    """Test event emitter emit method with no handlers."""
    emitter = EventEmitter()

    # Create event for type with no handlers
    context = Context()
    event = Event(type=EventType.RESPONSE_READY, context=context)

    # Should not raise exception
    await emitter.emit(event)
