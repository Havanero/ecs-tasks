"""Tests for the OpenSearch client."""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from opensearchpy import AsyncOpenSearch, NotFoundError, OpenSearchException
from src.data_access.clients.opensearch_client import (OpenSearchClient,
                                                       SearchResult)


@pytest.fixture
def mock_opensearch():
    """Mock AsyncOpenSearch client."""
    mock = AsyncMock(spec=AsyncOpenSearch)
    return mock


@pytest.fixture
def client(mock_opensearch):
    """Create OpenSearchClient with mocked AsyncOpenSearch."""
    with patch(
        "src.data_access.clients.opensearch_client.AsyncOpenSearch",
        return_value=mock_opensearch,
    ):
        client = OpenSearchClient(
            hosts=["http://localhost:9200"], username="test", password="test123"
        )
        client._client = mock_opensearch
        return client


@pytest.mark.asyncio
async def test_ping(client, mock_opensearch):
    """Test ping method."""
    # Set up mock
    mock_opensearch.ping.return_value = True

    # Call method
    result = await client.ping()

    # Verify result
    assert result is True
    mock_opensearch.ping.assert_called_once()


@pytest.mark.asyncio
async def test_ping_failure(client, mock_opensearch):
    """Test ping method failure."""
    # Set up mock
    mock_opensearch.ping.side_effect = OpenSearchException("Ping failed")

    # Call method
    result = await client.ping()

    # Verify result
    assert result is False
    mock_opensearch.ping.assert_called_once()


@pytest.mark.asyncio
async def test_search(client, mock_opensearch):
    """Test search method."""
    # Set up mock
    mock_opensearch.search.return_value = {
        "took": 10,
        "hits": {
            "total": {"value": 2, "relation": "eq"},
            "hits": [
                {
                    "_id": "1",
                    "_source": {
                        "id": "1",
                        "title": "Document 1",
                        "content": "Content 1",
                    },
                },
                {
                    "_id": "2",
                    "_source": {
                        "id": "2",
                        "title": "Document 2",
                        "content": "Content 2",
                    },
                },
            ],
        },
        "aggregations": {"count": {"value": 2}},
    }

    # Call method
    result = await client.search(
        index="test-index",
        query={"match_all": {}},
        sort=[{"title": "asc"}],
        page=1,
        size=10,
        source_includes=["id", "title"],
        aggs={"count": {"value_count": {"field": "id"}}},
    )

    # Verify result
    assert isinstance(result, SearchResult)
    assert result.total == 2
    assert len(result.hits) == 2
    assert result.hits[0]["id"] == "1"
    assert result.hits[1]["id"] == "2"
    assert result.took_ms == 10
    assert result.aggregations == {"count": {"value": 2}}

    # Verify mock was called correctly
    mock_opensearch.search.assert_called_once_with(
        index="test-index",
        body={
            "query": {"match_all": {}},
            "sort": [{"title": "asc"}],
            "aggs": {"count": {"value_count": {"field": "id"}}},
        },
        from_=0,  # page 1 starts at 0
        size=10,
        _source_includes=["id", "title"],
    )


@pytest.mark.asyncio
async def test_search_exception(client, mock_opensearch):
    """Test search method with exception."""
    # Set up mock
    mock_opensearch.search.side_effect = OpenSearchException("Search failed")

    # Call method and check exception
    with pytest.raises(OpenSearchException):
        await client.search(index="test-index", query={"match_all": {}})


@pytest.mark.asyncio
async def test_get_document(client, mock_opensearch):
    """Test get_document method."""
    # Set up mock
    mock_opensearch.get.return_value = {
        "_id": "1",
        "_source": {"id": "1", "title": "Document 1", "content": "Content 1"},
    }

    # Call method
    result = await client.get_document(
        index="test-index", id="1", source_includes=["id", "title"]
    )

    # Verify result
    assert result["id"] == "1"
    assert result["title"] == "Document 1"
    assert result["content"] == "Content 1"

    # Verify mock was called correctly
    mock_opensearch.get.assert_called_once_with(
        index="test-index", id="1", _source_includes=["id", "title"]
    )


