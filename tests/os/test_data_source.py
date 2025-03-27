"""Tests for the RegulatoryDataSource."""
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from src.data_access.clients.opensearch_client import SearchResult
from src.data_access.dao.regulatory_dao import (RegulatoryDataType,
                                                RegulatoryJurisdiction)
from src.data_access.sources.regulatory_data_source import (
    RegulatoryDataSource, RegulatoryDocument)


@pytest.fixture
def mock_opensearch_client():
    """Mock OpenSearch client."""
    client = AsyncMock()
    return client


@pytest.fixture
def data_source(mock_opensearch_client):
    """Create RegulatoryDataSource with mocked client."""
    return RegulatoryDataSource(
        client=mock_opensearch_client, index_prefix="test-regulatory"
    )


@pytest.fixture
def sample_document():
    """Create a sample regulatory document."""
    return RegulatoryDocument(
        id="test-reg-1",
        title="Test Regulation",
        data_type=RegulatoryDataType.REGULATION,
        jurisdiction=RegulatoryJurisdiction.EU,
        summary="Test regulation summary",
        effective_date=datetime(2022, 1, 1),
        publication_date=datetime(2021, 12, 1),
        issuing_body="Test Regulatory Body",
        industries=["Technology", "Finance"],
        topics=["Data Protection", "Privacy"],
    )


def test_regulatory_document_to_dict(sample_document):
    """Test converting RegulatoryDocument to dict."""
    doc_dict = sample_document.to_dict()

    # Check basic properties
    assert doc_dict["id"] == "test-reg-1"
    assert doc_dict["title"] == "Test Regulation"

    # Check enum conversions
    assert doc_dict["data_type"] == "regulation"
    assert doc_dict["jurisdiction"] == "eu"

    # Check date conversions
    assert doc_dict["effective_date"] == "2022-01-01T00:00:00"
    assert doc_dict["publication_date"] == "2021-12-01T00:00:00"

    # Check lists
    assert doc_dict["industries"] == ["Technology", "Finance"]
    assert doc_dict["topics"] == ["Data Protection", "Privacy"]


def test_regulatory_document_from_dict():
    """Test creating RegulatoryDocument from dict."""
    doc_dict = {
        "id": "test-reg-1",
        "title": "Test Regulation",
        "data_type": "regulation",
        "jurisdiction": "eu",
        "summary": "Test regulation summary",
        "effective_date": "2022-01-01T00:00:00",
        "publication_date": "2021-12-01T00:00:00",
        "issuing_body": "Test Regulatory Body",
        "industries": ["Technology", "Finance"],
        "topics": ["Data Protection", "Privacy"],
    }

    document = RegulatoryDocument.from_dict(doc_dict)

    # Check basic properties
    assert document.id == "test-reg-1"
    assert document.title == "Test Regulation"

    # Check enum conversions
    assert document.data_type == RegulatoryDataType.REGULATION
    assert document.jurisdiction == RegulatoryJurisdiction.EU

    # Check date conversions
    assert document.effective_date == datetime(2022, 1, 1)
    assert document.publication_date == datetime(2021, 12, 1)

    # Check lists
    assert document.industries == ["Technology", "Finance"]
    assert document.topics == ["Data Protection", "Privacy"]


@pytest.mark.asyncio
async def test_transform_record(data_source):
    """Test transform_record method."""
    record = {
        "id": "test-reg-1",
        "title": "Test Regulation",
        "data_type": "regulation",
        "jurisdiction": "eu",
    }

    result = data_source.transform_record(record)

    assert isinstance(result, RegulatoryDocument)
    assert result.id == "test-reg-1"
    assert result.title == "Test Regulation"
    assert result.data_type == RegulatoryDataType.REGULATION
    assert result.jurisdiction == RegulatoryJurisdiction.EU


@pytest.mark.asyncio
async def test_prepare_record(data_source, sample_document):
    """Test prepare_record method."""
    # Clone the document to avoid modifying the fixture
    document = RegulatoryDocument(
        id=sample_document.id,
        title=sample_document.title,
        data_type=sample_document.data_type,
        jurisdiction=sample_document.jurisdiction,
        summary=sample_document.summary,
        effective_date=sample_document.effective_date,
        publication_date=sample_document.publication_date,
    )

    # Ensure timestamps are not set
    assert document.created_at is None
    assert document.updated_at is None

    result = data_source.prepare_record(document)

    # Check timestamps were set
    assert document.created_at is not None
    assert document.updated_at is not None

    # Check result is a dict with the right values
    assert isinstance(result, dict)
    assert result["id"] == "test-reg-1"
    assert result["data_type"] == "regulation"
    assert result["jurisdiction"] == "eu"

    # Check timestamps in result
    assert "created_at" in result
    assert "updated_at" in result


