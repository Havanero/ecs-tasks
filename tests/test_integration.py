"""Integration tests for the Lambda API framework."""
import json
from unittest.mock import AsyncMock, Mock

import pytest
from lambda_api import (API, Context, EventType, HTTPMethod, HTTPStatus,
                        Request, ResourceView, Response, View, create_handler)


class UserView(ResourceView):
    """User resource view."""

    path = "/users/{user_id}"

    async def get(self, request):
        """Get user by ID."""
        user_id = request.param("user_id")
        return {
            "id": user_id,
            "name": f"User {user_id}",
            "context_data": {
                "authenticated": request.context.get("authenticated", False)
            },
        }

    async def put(self, request):
        """Update user."""
        user_id = request.param("user_id")
        return Response(
            body={"id": user_id, "message": "User updated", "data": request.body},
            status=HTTPStatus.OK,
        )

    async def delete(self, request):
        """Delete user."""
        user_id = request.param("user_id")
        return Response(
            body={"message": f"User {user_id} deleted"}, status=HTTPStatus.OK
        )


@pytest.fixture
def api():
    """Create API instance for testing."""
    api = API()

    # Register function-based routes
    @api.get("/health")
    async def health_check(request):
        return {"status": "healthy"}

    @api.post("/users")
    async def create_user(request):
        return Response(
            body={"id": "new-user", "data": request.body}, status=HTTPStatus.CREATED
        )

    # Register class-based views
    api.register_view(UserView)

    # Register middleware
    @api.middleware
    async def auth_middleware(request, context, next_middleware):
        # Check for auth header
        auth_header = request.headers.get("Authorization")
        if auth_header == "Bearer valid-token":
            context.set("authenticated", True)
            context.set("user_id", "123")

        return await next_middleware()

    @api.middleware
    async def timing_middleware(request, context, next_middleware):
        # Add timing header
        response = await next_middleware()
        response.headers["X-Processing-Time"] = "0.001s"
        return response

    # Register event handlers
    @api.on(EventType.REQUEST_RECEIVED)
    async def log_request(event):
        event.context.set("request_logged", True)

    @api.on(EventType.RESPONSE_READY)
    async def log_response(event):
        if hasattr(event.context, "response"):
            event.context.response.headers["X-Response-Logged"] = "True"

    return api


@pytest.fixture
def lambda_handler(api):
    """Create Lambda handler from API."""
    return create_handler(api)


@pytest.mark.asyncio
async def test_health_endpoint(lambda_handler):
    """Test health endpoint."""
    # Create event
    event = {"httpMethod": "GET", "path": "/health", "headers": {}}

    # Call handler
    response = await lambda_handler(event, None)

    # Verify response
    assert response["statusCode"] == 200
    assert json.loads(response["body"]) == {"status": "healthy"}
    assert "X-Processing-Time" in response["headers"]
    assert "X-Response-Logged" in response["headers"]