@pytest.mark.asyncio
async def test_get_document_not_found(client, mock_opensearch):
    """Test get_document method with not found error."""
    # Set up mock
    mock_opensearch.get.side_effect = NotFoundError("Document not found")

    # Call method
    result = await client.get_document(index="test-index", id="not-exists")

    # Verify result
    assert result is None


@pytest.mark.asyncio
async def test_index_document(client, mock_opensearch):
    """Test index_document method."""
    # Set up mock
    mock_opensearch.index.return_value = {"_id": "new-id", "result": "created"}

    # Call method
    document = {"title": "New Document", "content": "New Content"}
    result = await client.index_document(
        index="test-index", document=document, id="new-id", refresh=True
    )

    # Verify result
    assert result["_id"] == "new-id"
    assert result["result"] == "created"

    # Verify mock was called correctly
    mock_opensearch.index.assert_called_once_with(
        index="test-index", body=document, id="new-id", refresh=True
    )


@pytest.mark.asyncio
async def test_update_document(client, mock_opensearch):
    """Test update_document method."""
    # Set up mock
    mock_opensearch.update.return_value = {"_id": "1", "result": "updated"}

    # Call method
    doc_update = {"title": "Updated Title"}
    result = await client.update_document(
        index="test-index", id="1", doc=doc_update, refresh=True
    )

    # Verify result
    assert result["_id"] == "1"
    assert result["result"] == "updated"

    # Verify mock was called correctly
    mock_opensearch.update.assert_called_once_with(
        index="test-index", id="1", body={"doc": doc_update}, refresh=True
    )


@pytest.mark.asyncio
async def test_delete_document(client, mock_opensearch):
    """Test delete_document method."""
    # Set up mock
    mock_opensearch.delete.return_value = {"_id": "1", "result": "deleted"}

    # Call method
    result = await client.delete_document(index="test-index", id="1", refresh=True)

    # Verify result
    assert result is True

    # Verify mock was called correctly
    mock_opensearch.delete.assert_called_once_with(
        index="test-index", id="1", refresh=True
    )


@pytest.mark.asyncio
async def test_delete_document_not_found(client, mock_opensearch):
    """Test delete_document method with not found error."""
    # Set up mock
    mock_opensearch.delete.side_effect = NotFoundError("Document not found")

    # Call method
    result = await client.delete_document(index="test-index", id="not-exists")

    # Verify result
    assert result is False


@pytest.mark.asyncio
async def test_bulk_index(client, mock_opensearch):
    """Test bulk_index method."""
    # Set up mock
    with patch("src.data_access.clients.opensearch_client.async_bulk") as mock_bulk:
        mock_bulk.return_value = (2, [])

        # Call method
        documents = [{"id": "1", "title": "Doc 1"}, {"id": "2", "title": "Doc 2"}]
        result = await client.bulk_index(
            index="test-index", documents=documents, id_field="id", refresh=True
        )

        # Verify result
        assert result["success_count"] == 2
        assert result["error_count"] == 0
        assert result["errors"] == []

        # Verify mock was called correctly
        expected_actions = [
            {
                "_index": "test-index",
                "_id": "1",
                "_source": {"id": "1", "title": "Doc 1"},
            },
            {
                "_index": "test-index",
                "_id": "2",
                "_source": {"id": "2", "title": "Doc 2"},
            },
        ]
        mock_bulk.assert_called_once()
        args, kwargs = mock_bulk.call_args
        assert kwargs["client"] == mock_opensearch
        assert kwargs["refresh"] is True
        assert kwargs["raise_on_error"] is False
        # Check actions list (order might vary)
        actions = kwargs["actions"]
        assert len(actions) == 2
        assert actions[0] in expected_actions
        assert actions[1] in expected_actions


@pytest.mark.asyncio
async def test_close(client, mock_opensearch):
    """Test close method."""
    # Call method
    await client.close()

    # Verify mock was called correctly
    mock_opensearch.close.assert_called_once()
