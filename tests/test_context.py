"""Tests for the context module."""
import pytest
from lambda_api.context import Context


def test_context_initialization():
    """Test context initialization."""
    # Default initialization
    context = Context()
    assert context.request is None
    assert context.response is None
    assert context.path_params == {}
    assert context.lambda_context is None
    assert context.store == {}

    # Initialization with values
    mock_request = object()
    mock_response = object()
    mock_lambda_context = object()
    path_params = {"id": "123"}

    context = Context(
        request=mock_request,
        response=mock_response,
        path_params=path_params,
        lambda_context=mock_lambda_context,
    )

    assert context.request is mock_request
    assert context.response is mock_response
    assert context.path_params == path_params
    assert context.lambda_context is mock_lambda_context


def test_context_store():
    """Test context store operations."""
    context = Context()

    # Initially empty
    assert context.store == {}

    # Set and get value
    context.set("user_id", "123")
    assert context.get("user_id") == "123"

    # Get with default
    assert context.get("missing_key") is None
    assert context.get("missing_key", "default") == "default"

    # Multiple values
    context.set("count", 42)
    context.set("items", [1, 2, 3])

    assert context.get("count") == 42
    assert context.get("items") == [1, 2, 3]

    # Overwrite value
    context.set("user_id", "456")
    assert context.get("user_id") == "456"


def test_context_path_params():
    """Test context path parameters."""
    context = Context()

    # Add path parameters
    context.path_params["id"] = "123"
    assert context.path_params == {"id": "123"}

    # Add more path parameters
    context.path_params["action"] = "view"
    assert context.path_params == {"id": "123", "action": "view"}

    # Update path parameters
    context.path_params.update({"id": "456", "type": "user"})
    assert context.path_params == {"id": "456", "action": "view", "type": "user"}
