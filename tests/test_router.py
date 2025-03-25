"""Tests for the router module."""
import re
from unittest.mock import AsyncMock, Mock

import pytest
from lambda_api.router import RouteDefinition, Router
from lambda_api.types import HTTPMethod, MethodNotAllowedError


def test_route_definition_initialization():
    """Test route definition initialization."""
    # Simple path
    route_def = RouteDefinition("/users")

    assert route_def.template == "/users"
    assert route_def.param_names == []
    assert isinstance(route_def.pattern, re.Pattern)

    # Path with parameters
    route_def = RouteDefinition("/users/{id}/posts/{post_id}")

    assert route_def.template == "/users/{id}/posts/{post_id}"
    assert route_def.param_names == ["id", "post_id"]
    assert isinstance(route_def.pattern, re.Pattern)


def test_route_definition_match():
    """Test route definition match method."""
    # Simple path
    route_def = RouteDefinition("/users")

    # Exact match
    assert route_def.match("/users") == {}

    # No match
    assert route_def.match("/posts") is None
    assert route_def.match("/users/123") is None

    # Path with single parameter
    route_def = RouteDefinition("/users/{id}")

    # Match with parameter
    assert route_def.match("/users/123") == {"id": "123"}
    assert route_def.match("/users/abc") == {"id": "abc"}

    # No match
    assert route_def.match("/users") is None
    assert route_def.match("/users/123/posts") is None

    # Path with multiple parameters
    route_def = RouteDefinition("/users/{user_id}/posts/{post_id}")

    # Match with parameters
    assert route_def.match("/users/123/posts/456") == {
        "user_id": "123",
        "post_id": "456",
    }
    assert route_def.match("/users/abc/posts/def") == {
        "user_id": "abc",
        "post_id": "def",
    }

    # No match
    assert route_def.match("/users/123/posts") is None
    assert route_def.match("/users/123/comments/456") is None


def test_router_initialization():
    """Test router initialization."""
    # Default initialization
    router = Router()

    assert router.prefix == ""
    assert router.routes == {}
    assert router.dynamic_routes == []

    # With prefix
    router = Router(prefix="/api")

    assert router.prefix == "/api"
    assert router.routes == {}
    assert router.dynamic_routes == []


def test_router_add_route_static():
    """Test router add_route method with static path."""
    router = Router()
    handler = AsyncMock()

    # Add GET route
    router.add_route("/users", handler, [HTTPMethod.GET])

    assert "/users" in router.routes
    assert HTTPMethod.GET in router.routes["/users"]
    assert router.routes["/users"][HTTPMethod.GET] is handler

    # Add another method to same path
    handler2 = AsyncMock()
    router.add_route("/users", handler2, [HTTPMethod.POST])

    assert HTTPMethod.POST in router.routes["/users"]
    assert router.routes["/users"][HTTPMethod.POST] is handler2

    # Original handler should still be there
    assert router.routes["/users"][HTTPMethod.GET] is handler

    # Add route with prefix
    router = Router(prefix="/api")
    router.add_route("/users", handler, [HTTPMethod.GET])

    assert "/api/users" in router.routes


def test_router_add_route_dynamic():
    """Test router add_route method with dynamic path."""
    router = Router()
    handler = AsyncMock()

    # Add route with parameter
    router.add_route("/users/{id}", handler, [HTTPMethod.GET])

    # Should be added to dynamic_routes, not routes
    assert "/users/{id}" not in router.routes
    assert len(router.dynamic_routes) == 1

    route_def, methods = router.dynamic_routes[0]
    assert route_def.template == "/users/{id}"
    assert HTTPMethod.GET in methods
    assert methods[HTTPMethod.GET] is handler

    # Add another method to same path
    handler2 = AsyncMock()
    router.add_route("/users/{id}", handler2, [HTTPMethod.PUT])

    # Should update existing dynamic route
    assert len(router.dynamic_routes) == 1

    route_def, methods = router.dynamic_routes[0]
    assert HTTPMethod.PUT in methods
    assert methods[HTTPMethod.PUT] is handler2

    # Original handler should still be there
    assert methods[HTTPMethod.GET] is handler


