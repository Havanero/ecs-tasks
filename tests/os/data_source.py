"""Data source interface and abstract base classes."""
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Optional, TypeVar

from ..clients.opensearch_client import SearchResult

# Configure logging
logger = logging.getLogger(__name__)

T = TypeVar("T")


class DataSource(Generic[T], ABC):
    """Abstract base class for data sources."""

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

    @abstractmethod
    async def create(self, record: T, **kwargs) -> T:
        """Create a record.

        Args:
            record: Record to create
            **kwargs: Additional parameters

        Returns:
            T: Created record
        """
        pass

    @abstractmethod
    async def update(self, id: str, record: T, **kwargs) -> Optional[T]:
        """Update a record.

        Args:
            id: Record ID
            record: Updated record
            **kwargs: Additional parameters

        Returns:
            Optional[T]: Updated record if found and updated, None otherwise
        """
        pass

    @abstractmethod
    async def delete(self, id: str, **kwargs) -> bool:
        """Delete a record.

        Args:
            id: Record ID
            **kwargs: Additional parameters

        Returns:
            bool: True if deleted, False otherwise
        """
        pass


class OpenSearchDataSource(DataSource[T], ABC):
    """Base class for OpenSearch data sources."""

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

    async def create(self, record: T, **kwargs) -> T:
        """Create a record in OpenSearch.

        Args:
            record: Record to create
            **kwargs: Additional parameters

        Returns:
            T: Created record
        """
        id = kwargs.get("id")
        refresh = kwargs.get("refresh", False)

        # If there's a prepare_record method, use it
        doc = record
        if hasattr(self, "prepare_record"):
            doc = self.prepare_record(record)

        response = await self.client.index_document(
            index=self.index, document=doc, id=id, refresh=refresh
        )

        # Return the original record with ID updated if needed
        if hasattr(record, "id") and "_id" in response:
            record.id = response["_id"]

        return record

    async def update(self, id: str, record: T, **kwargs) -> Optional[T]:
        """Update a record in OpenSearch.

        Args:
            id: Record ID
            record: Updated record
            **kwargs: Additional parameters

        Returns:
            Optional[T]: Updated record if found and updated, None otherwise
        """
        refresh = kwargs.get("refresh", False)

        # If there's a prepare_record method, use it
        doc = record
        if hasattr(self, "prepare_record"):
            doc = self.prepare_record(record)

        try:
            await self.client.update_document(
                index=self.index, id=id, doc=doc, refresh=refresh
            )

            # Get the updated document
            return await self.get_by_id(id)
        except Exception as e:
            logger.error(f"Failed to update record: {str(e)}")
            return None

    async def delete(self, id: str, **kwargs) -> bool:
        """Delete a record from OpenSearch.

        Args:
            id: Record ID
            **kwargs: Additional parameters

        Returns:
            bool: True if deleted, False otherwise
        """
        refresh = kwargs.get("refresh", False)

        return await self.client.delete_document(
            index=self.index, id=id, refresh=refresh
        )