@pytest.mark.asyncio
async def test_create(data_source, mock_opensearch_client, sample_document):
    """Test create method."""
    # Set up mock
    mock_opensearch_client.index_document.return_value = {
        "_id": sample_document.id,
        "result": "created",
    }

    # Call method
    result = await data_source.create(sample_document)

    # Verify result
    assert result is sample_document

    # Verify mock was called correctly with the right index
    mock_opensearch_client.index_document.assert_called_once()
    args, kwargs = mock_opensearch_client.index_document.call_args

    assert kwargs["index"] == "test-regulatory_regulation"  # Based on document type
    assert kwargs["document"]["id"] == sample_document.id
    assert kwargs["document"]["title"] == sample_document.title
    assert kwargs["document"]["data_type"] == "regulation"
    assert kwargs["id"] is None  # Should use the id from the document


@pytest.mark.asyncio
async def test_search_by_text(data_source, mock_opensearch_client):
    """Test search_by_text method."""
    # Set up mock
    mock_result = SearchResult(
        hits=[
            RegulatoryDocument(
                id="doc-1",
                title="Privacy Regulation",
                data_type=RegulatoryDataType.REGULATION,
                jurisdiction=RegulatoryJurisdiction.EU,
            ),
            RegulatoryDocument(
                id="doc-2",
                title="Data Protection Standard",
                data_type=RegulatoryDataType.STANDARD,
                jurisdiction=RegulatoryJurisdiction.GLOBAL,
            ),
        ],
        total=2,
    )

    # Mock the search method
    with patch.object(data_source, "search", return_value=mock_result) as mock_search:
        # Call method
        result = await data_source.search_by_text(
            text="privacy",
            data_type=RegulatoryDataType.REGULATION,
            jurisdiction=RegulatoryJurisdiction.EU,
        )

        # Verify result
        assert result == mock_result.hits

        # Verify search was called with correct parameters
        mock_search.assert_called_once()
        args, kwargs = mock_search.call_args

        query = args[0]
        assert query["bool"]["must"][0]["multi_match"]["query"] == "privacy"
        assert query["bool"]["must"][0]["multi_match"]["fields"] == [
            "title^3",
            "summary^2",
            "content",
            "keywords^2",
        ]

        # Check filters
        filters = query["bool"]["filter"]
        assert {"term": {"data_type": "regulation"}} in filters
        assert {"term": {"jurisdiction": "eu"}} in filters

        # Check index
        assert kwargs.get("page") == 1
        assert kwargs.get("size") == 20


@pytest.mark.asyncio
async def test_get_by_jurisdiction(data_source, mock_opensearch_client):
    """Test get_by_jurisdiction method."""
    # Set up mock
    mock_docs = [
        RegulatoryDocument(
            id="doc-1",
            title="EU Regulation 1",
            data_type=RegulatoryDataType.REGULATION,
            jurisdiction=RegulatoryJurisdiction.EU,
        ),
        RegulatoryDocument(
            id="doc-2",
            title="EU Regulation 2",
            data_type=RegulatoryDataType.REGULATION,
            jurisdiction=RegulatoryJurisdiction.EU,
        ),
    ]
    mock_result = SearchResult(hits=mock_docs, total=2)

    # Mock the search method
    with patch.object(data_source, "search", return_value=mock_result) as mock_search:
        # Call method
        result = await data_source.get_by_jurisdiction(
            jurisdiction=RegulatoryJurisdiction.EU,
            data_type=RegulatoryDataType.REGULATION,
            sort_field="title",
            sort_order="asc",
        )

        # Verify result
        assert result == mock_docs

        # Verify search was called with correct parameters
        mock_search.assert_called_once()
        args, kwargs = mock_search.call_args

        query = args[0]
        assert "bool" in query
        assert "filter" in query["bool"]

        # Check filters
        filters = query["bool"]["filter"]
        assert {"term": {"jurisdiction": "eu"}} in filters
        assert {"term": {"data_type": "regulation"}} in filters

        # Check sort
        assert kwargs["sort"] == [{"title": {"order": "asc"}}]


