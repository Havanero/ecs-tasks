"""Tests for the API class."""
import json
from unittest.mock import AsyncMock, Mock, patch

import pytest
from lambda_api.api import API, create_handler
from lambda_api.context import Context
from lambda_api.events import Event
from lambda_api.request import Request
from lambda_api.response import Response
from lambda_api.types import (EventType, HTTPMethod, HTTPStatus,
                              MethodNotAllowedError)
from lambda_api.views import ResourceView, View


@pytest.mark.asyncio
async def test_api_initialization():
    """Test API initialization."""
    # Default initialization
    api = API()
    assert api.prefix == ""
    assert api.logger is None
    assert hasattr(api, "events")
    assert hasattr(api, "middleware_manager")

    # With prefix and logger
    logger = Mock()
    api = API(prefix="/api", logger=logger)
    assert api.prefix == "/api"
    assert api.logger is logger


@pytest.mark.asyncio
async def test_api_middleware():
    """Test API middleware method."""
    api = API()

    # Create middleware
    async def test_middleware(request, context, next_middleware):
        context.set("middleware_called", True)
        return await next_middleware()

    # Register middleware
    result = api.middleware(test_middleware)

    # Should return the middleware
    assert result is test_middleware

    # Should add middleware to manager
    assert len(api.middleware_manager.middlewares) == 1
    assert api.middleware_manager.middlewares[0] is test_middleware


@pytest.mark.asyncio
async def test_api_on():
    """Test API on method."""
    api = API()

    # Create event handler
    async def test_handler(event):
        pass

    # Register event handler
    decorator = api.on(EventType.REQUEST_RECEIVED)
    result = decorator(test_handler)

    # Should return the handler
    assert result is test_handler

    # Should register handler with event emitter
    assert EventType.REQUEST_RECEIVED in api.events.handlers
    assert test_handler in api.events.handlers[EventType.REQUEST_RECEIVED]


@pytest.mark.asyncio
async def test_api_routing_methods():
    """Test API routing methods."""
    api = API()

    # Test route method
    @api.route("/test", methods=[HTTPMethod.GET, HTTPMethod.POST])
    async def test_handler(request):
        return {"success": True}

    assert "/test" in api.routes
    assert HTTPMethod.GET in api.routes["/test"]
    assert HTTPMethod.POST in api.routes["/test"]

    # Test method-specific decorators
    @api.get("/get")
    async def get_handler(request):
        return {"method": "get"}

    @api.post("/post")
    async def post_handler(request):
        return {"method": "post"}

    @api.put("/put")
    async def put_handler(request):
        return {"method": "put"}

    @api.delete("/delete")
    async def delete_handler(request):
        return {"method": "delete"}

    @api.patch("/patch")
    async def patch_handler(request):
        return {"method": "patch"}

    assert "/get" in api.routes and HTTPMethod.GET in api.routes["/get"]
    assert "/post" in api.routes and HTTPMethod.POST in api.routes["/post"]
    assert "/put" in api.routes and HTTPMethod.PUT in api.routes["/put"]
    assert "/delete" in api.routes and HTTPMethod.DELETE in api.routes["/delete"]
    assert "/patch" in api.routes and HTTPMethod.PATCH in api.routes["/patch"]


# Test class for testing register_view method
class TestView(View):
    path = "/view-test"
    methods = [HTTPMethod.GET]

    async def get(self, request):
        return {"view": "test"}


@pytest.mark.asyncio
async def test_api_register_view():
    """Test API register_view method."""
    api = API()

    # Register view
    result = api.register_view(TestView)

    # Should return the view class
    assert result is TestView

    # Should register route
    assert "/view-test" in api.routes
    assert HTTPMethod.GET in api.routes["/view-test"]

    # Test the registered handler
    request = Request(method=HTTPMethod.GET, path="/view-test")
    response = await api.routes["/view-test"][HTTPMethod.GET](request)
    assert response == {"view": "test"}


