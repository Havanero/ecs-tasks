"""Tests for the views module."""
from unittest.mock import AsyncMock, patch

import pytest
from lambda_api.request import Request
from lambda_api.response import Response
from lambda_api.types import HTTPMethod, HTTPStatus
from lambda_api.views import ResourceView, View


class TestView(View):
    """Test view class."""

    path = "/test"
    methods = [HTTPMethod.GET, HTTPMethod.POST]

    async def get(self, request):
        """Handle GET request."""
        return {"method": "get"}

    async def post(self, request):
        """Handle POST request."""
        return {"method": "post"}


class TestResourceView(ResourceView):
    """Test resource view class."""

    path = "/resources/{id}"

    async def get(self, request):
        """Handle GET request."""
        return {"id": request.param("id"), "method": "get"}

    async def put(self, request):
        """Handle PUT request."""
        return {"id": request.param("id"), "method": "put"}


@pytest.mark.asyncio
async def test_view_dispatch_get():
    """Test view dispatch method with GET request."""
    view = TestView()
    request = Request(method=HTTPMethod.GET, path="/test")

    result = await view.dispatch(request)
    assert result == {"method": "get"}


@pytest.mark.asyncio
async def test_view_dispatch_post():
    """Test view dispatch method with POST request."""
    view = TestView()
    request = Request(method=HTTPMethod.POST, path="/test")

    result = await view.dispatch(request)
    assert result == {"method": "post"}


@pytest.mark.asyncio
async def test_view_dispatch_method_not_allowed():
    """Test view dispatch method with method not allowed."""
    view = TestView()
    request = Request(method=HTTPMethod.PUT, path="/test")

    result = await view.dispatch(request)
    assert isinstance(result, Response)
    assert result.status == HTTPStatus.METHOD_NOT_ALLOWED
    assert result.body == {"error": "Method not allowed"}
    assert "Allow" in result.headers
    assert result.headers["Allow"] == "GET, POST"


@pytest.mark.asyncio
async def test_view_as_view():
    """Test view as_view class method."""
    # Get view function
    view_func = TestView.as_view()

    # Check function metadata
    assert view_func.__name__ == "TestView"
    assert view_func.__doc__ == "Test view class."

    # Test GET request
    request = Request(method=HTTPMethod.GET, path="/test")
    result = await view_func(request)
    assert result == {"method": "get"}

    # Test POST request
    request = Request(method=HTTPMethod.POST, path="/test")
    result = await view_func(request)
    assert result == {"method": "post"}


@pytest.mark.asyncio
async def test_resource_view_get():
    """Test resource view get method."""
    view = TestResourceView()
    request = Request(
        method=HTTPMethod.GET, path="/resources/123", path_params={"id": "123"}
    )

    result = await view.dispatch(request)
    assert result == {"id": "123", "method": "get"}


@pytest.mark.asyncio
async def test_resource_view_put():
    """Test resource view put method."""
    view = TestResourceView()
    request = Request(
        method=HTTPMethod.PUT, path="/resources/123", path_params={"id": "123"}
    )

    result = await view.dispatch(request)
    assert result == {"id": "123", "method": "put"}


@pytest.mark.asyncio
async def test_resource_view_method_not_implemented():
    """Test resource view method not implemented."""
    view = TestResourceView()
    request = Request(
        method=HTTPMethod.DELETE, path="/resources/123", path_params={"id": "123"}
    )

    with pytest.raises(NotImplementedError) as excinfo:
        await view.dispatch(request)

    assert "Method DELETE not implemented" in str(excinfo.value)


@pytest.mark.asyncio
async def test_resource_view_as_view():
    """Test resource view as_view class method."""
    # Get view function
    view_func = TestResourceView.as_view()

    # Test with path parameters
    request = Request(
        method=HTTPMethod.GET, path="/resources/123", path_params={"id": "123"}
    )

    result = await view_func(request)
    assert result == {"id": "123", "method": "get"}
