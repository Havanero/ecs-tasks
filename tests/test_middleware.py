"""Tests for the middleware module."""
from unittest.mock import AsyncMock, Mock

import pytest
from lambda_api.context import Context
from lambda_api.middleware import MiddlewareManager
from lambda_api.request import Request
from lambda_api.response import Response
from lambda_api.types import HTTPMethod


@pytest.mark.asyncio
async def test_middleware_manager_initialization():
    """Test middleware manager initialization."""
    manager = MiddlewareManager()
    assert manager.middlewares == []


@pytest.mark.asyncio
async def test_middleware_manager_add():
    """Test middleware manager add method."""
    manager = MiddlewareManager()
    middleware = AsyncMock()

    # Add middleware
    manager.add(middleware)

    assert len(manager.middlewares) == 1
    assert manager.middlewares[0] is middleware

    # Add another middleware
    middleware2 = AsyncMock()
    manager.add(middleware2)

    assert len(manager.middlewares) == 2
    assert manager.middlewares[1] is middleware2


@pytest.mark.asyncio
async def test_middleware_manager_execute_no_middleware():
    """Test middleware manager execute method with no middleware."""
    manager = MiddlewareManager()

    # Create mock handler
    handler_response = Response(body={"message": "Success"})
    handler = AsyncMock(return_value=handler_response)

    # Create request and context
    request = Request(method=HTTPMethod.GET, path="/test")
    context = Context()

    # Execute with no middleware
    response = await manager.execute(request, context, handler)

    # Handler should be called directly
    handler.assert_called_once()
    assert response is handler_response


@pytest.mark.asyncio
async def test_middleware_manager_execute_single_middleware():
    """Test middleware manager execute method with a single middleware."""
    manager = MiddlewareManager()

    # Create mock handler
    handler_response = Response(body={"message": "Success"})
    handler = AsyncMock(return_value=handler_response)

    # Create middleware that passes through
    async def middleware1(req, ctx, next_mw):
        # Add something to context
        ctx.set("middleware1_ran", True)
        # Call next middleware
        response = await next_mw()
        # Modify response
        response.headers["X-Middleware1"] = "True"
        return response

    # Add middleware
    manager.add(middleware1)

    # Create request and context
    request = Request(method=HTTPMethod.GET, path="/test")
    context = Context()

    # Execute with middleware
    response = await manager.execute(request, context, handler)

    # Handler should be called
    handler.assert_called_once()

    # Context should be modified
    assert context.get("middleware1_ran") is True

    # Response should be modified
    assert response.headers["X-Middleware1"] == "True"


@pytest.mark.asyncio
async def test_middleware_manager_execute_multiple_middleware():
    """Test middleware manager execute method with multiple middleware."""
    manager = MiddlewareManager()

    # Create mock handler
    handler_response = Response(body={"message": "Success"})
    handler = AsyncMock(return_value=handler_response)

    # Create middlewares
    middleware_calls = []

    async def middleware1(req, ctx, next_mw):
        middleware_calls.append("middleware1_before")
        ctx.set("middleware1_ran", True)
        response = await next_mw()
        middleware_calls.append("middleware1_after")
        response.headers["X-Middleware1"] = "True"
        return response

    async def middleware2(req, ctx, next_mw):
        middleware_calls.append("middleware2_before")
        ctx.set("middleware2_ran", True)
        response = await next_mw()
        middleware_calls.append("middleware2_after")
        response.headers["X-Middleware2"] = "True"
        return response

    # Add middleware in order
    manager.add(middleware1)
    manager.add(middleware2)

    # Create request and context
    request = Request(method=HTTPMethod.GET, path="/test")
    context = Context()

    # Execute with middleware
    response = await manager.execute(request, context, handler)

    # Handler should be called
    handler.assert_called_once()

    # Context should be modified by both middleware
    assert context.get("middleware1_ran") is True
    assert context.get("middleware2_ran") is True

    # Response should be modified by both middleware
    assert response.headers["X-Middleware1"] == "True"
    assert response.headers["X-Middleware2"] == "True"

    # Middleware execution order should be correct:
    # 1. middleware1 before next_mw
    # 2. middleware2 before next_mw
    # 3. handler
    # 4. middleware2 after next_mw
    # 5. middleware1 after next_mw
    assert middleware_calls == [
        "middleware1_before",
        "middleware2_before",
        "middleware2_after",
        "middleware1_after",
    ]


@pytest.mark.asyncio
async def test_middleware_manager_execute_short_circuit():
    """Test middleware manager execute method with short-circuiting middleware."""
    manager = MiddlewareManager()

    # Create mock handler that should not be called
    handler = AsyncMock()

    # Create middleware that short-circuits
    async def auth_middleware(req, ctx, next_mw):
        # Don't call next middleware, return directly
        return Response(
            body={"error": "Unauthorized"},
            status=401,
            headers={"Content-Type": "application/json"},
        )

    # Add middleware
    manager.add(auth_middleware)

    # Create request and context
    request = Request(method=HTTPMethod.GET, path="/test")
    context = Context()

    # Execute with middleware
    response = await manager.execute(request, context, handler)

    # Handler should not be called
    handler.assert_not_called()

    # Response should be from middleware
    assert response.body == {"error": "Unauthorized"}
    assert response.status == 401
