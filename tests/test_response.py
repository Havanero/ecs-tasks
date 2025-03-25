"""Tests for the response module."""
import json

import pytest
from lambda_api.context import Context
from lambda_api.response import Response
from lambda_api.types import HTTPStatus


def test_response_initialization():
    """Test response initialization."""
    # Default initialization
    response = Response()

    assert response.body is None
    assert response.status == HTTPStatus.OK
    assert response.headers == {"Content-Type": "application/json"}
    assert response.context is None

    # Full initialization
    context = Context()
    response = Response(
        body={"message": "Success"},
        status=HTTPStatus.CREATED,
        headers={"Content-Type": "application/json", "X-Custom": "Value"},
        context=context,
    )

    assert response.body == {"message": "Success"}
    assert response.status == HTTPStatus.CREATED
    assert response.headers == {"Content-Type": "application/json", "X-Custom": "Value"}
    assert response.context is context


def test_response_post_init():
    """Test response __post_init__ method."""
    # Should set default headers if None
    response = Response(headers=None)
    assert response.headers == {"Content-Type": "application/json"}

    # Should not overwrite existing headers
    response = Response(headers={"Content-Type": "text/plain"})
    assert response.headers == {"Content-Type": "text/plain"}


def test_response_to_dict_null_body():
    """Test response to_dict method with null body."""
    response = Response(body=None)
    result = response.to_dict()

    assert result == {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": None,
    }


def test_response_to_dict_dict_body():
    """Test response to_dict method with dict body."""
    response = Response(body={"message": "Success"})
    result = response.to_dict()

    assert result == {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"message": "Success"}),
    }

    # Verify it's valid JSON
    parsed = json.loads(result["body"])
    assert parsed == {"message": "Success"}


def test_response_to_dict_string_body():
    """Test response to_dict method with string body."""
    response = Response(body="Plain text")
    result = response.to_dict()

    assert result == {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": "Plain text",
    }


def test_response_to_dict_custom_status():
    """Test response to_dict method with custom status."""
    response = Response(body={"message": "Created"}, status=HTTPStatus.CREATED)
    result = response.to_dict()

    assert result["statusCode"] == 201


def test_response_to_dict_custom_headers():
    """Test response to_dict method with custom headers."""
    response = Response(
        body={"message": "Success"},
        headers={
            "Content-Type": "application/json",
            "X-Custom": "Value",
            "Cache-Control": "no-cache",
        },
    )
    result = response.to_dict()

    assert result["headers"] == {
        "Content-Type": "application/json",
        "X-Custom": "Value",
        "Cache-Control": "no-cache",
    }