@pytest.mark.asyncio
async def test_api_dispatch():
    """Test API dispatch method."""
    api = API()
    logger = Mock()
    api.logger = logger

    # Register route handler
    @api.get("/test")
    async def test_handler(request):
        return {"success": True}

    # Register event handler to verify events are emitted
    request_received_handler = AsyncMock()
    before_dispatch_handler = AsyncMock()
    after_dispatch_handler = AsyncMock()
    response_ready_handler = AsyncMock()

    api.events.on(EventType.REQUEST_RECEIVED, request_received_handler)
    api.events.on(EventType.BEFORE_DISPATCH, before_dispatch_handler)
    api.events.on(EventType.AFTER_DISPATCH, after_dispatch_handler)
    api.events.on(EventType.RESPONSE_READY, response_ready_handler)

    # Create request
    request = Request(method=HTTPMethod.GET, path="/test")

    # Dispatch request
    response = await api.dispatch(request)

    # Verify response
    assert isinstance(response, Response)
    assert response.body == {"success": True}
    assert response.status == HTTPStatus.OK

    # Verify events were emitted
    request_received_handler.assert_called_once()
    before_dispatch_handler.assert_called_once()
    after_dispatch_handler.assert_called_once()
    response_ready_handler.assert_called_once()

    # Verify logger was used
    logger.info.assert_called_with("GET /test")


@pytest.mark.asyncio
async def test_api_dispatch_not_found():
    """Test API dispatch method with non-existent route."""
    api = API()

    # Create request for non-existent route
    request = Request(method=HTTPMethod.GET, path="/not-found")

    # Dispatch request
    response = await api.dispatch(request)

    # Verify response
    assert isinstance(response, Response)
    assert response.body == {"error": "Not found"}
    assert response.status == HTTPStatus.NOT_FOUND


@pytest.mark.asyncio
async def test_api_dispatch_method_not_allowed():
    """Test API dispatch method with method not allowed."""
    api = API()

    # Register route handler
    @api.get("/test")
    async def test_handler(request):
        return {"success": True}

    # Create request with wrong method
    request = Request(method=HTTPMethod.POST, path="/test")

    # Dispatch request
    response = await api.dispatch(request)

    # Verify response
    assert isinstance(response, Response)
    assert response.body == {"error": "Method not allowed", "allowed": ["GET"]}
    assert response.status == HTTPStatus.METHOD_NOT_ALLOWED
    assert response.headers["Allow"] == "GET"


@pytest.mark.asyncio
async def test_api_handle_event_http():
    """Test API handle_event method with HTTP event."""
    api = API()

    # Register route handler
    @api.get("/test")
    async def test_handler(request):
        return {"success": True, "path_params": request.path_params}

    # Create HTTP event
    event = {
        "httpMethod": "GET",
        "path": "/test",
        "headers": {"Content-Type": "application/json"},
        "queryStringParameters": {"query": "value"},
        "pathParameters": {"param": "value"},
    }

    # Handle event
    response = await api.handle_event(event)

    # Verify response
    assert response["statusCode"] == 200
    assert json.loads(response["body"]) == {
        "success": True,
        "path_params": {"param": "value"},
    }


@pytest.mark.asyncio
async def test_api_handle_event_direct():
    """Test API handle_event method with direct invocation."""
    api = API()

    # Create direct invocation event
    event = {"action": "process", "data": {"id": 123}}

    # Handle event
    response = await api.handle_event(event)

    # Verify response
    assert response["statusCode"] == 200
    assert json.loads(response["body"]) == {
        "message": "Direct invocation",
        "event": event,
    }


@pytest.mark.asyncio
async def test_api_handle_event_with_middleware():
    """Test API handle_event method with middleware."""
    api = API()

    # Register route handler
    @api.get("/test")
    async def test_handler(request):
        return {
            "success": True,
            "middleware_ran": request.context.get("middleware_ran", False),
        }

    # Register middleware
    @api.middleware
    async def test_middleware(request, context, next_middleware):
        context.set("middleware_ran", True)
        return await next_middleware()

    # Create HTTP event
    event = {"httpMethod": "GET", "path": "/test"}

    # Handle event
    response = await api.handle_event(event)

    # Verify response
    assert response["statusCode"] == 200
    assert json.loads(response["body"]) == {"success": True, "middleware_ran": True}


@pytest.mark.asyncio
async def test_create_handler():
    """Test create_handler function."""
    api = API()

    # Register route handler
    @api.get("/test")
    async def test_handler(request):
        return {"success": True}

    # Create Lambda handler
    lambda_handler = create_handler(api)

    # Create HTTP event
    event = {"httpMethod": "GET", "path": "/test"}

    # Create mock Lambda context
    mock_context = Mock()

    # Call handler
    response = await lambda_handler(event, mock_context)

    # Verify response
    assert response["statusCode"] == 200
    assert json.loads(response["body"]) == {"success": True}
