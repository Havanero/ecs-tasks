"""Factory for creating data access components."""
import logging
import os
from typing import Dict, Generic, Optional, Type, TypeVar

from .clients.opensearch_client import OpenSearchClient
from .dao.regulatory_dao import RegulatoryDAO
from .sources.data_source import DataSource
from .sources.regulatory_data_source import RegulatoryDataSource

# Configure logging
logger = logging.getLogger(__name__)

T = TypeVar("T")


class DataAccessFactory:
    """Factory for creating data access components."""

    def __init__(self):
        """Initialize the factory."""
        self._clients = {}
        self._daos = {}
        self._data_sources = {}

    def get_opensearch_client(
        self,
        name: str = "default",
        hosts: Optional[list] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        aws_region: Optional[str] = None,
    ) -> OpenSearchClient:
        """Get an OpenSearch client.

        Args:
            name: Client name
            hosts: OpenSearch hosts
            username: Basic auth username
            password: Basic auth password
            aws_region: AWS region

        Returns:
            OpenSearchClient: OpenSearch client
        """
        if name in self._clients:
            return self._clients[name]

        # Get configuration from environment variables if not provided
        if hosts is None:
            hosts_str = os.environ.get("OPENSEARCH_HOSTS", "http://localhost:9200")
            hosts = hosts_str.split(",")

        if username is None:
            username = os.environ.get("OPENSEARCH_USERNAME")

        if password is None:
            password = os.environ.get("OPENSEARCH_PASSWORD")

        if aws_region is None:
            aws_region = os.environ.get("AWS_REGION")

        # Create client
        client = OpenSearchClient(
            hosts=hosts, username=username, password=password, aws_region=aws_region
        )

        self._clients[name] = client
        return client

    def get_regulatory_dao(
        self,
        client_name: str = "default",
        index_prefix: str = "regulatory",
    ) -> RegulatoryDAO:
        """Get a regulatory DAO.

        Args:
            client_name: OpenSearch client name
            index_prefix: Index prefix

        Returns:
            RegulatoryDAO: Regulatory DAO
        """
        dao_key = f"regulatory_{client_name}_{index_prefix}"

        if dao_key in self._daos:
            return self._daos[dao_key]

        # Get or create client
        client = self.get_opensearch_client(client_name)

        # Create DAO
        dao = RegulatoryDAO(opensearch_client=client, index_prefix=index_prefix)

        self._daos[dao_key] = dao
        return dao

    def get_regulatory_data_source(
        self,
        client_name: str = "default",
        index_prefix: str = "regulatory",
    ) -> RegulatoryDataSource:
        """Get a regulatory data source.

        Args:
            client_name: OpenSearch client name
            index_prefix: Index prefix

        Returns:
            RegulatoryDataSource: Regulatory data source
        """
        source_key = f"regulatory_{client_name}_{index_prefix}"

        if source_key in self._data_sources:
            return self._data_sources[source_key]

        # Get or create client
        client = self.get_opensearch_client(client_name)

        # Create data source
        data_source = RegulatoryDataSource(client=client, index_prefix=index_prefix)

        self._data_sources[source_key] = data_source
        return data_source

    async def close_all_clients(self):
        """Close all OpenSearch clients."""
        for name, client in self._clients.items():
            logger.info(f"Closing OpenSearch client: {name}")
            await client.close()

        self._clients = {}
        self._daos = {}
        self._data_sources = {}


# Create a singleton instance
factory = DataAccessFactory()
