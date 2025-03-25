"""Tests for the types module."""
import pytest
from lambda_api.types import (EventType, HTTPMethod, HTTPStatus,
                              MethodNotAllowedError)


def test_http_method_enum():
    """Test HTTP method enum."""
    assert HTTPMethod.GET == "GET"
    assert HTTPMethod.POST == "POST"
    assert HTTPMethod.PUT == "PUT"
    assert HTTPMethod.DELETE == "DELETE"
    assert HTTPMethod.PATCH == "PATCH"
    assert HTTPMethod.OPTIONS == "OPTIONS"
    assert HTTPMethod.HEAD == "HEAD"

    # Test string comparison
    assert HTTPMethod.GET == "GET"
    assert "GET" == HTTPMethod.GET

    # Test in collection
    methods = [HTTPMethod.GET, HTTPMethod.POST]
    assert HTTPMethod.GET in methods
    assert "GET" in methods


def test_http_status_enum():
    """Test HTTP status enum."""
    assert HTTPStatus.OK == 200
    assert HTTPStatus.CREATED == 201
    assert HTTPStatus.NOT_FOUND == 404
    assert HTTPStatus.INTERNAL_SERVER_ERROR == 500

    # Test integer comparison
    assert HTTPStatus.OK == 200
    assert 200 == HTTPStatus.OK

    # Test in collection
    statuses = [HTTPStatus.OK, HTTPStatus.NOT_FOUND]
    assert HTTPStatus.OK in statuses
    assert 200 in statuses


def test_event_type_enum():
    """Test event type enum."""
    assert EventType.REQUEST_RECEIVED == "request.received"
    assert EventType.BEFORE_DISPATCH == "request.before_dispatch"
    assert EventType.AFTER_DISPATCH == "request.after_dispatch"
    assert EventType.RESPONSE_READY == "response.ready"
    assert EventType.ERROR == "error"


def test_method_not_allowed_error():
    """Test MethodNotAllowedError."""
    allowed_methods = [HTTPMethod.GET, HTTPMethod.POST]
    error = MethodNotAllowedError(allowed_methods)

    assert error.allowed_methods == allowed_methods
    assert (
        str(error)
        == "Method not allowed. Allowed methods: [HTTPMethod.GET, HTTPMethod.POST]"
    )
