"""Tests for the request module."""
import json

import pytest
from lambda_api.context import Context
from lambda_api.request import Request
from lambda_api.types import HTTPMethod


def test_request_initialization():
    """Test request initialization."""
    # Basic initialization
    request = Request(
        method=HTTPMethod.GET,
        path="/users",
    )

    assert request.method == HTTPMethod.GET
    assert request.path == "/users"
    assert request.query_params == {}
    assert request.headers == {}
    assert request.body is None
    assert request.path_params == {}
    assert request.context is None

    # Full initialization
    context = Context()
    request = Request(
        method=HTTPMethod.POST,
        path="/users",
        query_params={"filter": "active"},
        headers={"Content-Type": "application/json"},
        body={"name": "Test User"},
        path_params={"id": "123"},
        raw_event={"source": "test"},
        context=context,
    )

    assert request.method == HTTPMethod.POST
    assert request.path == "/users"
    assert request.query_params == {"filter": "active"}
    assert request.headers == {"Content-Type": "application/json"}
    assert request.body == {"name": "Test User"}
    assert request.path_params == {"id": "123"}
    assert request.raw_event == {"source": "test"}
    assert request.context is context


def test_request_from_event_minimal():
    """Test creating request from minimal event."""
    event = {"httpMethod": "GET", "path": "/users"}

    request = Request.from_event(event)

    assert request.method == HTTPMethod.GET
    assert request.path == "/users"
    assert request.query_params == {}
    assert request.headers == {}
    assert request.body is None
    assert request.path_params == {}
    assert isinstance(request.context, Context)


def test_request_from_event_complete():
    """Test creating request from complete event."""
    event = {
        "httpMethod": "POST",
        "path": "/users",
        "queryStringParameters": {"filter": "active"},
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"name": "Test User"}),
        "pathParameters": {"id": "123"},
    }

    request = Request.from_event(event)

    assert request.method == HTTPMethod.POST
    assert request.path == "/users"
    assert request.query_params == {"filter": "active"}
    assert request.headers == {"Content-Type": "application/json"}
    assert request.body == {"name": "Test User"}
    assert request.path_params == {"id": "123"}
    assert isinstance(request.context, Context)
    assert request.context.path_params == {"id": "123"}


def test_request_from_event_with_context():
    """Test creating request with existing context."""
    event = {"httpMethod": "GET", "path": "/users/123", "pathParameters": {"id": "123"}}

    context = Context()
    request = Request.from_event(event, context)

    assert request.context is context
    assert context.request is request
    assert context.path_params == {"id": "123"}


def test_request_param():
    """Test request param method."""
    request = Request(
        method=HTTPMethod.GET,
        path="/users",
        query_params={"filter": "active", "page": "1"},
        body={"name": "Test User", "email": "test@example.com"},
        path_params={"id": "123"},
    )

    # Get from path params
    assert request.param("id") == "123"

    # Get from query params
    assert request.param("filter") == "active"
    assert request.param("page") == "1"

    # Get from body
    assert request.param("name") == "Test User"
    assert request.param("email") == "test@example.com"

    # Priority: path_params > query_params > body
    request.path_params["filter"] = "path_filter"
    request.query_params["filter"] = "query_filter"
    request.body["filter"] = "body_filter"

    assert request.param("filter") == "path_filter"

    # Default value
    assert request.param("missing") is None
    assert request.param("missing", "default") == "default"


def test_request_from_event_body_parsing():
    """Test body parsing from event."""
    # JSON body
    event = {
        "httpMethod": "POST",
        "path": "/users",
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"name": "Test User"}),
    }

    request = Request.from_event(event)
    assert request.body == {"name": "Test User"}

    # Non-JSON body
    event = {
        "httpMethod": "POST",
        "path": "/users",
        "headers": {"Content-Type": "text/plain"},
        "body": "Hello, world!",
    }

    request = Request.from_event(event)
    assert request.body == "Hello, world!"

    # Invalid JSON body should be kept as string
    event = {
        "httpMethod": "POST",
        "path": "/users",
        "headers": {"Content-Type": "application/json"},
        "body": "Not valid JSON",
    }

    request = Request.from_event(event)
    assert request.body == "Not valid JSON"
