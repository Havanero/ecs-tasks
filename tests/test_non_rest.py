"""Tests for non-REST API invocations."""
import json
from unittest.mock import AsyncMock, Mock

import pytest
from lambda_api import (API, Context, EventType, HTTPMethod, HTTPStatus,
                        Request, Response, create_handler)


@pytest.fixture
def direct_api():
    """Create API instance with custom direct invocation handling."""
    api = API()

    # Override handle_event method to handle direct invocations
    original_handle_event = api.handle_event

    async def custom_handle_event(event, lambda_context=None):
        # Check if this is a direct invocation
        if "httpMethod" not in event:
            # Process based on action type
            if "action" in event:
                action = event["action"]

                if action == "calculate":
                    # Calculate something
                    result = sum(event.get("numbers", [0]))
                    return {
                        "statusCode": 200,
                        "body": json.dumps({"result": result, "action": action}),
                    }

                elif action == "process":
                    # Process some data
                    data = event.get("data", {})
                    processed = {
                        "id": data.get("id", "unknown"),
                        "processed": True,
                        "itemCount": len(data.get("items", [])),
                    }
                    return {
                        "statusCode": 200,
                        "body": json.dumps({"result": processed, "action": action}),
                    }

                elif action == "error":
                    # Return an error
                    return {
                        "statusCode": 400,
                        "body": json.dumps(
                            {
                                "error": "Invalid request",
                                "details": event.get("details", "No details provided"),
                            }
                        ),
                    }

            # Default direct invocation handling
            return {
                "statusCode": 200,
                "body": json.dumps({"message": "Direct invocation", "event": event}),
            }

        # Regular HTTP handling
        return await original_handle_event(event, lambda_context)

    # Replace handle_event method
    api.handle_event = custom_handle_event

    # Add normal HTTP routes for comparison
    @api.get("/health")
    async def health_check(request):
        return {"status": "healthy"}

    return api


@pytest.fixture
def direct_handler(direct_api):
    """Create Lambda handler from API with direct invocation handling."""
    return create_handler(direct_api)


@pytest.mark.asyncio
async def test_direct_calculate(direct_handler):
    """Test direct invocation with calculate action."""
    # Create event
    event = {"action": "calculate", "numbers": [1, 2, 3, 4, 5]}

    # Call handler
    response = await direct_handler(event, None)

    # Verify response
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["action"] == "calculate"
    assert body["result"] == 15  # sum of 1+2+3+4+5


@pytest.mark.asyncio
async def test_direct_process(direct_handler):
    """Test direct invocation with process action."""
    # Create event
    event = {"action": "process", "data": {"id": "item-123", "items": ["a", "b", "c"]}}

    # Call handler
    response = await direct_handler(event, None)

    # Verify response
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["action"] == "process"
    assert body["result"]["id"] == "item-123"
    assert body["result"]["processed"] is True
    assert body["result"]["itemCount"] == 3


@pytest.mark.asyncio
async def test_direct_error(direct_handler):
    """Test direct invocation with error action."""
    # Create event
    event = {"action": "error", "details": "Something went wrong"}

    # Call handler
    response = await direct_handler(event, None)

    # Verify response
    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert body["error"] == "Invalid request"
    assert body["details"] == "Something went wrong"


@pytest.mark.asyncio
async def test_direct_default(direct_handler):
    """Test direct invocation with default handling."""
    # Create event
    event = {"custom_field": "custom_value", "data": {"some": "data"}}

    # Call handler
    response = await direct_handler(event, None)

    # Verify response
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["message"] == "Direct invocation"
    assert body["event"] == event


@pytest.mark.asyncio
async def test_http_still_works(direct_handler):
    """Test that HTTP handling still works with custom direct invocation."""
    # Create event
    event = {"httpMethod": "GET", "path": "/health", "headers": {}}

    # Call handler
    response = await direct_handler(event, None)

    # Verify response
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["status"] == "healthy"


class CustomContext:
    """Custom Lambda context for testing."""

    def __init__(self):
        self.function_name = "test-function"
        self.function_version = "$LATEST"
        self.invoked_function_arn = (
            "arn:aws:lambda:us-east-1:123456789012:function:test-function"
        )
        self.memory_limit_in_mb = 128
        self.aws_request_id = "test-request-id"
        self.log_group_name = "/aws/lambda/test-function"
        self.log_stream_name = "2022/01/01/[$LATEST]abcdef123456"
        self.identity = None
        self.client_context = None

    def get_remaining_time_in_millis(self):
        """Get remaining execution time."""
        return 3000  # 3 seconds


@pytest.mark.asyncio
async def test_with_custom_lambda_context(direct_handler):
    """Test direct invocation with custom Lambda context."""
    # Create event and context
    event = {"action": "calculate", "numbers": [10, 20, 30]}
    context = CustomContext()

    # Call handler
    response = await direct_handler(event, context)

    # Verify response
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["result"] == 60  # sum of 10+20+30


@pytest.mark.asyncio
async def test_complex_nested_data(direct_handler):
    """Test direct invocation with complex nested data."""
    # Create event with complex data
    event = {
        "action": "process",
        "data": {
            "id": "complex-123",
            "items": [
                {"id": 1, "name": "Item 1", "tags": ["tag1", "tag2"]},
                {"id": 2, "name": "Item 2", "tags": ["tag2", "tag3"]},
                {
                    "id": 3,
                    "name": "Item 3",
                    "tags": ["tag1", "tag3"],
                    "nested": {"level1": {"level2": {"value": "deeply nested"}}},
                },
            ],
            "metadata": {
                "created": "2023-01-01",
                "owner": {"id": "user-456", "role": "admin"},
            },
        },
    }

    # Call handler
    response = await direct_handler(event, None)

    # Verify response
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["action"] == "process"
    assert body["result"]["id"] == "complex-123"
    assert body["result"]["itemCount"] == 3
