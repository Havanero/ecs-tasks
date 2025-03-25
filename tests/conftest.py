"""Common test fixtures and utilities."""
import json
from unittest.mock import Mock

import pytest
from lambda_api import API, Context, HTTPMethod, Request, Response


@pytest.fixture
def mock_context():
    """Create a mock context for testing."""
    return Context()


@pytest.fixture
def mock_request():
    """Create a mock request for testing."""
    return Request(
        method=HTTPMethod.GET,
        path="/test",
        headers={"Content-Type": "application/json"},
        query_params={"query": "value"},
        path_params={"id": "123"},
        body={"key": "value"},
        context=Context(),
    )


@pytest.fixture
def mock_lambda_context():
    """Create a mock Lambda context."""
    context = Mock()
    context.function_name = "test-function"
    context.function_version = "$LATEST"
    context.invoked_function_arn = (
        "arn:aws:lambda:us-east-1:123456789012:function:test-function"
    )
    context.memory_limit_in_mb = 128
    context.aws_request_id = "test-request-id"
    context.log_group_name = "/aws/lambda/test-function"
    context.log_stream_name = "2022/01/01/[$LATEST]abcdef123456"
    context.identity = None
    context.client_context = None
    context.get_remaining_time_in_millis.return_value = 3000  # 3 seconds
    return context


def create_event(
    method="GET",
    path="/test",
    headers=None,
    query_params=None,
    path_params=None,
    body=None,
):
    """Create a Lambda event for testing."""
    event = {
        "httpMethod": method,
        "path": path,
        "headers": headers or {},
    }

    if query_params:
        event["queryStringParameters"] = query_params

    if path_params:
        event["pathParameters"] = path_params

    if body:
        if isinstance(body, dict):
            event["body"] = json.dumps(body)
        else:
            event["body"] = body

    return event
