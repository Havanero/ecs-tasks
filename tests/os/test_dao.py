"""Tests for the RegulatoryDAO."""
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from src.data_access.clients.opensearch_client import SearchResult
from src.data_access.dao.regulatory_dao import (RegulatoryDAO,
                                                RegulatoryDataType,
                                                RegulatoryJurisdiction)


@pytest.fixture
def mock_opensearch_client():
    """Mock OpenSearchClient."""
    client = AsyncMock()
    return client


@pytest.fixture
def regulatory_dao(mock_opensearch_client):
    """Create RegulatoryDAO with mocked client."""
    return RegulatoryDAO(
        opensearch_client=mock_opensearch_client, index_prefix="test-regulatory"
    )


@pytest.mark.asyncio
async def test_search_regulations(regulatory_dao, mock_opensearch_client):
    """Test search_regulations method."""
    # Set up mock response
    mock_search_result = SearchResult(
        hits=[
            {
                "id": "1",
                "title": "GDPR",
                "data_type": "regulation",
                "jurisdiction": "eu",
                "effective_date": "2018-05-25T00:00:00Z",
            },
            {
                "id": "2",
                "title": "CCPA",
                "data_type": "regulation",
                "jurisdiction": "us",
                "effective_date": "2020-01-01T00:00:00Z",
            },
        ],
        total=2,
        aggregations={
            "jurisdictions": {
                "buckets": [
                    {"key": "eu", "doc_count": 1},
                    {"key": "us", "doc_count": 1},
                ]
            }
        },
        took_ms=15,
    )
    mock_opensearch_client.search.return_value = mock_search_result

    # Call method
    result = await regulatory_dao.search_regulations(
        query_text="privacy",
        data_type=RegulatoryDataType.REGULATION,
        jurisdiction=RegulatoryJurisdiction.EU,
        effective_date_start=datetime(2018, 1, 1),
        effective_date_end=datetime(2020, 1, 1),
        industry="Technology",
        topic="Data Protection",
        page=1,
        size=10,
        sort_by="effective_date",
        sort_order="desc",
    )

    # Verify result
    assert result is mock_search_result
    assert len(result.hits) == 2
    assert result.total == 2

    # Verify mock was called correctly
    mock_opensearch_client.search.assert_called_once()
    args, kwargs = mock_opensearch_client.search.call_args

    # Check index
    assert kwargs["index"] == "test-regulatory_regulation"

    # Check query structure
    query = kwargs["query"]
    assert "bool" in query
    assert "must" in query["bool"]
    assert "filter" in query["bool"]

    # Verify text search
    assert query["bool"]["must"][0]["multi_match"]["query"] == "privacy"

    # Verify filters
    filters = query["bool"]["filter"]
    data_type_filter = [
        f for f in filters if "terms" in f and "data_type" in f["terms"]
    ]
    assert len(data_type_filter) == 1
    assert data_type_filter[0]["terms"]["data_type"] == ["regulation"]

    jurisdiction_filter = [
        f for f in filters if "terms" in f and "jurisdiction" in f["terms"]
    ]
    assert len(jurisdiction_filter) == 1
    assert jurisdiction_filter[0]["terms"]["jurisdiction"] == ["eu"]

    date_filter = [
        f for f in filters if "range" in f and "effective_date" in f["range"]
    ]
    assert len(date_filter) == 1
    assert "gte" in date_filter[0]["range"]["effective_date"]
    assert "lte" in date_filter[0]["range"]["effective_date"]

    # Verify sort
    assert kwargs["sort"] == [{"effective_date": {"order": "desc"}}]

    # Verify pagination
    assert kwargs["page"] == 1
    assert kwargs["size"] == 10


@pytest.mark.asyncio
async def test_get_regulation_by_id_with_data_type(
    regulatory_dao, mock_opensearch_client
):
    """Test get_regulation_by_id method with known data type."""
    # Set up mock
    regulation = {
        "id": "1",
        "title": "GDPR",
        "data_type": "regulation",
        "jurisdiction": "eu",
    }
    mock_opensearch_client.get_document.return_value = regulation

    # Call method
    result = await regulatory_dao.get_regulation_by_id(
        regulation_id="1", data_type=RegulatoryDataType.REGULATION
    )

    # Verify result
    assert result is regulation

    # Verify mock was called correctly
    mock_opensearch_client.get_document.assert_called_once_with(
        "test-regulatory_regulation", "1"
    )


@pytest.mark.asyncio
async def test_get_regulation_by_id_without_data_type(
    regulatory_dao, mock_opensearch_client
):
    """Test get_regulation_by_id method without data type (tries all types)."""

    # Set up mock - return None for all types except standard
    async def get_document_side_effect(index, id):
        if index == "test-regulatory_standard":
            return {
                "id": "1",
                "title": "ISO 27001",
                "data_type": "standard",
                "jurisdiction": "global",
            }
        return None

    mock_opensearch_client.get_document.side_effect = get_document_side_effect

    # Call method
    result = await regulatory_dao.get_regulation_by_id(regulation_id="1")

    # Verify result
    assert result is not None
    assert result["data_type"] == "standard"
    assert result["title"] == "ISO 27001"

    # Verify mock was called with all data types
    expected_calls = [(f"test-regulatory_{dt.value}", "1") for dt in RegulatoryDataType]

    # Check that all expected calls were made (order doesn't matter)
    for expected_call in expected_calls:
        found = False
        for actual_call in mock_opensearch_client.get_document.call_args_list:
            if actual_call[0] == expected_call:
                found = True
                break
        assert found, f"Missing expected call: {expected_call}"