@pytest.mark.asyncio
async def test_get_by_effective_date_range(data_source, mock_opensearch_client):
    """Test get_by_effective_date_range method."""
    # Set up mock
    mock_docs = [
        RegulatoryDocument(
            id="doc-1",
            title="2022 Regulation",
            data_type=RegulatoryDataType.REGULATION,
            jurisdiction=RegulatoryJurisdiction.EU,
            effective_date=datetime(2022, 1, 15),
        ),
        RegulatoryDocument(
            id="doc-2",
            title="2022 Regulation 2",
            data_type=RegulatoryDataType.REGULATION,
            jurisdiction=RegulatoryJurisdiction.EU,
            effective_date=datetime(2022, 2, 1),
        ),
    ]
    mock_result = SearchResult(hits=mock_docs, total=2)

    # Mock the search method
    with patch.object(data_source, "search", return_value=mock_result) as mock_search:
        # Call method
        start_date = datetime(2022, 1, 1)
        end_date = datetime(2022, 12, 31)

        result = await data_source.get_by_effective_date_range(
            start_date=start_date,
            end_date=end_date,
            data_type=RegulatoryDataType.REGULATION,
            jurisdiction=RegulatoryJurisdiction.EU,
        )

        # Verify result
        assert result == mock_docs

        # Verify search was called with correct parameters
        mock_search.assert_called_once()
        args, kwargs = mock_search.call_args

        query = args[0]
        assert "bool" in query
        assert "filter" in query["bool"]

        # Check date range filter
        filters = query["bool"]["filter"]
        date_filter = [f for f in filters if "range" in f][0]
        assert date_filter["range"]["effective_date"]["gte"] == start_date.isoformat()
        assert date_filter["range"]["effective_date"]["lte"] == end_date.isoformat()

        # Check other filters
        assert {"term": {"data_type": "regulation"}} in filters
        assert {"term": {"jurisdiction": "eu"}} in filters

        # Check sort
        assert kwargs["sort"] == [{"effective_date": {"order": "desc"}}]


@pytest.mark.asyncio
async def test_get_by_topics(data_source, mock_opensearch_client):
    """Test get_by_topics method."""
    # Set up mock
    mock_docs = [
        RegulatoryDocument(
            id="doc-1",
            title="Privacy Regulation",
            data_type=RegulatoryDataType.REGULATION,
            jurisdiction=RegulatoryJurisdiction.EU,
            topics=["Privacy", "Data Protection"],
        ),
        RegulatoryDocument(
            id="doc-2",
            title="Security Standard",
            data_type=RegulatoryDataType.STANDARD,
            jurisdiction=RegulatoryJurisdiction.GLOBAL,
            topics=["Security", "Data Protection"],
        ),
    ]
    mock_result = SearchResult(hits=mock_docs, total=2)

    # Mock the search method
    with patch.object(data_source, "search", return_value=mock_result) as mock_search:
        # Call method - match any topic
        topics = ["Privacy", "Data Protection"]

        result = await data_source.get_by_topics(
            topics=topics,
            match_all=False,
            data_type=RegulatoryDataType.REGULATION,
            jurisdiction=RegulatoryJurisdiction.EU,
        )

        # Verify result
        assert result == mock_docs

        # Verify search was called with correct parameters
        mock_search.assert_called_once()
        args, kwargs = mock_search.call_args

        query = args[0]
        assert "bool" in query
        assert "filter" in query["bool"]

        # Check topics filter (OR condition)
        filters = query["bool"]["filter"]
        topics_filter = [f for f in filters if "terms" in f and "topics" in f["terms"]][
            0
        ]
        assert topics_filter["terms"]["topics"] == topics

        # Check other filters
        assert {"term": {"data_type": "regulation"}} in filters
        assert {"term": {"jurisdiction": "eu"}} in filters

        # Reset mock
        mock_search.reset_mock()

        # Test with match_all=True (AND condition)
        await data_source.get_by_topics(topics=topics, match_all=True)

        # Verify search was called with correct parameters
        mock_search.assert_called_once()
        args, kwargs = mock_search.call_args

        query = args[0]
        filters = query["bool"]["filter"]

        # Check that we have two topic filters (one for each topic)
        topic_filters = [f for f in filters if "term" in f and "topics" in f["term"]]
        assert len(topic_filters) == 2
        assert {"term": {"topics": "Privacy"}} in filters
        assert {"term": {"topics": "Data Protection"}} in filters