def test_router_route_decorator():
    """Test router route decorator."""
    router = Router()

    # Use decorator
    @router.route("/users", methods=[HTTPMethod.GET, HTTPMethod.POST])
    async def handle_users(request):
        return {"users": []}

    # Check if route was added
    assert "/users" in router.routes
    assert HTTPMethod.GET in router.routes["/users"]
    assert HTTPMethod.POST in router.routes["/users"]
    assert router.routes["/users"][HTTPMethod.GET] is handle_users
    assert router.routes["/users"][HTTPMethod.POST] is handle_users

    # Default method is GET
    @router.route("/health")
    async def health_check(request):
        return {"status": "healthy"}

    assert "/health" in router.routes
    assert HTTPMethod.GET in router.routes["/health"]
    assert router.routes["/health"][HTTPMethod.GET] is health_check


def test_router_method_decorators():
    """Test router method-specific decorators."""
    router = Router()

    # GET decorator
    @router.get("/users")
    async def get_users(request):
        return {"users": []}

    assert "/users" in router.routes
    assert HTTPMethod.GET in router.routes["/users"]
    assert router.routes["/users"][HTTPMethod.GET] is get_users

    # POST decorator
    @router.post("/users")
    async def create_user(request):
        return {"id": "new-user"}

    assert HTTPMethod.POST in router.routes["/users"]
    assert router.routes["/users"][HTTPMethod.POST] is create_user

    # Other method decorators
    @router.put("/users/{id}")
    async def update_user(request):
        return {"id": "updated-user"}

    @router.delete("/users/{id}")
    async def delete_user(request):
        return {"id": "deleted-user"}

    @router.patch("/users/{id}")
    async def patch_user(request):
        return {"id": "patched-user"}

    # Dynamic routes should be added
    assert len(router.dynamic_routes) == 1

    route_def, methods = router.dynamic_routes[0]
    assert route_def.template == "/users/{id}"
    assert HTTPMethod.PUT in methods
    assert HTTPMethod.DELETE in methods
    assert HTTPMethod.PATCH in methods


def test_router_find_route_static():
    """Test router find_route method with static paths."""
    router = Router()
    handler1 = AsyncMock()
    handler2 = AsyncMock()

    # Add routes
    router.add_route("/users", handler1, [HTTPMethod.GET, HTTPMethod.POST])
    router.add_route("/health", handler2, [HTTPMethod.GET])

    # Find existing routes
    handler, params = router.find_route("/users", HTTPMethod.GET)
    assert handler is handler1
    assert params == {}

    handler, params = router.find_route("/users", HTTPMethod.POST)
    assert handler is handler1
    assert params == {}

    handler, params = router.find_route("/health", HTTPMethod.GET)
    assert handler is handler2
    assert params == {}

    # Find non-existent route
    handler, params = router.find_route("/missing", HTTPMethod.GET)
    assert handler is None
    assert params == {}

    # Method not allowed
    with pytest.raises(MethodNotAllowedError) as excinfo:
        router.find_route("/users", HTTPMethod.PUT)

    assert excinfo.value.allowed_methods == [HTTPMethod.GET, HTTPMethod.POST]


def test_router_find_route_dynamic():
    """Test router find_route method with dynamic paths."""
    router = Router()
    handler1 = AsyncMock()
    handler2 = AsyncMock()

    # Add routes
    router.add_route("/users/{id}", handler1, [HTTPMethod.GET, HTTPMethod.PUT])
    router.add_route(
        "/posts/{post_id}/comments/{comment_id}", handler2, [HTTPMethod.GET]
    )

    # Find route with parameter
    handler, params = router.find_route("/users/123", HTTPMethod.GET)
    assert handler is handler1
    assert params == {"id": "123"}

    handler, params = router.find_route("/users/abc", HTTPMethod.PUT)
    assert handler is handler1
    assert params == {"id": "abc"}

    # Find route with multiple parameters
    handler, params = router.find_route("/posts/123/comments/456", HTTPMethod.GET)
    assert handler is handler2
    assert params == {"post_id": "123", "comment_id": "456"}

    # Method not allowed
    with pytest.raises(MethodNotAllowedError) as excinfo:
        router.find_route("/users/123", HTTPMethod.DELETE)

    assert excinfo.value.allowed_methods == [HTTPMethod.GET, HTTPMethod.PUT]

    # Non-existent path
    handler, params = router.find_route("/users/123/profile", HTTPMethod.GET)
    assert handler is None
    assert params == {}
