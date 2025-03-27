"""OpenSearch client for interacting with OpenSearch/Elasticsearch."""
import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, TypeVar, Union

from opensearchpy import AsyncOpenSearch, NotFoundError, OpenSearchException
from opensearchpy.helpers import async_bulk

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


class OpenSearchClient:
    """Abstract client for OpenSearch operations."""

    def __init__(
        self,
        hosts: List[str],
        username: Optional[str] = None,
        password: Optional[str] = None,
        aws_region: Optional[str] = None,
        use_ssl: bool = True,
        verify_certs: bool = True,
        connection_timeout: int = 10,
        max_retries: int = 3,
        retry_on_timeout: bool = True,
    ):
        """Initialize OpenSearch client.

        Args:
            hosts: List of OpenSearch hosts
            username: Basic auth username
            password: Basic auth password
            aws_region: AWS region (for AWS OpenSearch Service)
            use_ssl: Whether to use SSL
            verify_certs: Whether to verify SSL certificates
            connection_timeout: Connection timeout in seconds
            max_retries: Maximum number of retries
            retry_on_timeout: Whether to retry on timeout
        """
        self.hosts = hosts
        self.client_args = {
            "hosts": hosts,
            "use_ssl": use_ssl,
            "verify_certs": verify_certs,
            "connection_timeout": connection_timeout,
            "max_retries": max_retries,
            "retry_on_timeout": retry_on_timeout,
        }

        # Configure authentication
        if username and password:
            self.client_args["http_auth"] = (username, password)
        elif aws_region:
            # Use AWS IAM authentication if AWS region is provided
            from opensearchpy import AWSIAM

            self.client_args["http_auth"] = AWSIAM(aws_region)

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

    async def index_document(
        self,
        index: str,
        document: Dict[str, Any],
        id: Optional[str] = None,
        refresh: bool = False,
    ) -> Dict[str, Any]:
        """Index a document.

        Args:
            index: Index name
            document: Document to index
            id: Document ID (optional)
            refresh: Whether to refresh the index

        Returns:
            Dict[str, Any]: Indexing response
        """
        try:
            client = await self._get_client()
            response = await client.index(
                index=index, body=document, id=id, refresh=refresh
            )
            return response
        except OpenSearchException as e:
            logger.error(f"Failed to index document in OpenSearch: {str(e)}")
            raise

    async def bulk_index(
        self,
        index: str,
        documents: List[Dict[str, Any]],
        id_field: str = "id",
        refresh: bool = False,
    ) -> Dict[str, Any]:
        """Bulk index documents.

        Args:
            index: Index name
            documents: List of documents to index
            id_field: Field to use as document ID
            refresh: Whether to refresh the index

        Returns:
            Dict[str, Any]: Bulk indexing response
        """
        try:
            client = await self._get_client()

            actions = [
                {"_index": index, "_id": doc.get(id_field), "_source": doc}
                for doc in documents
            ]

            success, errors = await async_bulk(
                client=client, actions=actions, refresh=refresh, raise_on_error=False
            )

            return {
                "success_count": success,
                "error_count": len(errors),
                "errors": errors,
            }
        except OpenSearchException as e:
            logger.error(f"Failed to bulk index documents in OpenSearch: {str(e)}")
            raise

    async def delete_document(
        self,
        index: str,
        id: str,
        refresh: bool = False,
    ) -> bool:
        """Delete a document by ID.

        Args:
            index: Index name
            id: Document ID
            refresh: Whether to refresh the index

        Returns:
            bool: True if deleted, False if not found
        """
        try:
            client = await self._get_client()
            response = await client.delete(index=index, id=id, refresh=refresh)
            return response["result"] == "deleted"
        except NotFoundError:
            logger.debug(f"Document {id} not found in index {index}")
            return False
        except OpenSearchException as e:
            logger.error(f"Failed to delete document from OpenSearch: {str(e)}")
            raise

    async def update_document(
        self,
        index: str,
        id: str,
        doc: Dict[str, Any],
        refresh: bool = False,
    ) -> Dict[str, Any]:
        """Update a document by ID.

        Args:
            index: Index name
            id: Document ID
            doc: Document fields to update
            refresh: Whether to refresh the index

        Returns:
            Dict[str, Any]: Update response
        """
        try:
            client = await self._get_client()
            response = await client.update(
                index=index, id=id, body={"doc": doc}, refresh=refresh
            )
            return response
        except OpenSearchException as e:
            logger.error(f"Failed to update document in OpenSearch: {str(e)}")
            raise
