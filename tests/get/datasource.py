"""Data source interface and abstract base classes (read-only)."""
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Optional, TypeVar

from ..clients.opensearch_client import SearchResult

# Configure logging
logger = logging.getLogger(__name__)

T = TypeVar("T")


class ReadOnlyDataSource(Generic[T], ABC):
    """Abstract base class for read-only data sources."""

    @abstractmethod
    async def search(self, query: Dict[str, Any], **kwargs) -> SearchResult[T]:
        """Search for records in the data source.

        Args:
            query: Query parameters
            **kwargs: Additional parameters

        Returns:
            SearchResult: Search results
        """
        pass

    @abstractmethod
    async def get_by_id(self, id: str, **kwargs) -> Optional[T]:
        """Get a record by ID.

        Args:
            id: Record ID
            **kwargs: Additional parameters

        Returns:
            Optional[T]: Record if found, None otherwise
        """
        pass


class OpenSearchReadOnlyDataSource(ReadOnlyDataSource[T], ABC):
    """Base class for OpenSearch read-only data sources."""

    def __init__(self, client, index):
        """Initialize the data source.

        Args:
            client: OpenSearch client
            index: Index name
        """
        self.client = client
        self.index = index

    async def search(self, query: Dict[str, Any], **kwargs) -> SearchResult[T]:
        """Search for records in OpenSearch.

        Args:
            query: Query DSL
            **kwargs: Additional parameters

        Returns:
            SearchResult: Search results
        """
        # Extract common parameters with defaults
        page = kwargs.get("page", 1)
        size = kwargs.get("size", 20)
        sort = kwargs.get("sort")
        source_includes = kwargs.get("source_includes")
        aggs = kwargs.get("aggs")

        # Perform the search
        result = await self.client.search(
            index=self.index,
            query=query,
            sort=sort,
            page=page,
            size=size,
            source_includes=source_includes,
            aggs=aggs,
        )

        # Transform hits if needed
        hits = result.hits
        if hasattr(self, "transform_record"):
            hits = [self.transform_record(hit) for hit in hits]

        return SearchResult(
            hits=hits,
            total=result.total,
            aggregations=result.aggregations,
            took_ms=result.took_ms,
        )

    async def get_by_id(self, id: str, **kwargs) -> Optional[T]:
        """Get a record by ID from OpenSearch.

        Args:
            id: Record ID
            **kwargs: Additional parameters

        Returns:
            Optional[T]: Record if found, None otherwise
        """
        source_includes = kwargs.get("source_includes")

        record = await self.client.get_document(
            index=self.index, id=id, source_includes=source_includes
        )

        if record and hasattr(self, "transform_record"):
            return self.transform_record(record)

        return record