@pytest.mark.asyncio
async def test_get_regulation_by_id_not_found(regulatory_dao, mock_opensearch_client):
    """Test get_regulation_by_id method when document is not found."""
    # Set up mock
    mock_opensearch_client.get_document.return_value = None

    # Call method
    result = await regulatory_dao.get_regulation_by_id(regulation_id="not-exists")

    # Verify result
    assert result is None

    # Verify all data types were tried
    assert mock_opensearch_client.get_document.call_count == len(RegulatoryDataType)


@pytest.mark.asyncio
async def test_get_related_regulations(regulatory_dao, mock_opensearch_client):
    """Test get_related_regulations method."""
    # Set up mocks
    # First get the original regulation
    original_regulation = {
        "id": "1",
        "title": "GDPR",
        "content": "Data protection regulation",
        "jurisdiction": "eu",
        "industries": ["Technology", "Healthcare"],
        "topics": ["Privacy", "Data Protection"],
    }

    # Then mock the search for related regulations
    related_regulations = [
        {
            "id": "2",
            "title": "CCPA",
            "summary": "California privacy law",
            "jurisdiction": "us",
        },
        {
            "id": "3",
            "title": "ePrivacy Directive",
            "summary": "EU privacy directive",
            "jurisdiction": "eu",
        },
    ]

    # Set up mock responses
    async def get_document_side_effect(index, id):
        if id == "1":
            return original_regulation
        return None

    mock_opensearch_client.get_document.side_effect = get_document_side_effect
    mock_opensearch_client.search.return_value = SearchResult(
        hits=related_regulations, total=2
    )

    # Call method
    result = await regulatory_dao.get_related_regulations(
        regulation_id="1", max_results=5
    )

    # Verify result
    assert result == related_regulations

    # Verify mocks were called correctly
    mock_opensearch_client.get_document.assert_called_once()
    mock_opensearch_client.search.assert_called_once()

    # Check search query
    search_args, search_kwargs = mock_opensearch_client.search.call_args
    assert search_kwargs["index"] == "test-regulatory_*"
    assert search_kwargs["size"] == 5

    # Check the query has a must_not clause to exclude the original document
    query = search_kwargs["query"]
    assert "bool" in query
    assert "must_not" in query["bool"]
    must_not = query["bool"]["must_not"][0]
    assert "term" in must_not
    assert must_not["term"]["id"] == "1"

    # Check the query has a should clause for jurisdiction
    assert "should" in query["bool"]
    should = query["bool"]["should"]
    assert any(c for c in should if "term" in c and "jurisdiction" in c["term"])
    assert any(c for c in should if "terms" in c and "industries" in c["terms"])


@pytest.mark.asyncio
async def test_get_latest_regulations(regulatory_dao, mock_opensearch_client):
    """Test get_latest_regulations method."""
    # Set up mock
    mock_search_result = SearchResult(
        hits=[
            {
                "id": "1",
                "title": "New Regulation",
                "publication_date": "2023-01-15T00:00:00Z",
            },
            {
                "id": "2",
                "title": "Another New Regulation",
                "publication_date": "2023-01-10T00:00:00Z",
            },
        ],
        total=2,
    )
    mock_opensearch_client.search.return_value = mock_search_result

    # Call method
    result = await regulatory_dao.get_latest_regulations(
        days=30, jurisdiction=RegulatoryJurisdiction.US, page=1, size=10
    )

    # Verify result
    assert result is mock_search_result

    # Verify mock was called correctly
    mock_opensearch_client.search.assert_called_once()
    args, kwargs = mock_opensearch_client.search.call_args

    # Check index and query
    assert kwargs["index"] == "test-regulatory_*"

    # Verify query contains date range
    query = kwargs["query"]
    assert "bool" in query
    assert "filter" in query["bool"]
    filters = query["bool"]["filter"]

    # Check date filter
    date_filter = [
        f for f in filters if "range" in f and "publication_date" in f["range"]
    ]
    assert len(date_filter) == 1
    assert "gte" in date_filter[0]["range"]["publication_date"]
    assert date_filter[0]["range"]["publication_date"]["gte"] == "now-30d/d"

    # Check jurisdiction filter
    jurisdiction_filter = [
        f for f in filters if "term" in f and "jurisdiction" in f["term"]
    ]
    assert len(jurisdiction_filter) == 1
    assert jurisdiction_filter[0]["term"]["jurisdiction"] == "us"

    # Check sort (by publication date, descending)
    assert kwargs["sort"] == [{"publication_date": {"order": "desc"}}]