@pytest.mark.asyncio
async def test_create_user(lambda_handler):
    """Test create user endpoint."""
    # Create event
    event = {
        "httpMethod": "POST",
        "path": "/users",
        "headers": {
            "Content-Type": "application/json",
            "Authorization": "Bearer valid-token",
        },
        "body": json.dumps({"name": "Test User", "email": "test@example.com"}),
    }

    # Call handler
    response = await lambda_handler(event, None)

    # Verify response
    assert response["statusCode"] == 201
    body = json.loads(response["body"])
    assert body["id"] == "new-user"
    assert body["data"]["name"] == "Test User"
    assert body["data"]["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_get_user(lambda_handler):
    """Test get user endpoint."""
    # Create event
    event = {
        "httpMethod": "GET",
        "path": "/users/123",
        "headers": {"Authorization": "Bearer valid-token"},
        "pathParameters": {"user_id": "123"},
    }

    # Call handler
    response = await lambda_handler(event, None)

    # Verify response
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["id"] == "123"
    assert body["name"] == "User 123"
    assert body["context_data"]["authenticated"] is True


@pytest.mark.asyncio
async def test_update_user(lambda_handler):
    """Test update user endpoint."""
    # Create event
    event = {
        "httpMethod": "PUT",
        "path": "/users/123",
        "headers": {
            "Content-Type": "application/json",
            "Authorization": "Bearer valid-token",
        },
        "pathParameters": {"user_id": "123"},
        "body": json.dumps({"name": "Updated User"}),
    }

    # Call handler
    response = await lambda_handler(event, None)

    # Verify response
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["id"] == "123"
    assert body["message"] == "User updated"
    assert body["data"]["name"] == "Updated User"


@pytest.mark.asyncio
async def test_delete_user(lambda_handler):
    """Test delete user endpoint."""
    # Create event
    event = {
        "httpMethod": "DELETE",
        "path": "/users/123",
        "headers": {"Authorization": "Bearer valid-token"},
        "pathParameters": {"user_id": "123"},
    }

    # Call handler
    response = await lambda_handler(event, None)

    # Verify response
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["message"] == "User 123 deleted"


@pytest.mark.asyncio
async def test_not_found(lambda_handler):
    """Test not found error."""
    # Create event
    event = {"httpMethod": "GET", "path": "/not-found", "headers": {}}

    # Call handler
    response = await lambda_handler(event, None)

    # Verify response
    assert response["statusCode"] == 404
    body = json.loads(response["body"])
    assert body["error"] == "Not found"


@pytest.mark.asyncio
async def test_method_not_allowed(lambda_handler):
    """Test method not allowed error."""
    # Create event
    event = {"httpMethod": "POST", "path": "/health", "headers": {}}

    # Call handler
    response = await lambda_handler(event, None)

    # Verify response
    assert response["statusCode"] == 405
    body = json.loads(response["body"])
    assert body["error"] == "Method not allowed"
    assert body["allowed"] == ["GET"]
    assert response["headers"]["Allow"] == "GET"


@pytest.mark.asyncio
async def test_direct_invocation(lambda_handler):
    """Test direct invocation (non-HTTP)."""
    # Create event
    event = {"action": "process", "data": {"id": 123, "items": ["item1", "item2"]}}

    # Call handler
    response = await lambda_handler(event, None)

    # Verify response
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["message"] == "Direct invocation"
    assert body["event"] == event


@pytest.mark.asyncio
async def test_error_handling(lambda_handler, api):
    """Test error handling."""

    # Register route that raises an exception
    @api.get("/error")
    async def error_route(request):
        raise ValueError("Test error")

    # Create event
    event = {"httpMethod": "GET", "path": "/error", "headers": {}}

    # Call handler
    response = await lambda_handler(event, None)

    # Verify response
    assert response["statusCode"] == 500
    body = json.loads(response["body"])
    assert body["error"] == "Test error"


@pytest.mark.asyncio
async def test_middleware_short_circuit(lambda_handler, api):
    """Test middleware short-circuiting."""

    # Register middleware that short-circuits
    @api.middleware
    async def auth_blocker(request, context, next_middleware):
        if request.path == "/blocked":
            return Response(
                body={"error": "Access denied"}, status=HTTPStatus.FORBIDDEN
            )
        return await next_middleware()

    # Register route that should not be called
    @api.get("/blocked")
    async def blocked_route(request):
        assert False, "This route should not be called"

    # Create event
    event = {"httpMethod": "GET", "path": "/blocked", "headers": {}}

    # Call handler
    response = await lambda_handler(event, None)

    # Verify response
    assert response["statusCode"] == 403
    body = json.loads(response["body"])
    assert body["error"] == "Access denied"


@pytest.mark.asyncio
async def test_path_parameters_from_router(lambda_handler):
    """Test path parameters extracted from router matching."""
    # Create event without pathParameters but with matching path
    event = {
        "httpMethod": "GET",
        "path": "/users/456",
        "headers": {},
        # Intentionally omit pathParameters to test router extraction
    }

    # Call handler
    response = await lambda_handler(event, None)

    # Verify response still works because router extracts params
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["id"] == "456"  # Should get ID from path
    assert body["name"] == "User 456"
