"""Tests for the DataAccessFactory."""
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from src.data_access.clients.opensearch_client import OpenSearchClient
from src.data_access.dao.regulatory_dao import RegulatoryDAO
from src.data_access.factory import DataAccessFactory
from src.data_access.sources.regulatory_data_source import RegulatoryDataSource


@pytest.fixture
def factory():
    """Create a DataAccessFactory instance."""
    return DataAccessFactory()


def test_get_opensearch_client(factory):
    """Test get_opensearch_client method."""
    # Mock the OpenSearchClient constructor
    with patch("src.data_access.factory.OpenSearchClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Call method
        client = factory.get_opensearch_client(
            hosts=["http://example.com:9200"], username="user", password="pass"
        )

        # Verify result
        assert client is mock_client

        # Verify constructor was called correctly
        mock_client_class.assert_called_once_with(
            hosts=["http://example.com:9200"],
            username="user",
            password="pass",
            aws_region=None,
        )

        # Check client was cached
        assert "default" in factory._clients
        assert factory._clients["default"] is mock_client


def test_get_opensearch_client_custom_name(factory):
    """Test get_opensearch_client method with custom name."""
    # Mock the OpenSearchClient constructor
    with patch("src.data_access.factory.OpenSearchClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Call method
        client = factory.get_opensearch_client(
            name="custom", hosts=["http://example.com:9200"]
        )

        # Verify result
        assert client is mock_client

        # Check client was cached with custom name
        assert "custom" in factory._clients
        assert factory._clients["custom"] is mock_client


def test_get_opensearch_client_aws(factory):
    """Test get_opensearch_client method with AWS region."""
    # Mock the OpenSearchClient constructor and AWSIAM
    with patch(
        "src.data_access.factory.OpenSearchClient"
    ) as mock_client_class, patch.dict(os.environ, {"AWS_REGION": "us-west-2"}):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Call method
        client = factory.get_opensearch_client()

        # Verify result
        assert client is mock_client

        # Verify constructor was called with AWS region from env
        args, kwargs = mock_client_class.call_args
        assert kwargs["aws_region"] == "us-west-2"


def test_get_opensearch_client_env_vars(factory):
    """Test get_opensearch_client method using environment variables."""
    # Mock environment variables
    env_vars = {
        "OPENSEARCH_HOSTS": "http://env-host:9200,http://env-host2:9200",
        "OPENSEARCH_USERNAME": "env-user",
        "OPENSEARCH_PASSWORD": "env-pass",
    }

    # Mock the OpenSearchClient constructor
    with patch(
        "src.data_access.factory.OpenSearchClient"
    ) as mock_client_class, patch.dict(os.environ, env_vars):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Call method without arguments
        client = factory.get_opensearch_client()

        # Verify result
        assert client is mock_client

        # Verify constructor was called with env values
        mock_client_class.assert_called_once_with(
            hosts=["http://env-host:9200", "http://env-host2:9200"],
            username="env-user",
            password="env-pass",
            aws_region=None,
        )


def test_get_opensearch_client_cached(factory):
    """Test get_opensearch_client returns cached instance."""
    # Create a mock client and add it to the cache
    mock_client = MagicMock()
    factory._clients["default"] = mock_client

    # Call method
    client = factory.get_opensearch_client()

    # Verify the cached client was returned
    assert client is mock_client


def test_get_regulatory_dao(factory):
    """Test get_regulatory_dao method."""
    # Mock OpenSearchClient and RegulatoryDAO
    with patch("src.data_access.factory.OpenSearchClient") as mock_client_class, patch(
        "src.data_access.factory.RegulatoryDAO"
    ) as mock_dao_class:
        mock_client = MagicMock()
        mock_dao = MagicMock()
        mock_client_class.return_value = mock_client
        mock_dao_class.return_value = mock_dao

        # Call method
        dao = factory.get_regulatory_dao(
            client_name="test", index_prefix="custom-prefix"
        )

        # Verify result
        assert dao is mock_dao

        # Verify DAO constructor was called correctly
        mock_dao_class.assert_called_once_with(
            opensearch_client=mock_client, index_prefix="custom-prefix"
        )

        # Check DAO was cached
        assert "regulatory_test_custom-prefix" in factory._daos
        assert factory._daos["regulatory_test_custom-prefix"] is mock_dao


def test_get_regulatory_dao_cached(factory):
    """Test get_regulatory_dao returns cached instance."""
    # Create a mock DAO and add it to the cache
    mock_dao = MagicMock()
    factory._daos["regulatory_default_regulatory"] = mock_dao

    # Call method
    dao = factory.get_regulatory_dao()

    # Verify the cached DAO was returned
    assert dao is mock_dao


def test_get_regulatory_data_source(factory):
    """Test get_regulatory_data_source method."""
    # Mock OpenSearchClient and RegulatoryDataSource
    with patch("src.data_access.factory.OpenSearchClient") as mock_client_class, patch(
        "src.data_access.factory.RegulatoryDataSource"
    ) as mock_ds_class:
        mock_client = MagicMock()
        mock_data_source = MagicMock()
        mock_client_class.return_value = mock_client
        mock_ds_class.return_value = mock_data_source

        # Call method
        data_source = factory.get_regulatory_data_source(
            client_name="test", index_prefix="custom-prefix"
        )

        # Verify result
        assert data_source is mock_data_source

        # Verify data source constructor was called correctly
        mock_ds_class.assert_called_once_with(
            client=mock_client, index_prefix="custom-prefix"
        )

        # Check data source was cached
        assert "regulatory_test_custom-prefix" in factory._data_sources
        assert (
            factory._data_sources["regulatory_test_custom-prefix"] is mock_data_source
        )


def test_get_regulatory_data_source_cached(factory):
    """Test get_regulatory_data_source returns cached instance."""
    # Create a mock data source and add it to the cache
    mock_data_source = MagicMock()
    factory._data_sources["regulatory_default_regulatory"] = mock_data_source

    # Call method
    data_source = factory.get_regulatory_data_source()

    # Verify the cached data source was returned
    assert data_source is mock_data_source


@pytest.mark.asyncio
async def test_close_all_clients(factory):
    """Test close_all_clients method."""
    # Create mock clients
    client1 = AsyncMock()
    client2 = AsyncMock()

    # Add to cache
    factory._clients = {"client1": client1, "client2": client2}

    # Add some DAOs and data sources
    factory._daos = {"dao1": MagicMock()}
    factory._data_sources = {"ds1": MagicMock()}

    # Call method
    await factory.close_all_clients()

    # Verify all clients were closed
    client1.close.assert_called_once()
    client2.close.assert_called_once()

    # Verify caches were cleared
    assert factory._clients == {}
    assert factory._daos == {}
    assert factory._data_sources == {}
