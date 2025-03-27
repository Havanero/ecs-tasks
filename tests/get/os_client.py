"""OpenSearch client for reading data from OpenSearch/Elasticsearch."""
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Generic, List, Optional, TypeVar

from opensearchpy import AsyncOpenSearch, NotFoundError, OpenSearchException

# Configure logging
logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class SearchResult(Generic[T]):
    """Container for search results."""

    hits: List[T]
    total: int
    aggregations: Optional[Dict[str, Any]] = None
    took_ms: Optional[int] = None


@dataclass
class OpenSearchConfig:
    """Configuration for OpenSearch client."""

    hosts: List[str]
    username: Optional[str] = None
    password: Optional[str] = None
    aws_region: Optional[str] = None
    use_ssl: bool = True
    verify_certs: bool = True
    connection_timeout: int = 10
    max_retries: int = 3
    retry_on_timeout: bool = True


class OpenSearchClient:
    """Client for read-only OpenSearch operations."""

    def __init__(self, config: OpenSearchConfig):
        """Initialize OpenSearch client.

        Args:
            config: OpenSearch configuration
        """
        self.config = config
        self.client_args = {
            "hosts": config.hosts,
            "use_ssl": config.use_ssl,
            "verify_certs": config.verify_certs,
            "connection_timeout": config.connection_timeout,
            "max_retries": config.max_retries,
            "retry_on_timeout": config.retry_on_timeout,
        }

        # Configure authentication
        if config.username and config.password:
            self.client_args["http_auth"] = (config.username, config.password)
        elif config.aws_region:
            # Use AWS IAM authentication if AWS region is provided
            from opensearchpy import AWSIAM

            self.client_args["http_auth"] = AWSIAM(config.aws_region)

        self._client = None

    async def _get_client(self) -> AsyncOpenSearch:
        """Get the AsyncOpenSearch client instance.

        Returns:
            AsyncOpenSearch: Initialized client
        """
        if self._client is None:
            self._client = AsyncOpenSearch(**self.client_args)
        return self._client

    async def close(self):
        """Close the client connection."""
        if self._client:
            await self._client.close()
            self._client = None

    async def ping(self) -> bool:
        """Check if the OpenSearch cluster is available.

        Returns:
            bool: True if the cluster is available
        """
        try:
            client = await self._get_client()
            return await client.ping()
        except OpenSearchException as e:
            logger.error(f"Failed to ping OpenSearch: {str(e)}")
            return False

    async def search(
        self,
        index: str,
        query: Dict[str, Any],
        sort: Optional[List[Dict[str, str]]] = None,
        page: int = 1,
        size: int = 10,
        source_includes: Optional[List[str]] = None,
        aggs: Optional[Dict[str, Any]] = None,
    ) -> SearchResult:
        """Search documents in the specified index.

        Args:
            index: Index name
            query: Query DSL
            sort: Sort criteria
            page: Page number (1-based)
            size: Page size
            source_includes: Fields to include in the response
            aggs: Aggregations to perform

        Returns:
            SearchResult: Search results
        """
        try:
            client = await self._get_client()

            body = {"query": query}
            if sort:
                body["sort"] = sort
            if aggs:
                body["aggs"] = aggs

            # Calculate from based on page and size
            from_ = (page - 1) * size

            response = await client.search(
                index=index,
                body=body,
                from_=from_,
                size=size,
                _source_includes=source_includes,
            )

            # Extract hits and convert to objects
            hits = [hit["_source"] for hit in response["hits"]["hits"]]
            total = response["hits"]["total"]["value"]
            took_ms = response.get("took")
            aggregations = response.get("aggregations")

            return SearchResult(
                hits=hits, total=total, aggregations=aggregations, took_ms=took_ms
            )

        except OpenSearchException as e:
            logger.error(f"Failed to search in OpenSearch: {str(e)}")
            raise

    async def get_document(
        self,
        index: str,
        id: str,
        source_includes: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get a document by ID.

        Args:
            index: Index name
            id: Document ID
            source_includes: Fields to include in the response

        Returns:
            Optional[Dict[str, Any]]: Document if found, None otherwise
        """
        try:
            client = await self._get_client()
            response = await client.get(
                index=index, id=id, _source_includes=source_includes
            )
            return response["_source"]
        except NotFoundError:
            logger.debug(f"Document {id} not found in index {index}")
            return None
        except OpenSearchException as e:
            logger.error(f"Failed to get document from OpenSearch: {str(e)}")
            raise
