"""Regulatory data source implementation (read-only)."""
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from ..clients.opensearch_client import OpenSearchClient, SearchResult
from ..dao.regulatory_dao import RegulatoryDataType, RegulatoryJurisdiction
from .data_source import OpenSearchReadOnlyDataSource

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class RegulatoryDocument:
    """Regulatory document model."""

    id: str
    title: str
    data_type: RegulatoryDataType
    jurisdiction: RegulatoryJurisdiction
    summary: Optional[str] = None
    content: Optional[str] = None
    effective_date: Optional[datetime] = None
    publication_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None
    issuing_body: Optional[str] = None
    citation: Optional[str] = None
    url: Optional[str] = None
    industries: List[str] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    related_documents: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RegulatoryDocument":
        """Create from dictionary."""
        # Create a copy to avoid modifying the input
        doc_dict = data.copy()

        # Convert string values to enums
        if "data_type" in doc_dict and isinstance(doc_dict["data_type"], str):
            doc_dict["data_type"] = RegulatoryDataType(doc_dict["data_type"])

        if "jurisdiction" in doc_dict and isinstance(doc_dict["jurisdiction"], str):
            doc_dict["jurisdiction"] = RegulatoryJurisdiction(doc_dict["jurisdiction"])

        # Convert ISO format strings to datetime objects
        for date_field in ["effective_date", "publication_date", "expiration_date"]:
            if doc_dict.get(date_field) and isinstance(doc_dict[date_field], str):
                try:
                    doc_dict[date_field] = datetime.fromisoformat(doc_dict[date_field])
                except ValueError:
                    # If the format isn't ISO, skip conversion
                    pass

        return cls(**doc_dict)


class RegulatoryDataSource(OpenSearchReadOnlyDataSource[RegulatoryDocument]):
    """Regulatory data source using OpenSearch (read-only)."""

    def __init__(
        self,
        client: OpenSearchClient,
        index_prefix: str = "regulatory",
    ):
        """Initialize the data source.

        Args:
            client: OpenSearch client
            index_prefix: Prefix for regulatory indices
        """
        super().__init__(client, f"{index_prefix}_*")
        self.index_prefix = index_prefix

    def _get_index(self, data_type: Optional[RegulatoryDataType] = None) -> str:
        """Get index name for data type.

        Args:
            data_type: Regulatory data type

        Returns:
            str: Index name
        """
        if data_type:
            return f"{self.index_prefix}_{data_type.value}"
        return self.index

    def transform_record(self, record: Dict[str, Any]) -> RegulatoryDocument:
        """Transform record from OpenSearch to RegulatoryDocument.

        Args:
            record: Record from OpenSearch

        Returns:
            RegulatoryDocument: Transformed document
        """
        return RegulatoryDocument.from_dict(record)

    async def search_by_text(
        self,
        text: str,
        data_type: Optional[RegulatoryDataType] = None,
        jurisdiction: Optional[RegulatoryJurisdiction] = None,
        page: int = 1,
        size: int = 20,
    ) -> List[RegulatoryDocument]:
        """Search for regulatory documents by text.

        Args:
            text: Text to search for
            data_type: Data type to filter by
            jurisdiction: Jurisdiction to filter by
            page: Page number
            size: Page size

        Returns:
            List[RegulatoryDocument]: Matching documents
        """
        # Build the query
        query = {
            "bool": {
                "must": [
                    {
                        "multi_match": {
                            "query": text,
                            "fields": ["title^3", "summary^2", "content", "keywords^2"],
                        }
                    }
                ],
                "filter": [],
            }
        }

        # Add filters
        if data_type:
            query["bool"]["filter"].append({"term": {"data_type": data_type.value}})

        if jurisdiction:
            query["bool"]["filter"].append(
                {"term": {"jurisdiction": jurisdiction.value}}
            )

        # Set the index
        index = self._get_index(data_type)
        original_index = self.index
        self.index = index

        try:
            result = await self.search(query, page=page, size=size)
            return result.hits
        finally:
            self.index = original_index

    async def get_by_jurisdiction(
        self,
        jurisdiction: RegulatoryJurisdiction,
        data_type: Optional[RegulatoryDataType] = None,
        page: int = 1,
        size: int = 20,
        sort_field: str = "effective_date",
        sort_order: str = "desc",
    ) -> List[RegulatoryDocument]:
        """Get regulatory documents by jurisdiction.

        Args:
            jurisdiction: Jurisdiction to filter by
            data_type: Data type to filter by
            page: Page number
            size: Page size
            sort_field: Field to sort by
            sort_order: Sort order

        Returns:
            List[RegulatoryDocument]: Matching documents
        """
        # Build the query
        query = {"bool": {"filter": [{"term": {"jurisdiction": jurisdiction.value}}]}}

        # Add data type filter if specified
        if data_type:
            query["bool"]["filter"].append({"term": {"data_type": data_type.value}})

        # Set the index
        index = self._get_index(data_type)
        original_index = self.index
        self.index = index

        # Set sorting
        sort = [{sort_field: {"order": sort_order}}]

        try:
            result = await self.search(query, page=page, size=size, sort=sort)
            return result.hits
        finally:
            self.index = original_index

    async def get_by_effective_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        data_type: Optional[RegulatoryDataType] = None,
        jurisdiction: Optional[RegulatoryJurisdiction] = None,
        page: int = 1,
        size: int = 20,
    ) -> List[RegulatoryDocument]:
        """Get regulatory documents by effective date range.

        Args:
            start_date: Start date
            end_date: End date
            data_type: Data type to filter by
            jurisdiction: Jurisdiction to filter by
            page: Page number
            size: Page size

        Returns:
            List[RegulatoryDocument]: Matching documents
        """
        # Build the query
        query = {
            "bool": {
                "filter": [
                    {
                        "range": {
                            "effective_date": {
                                "gte": start_date.isoformat(),
                                "lte": end_date.isoformat(),
                            }
                        }
                    }
                ]
            }
        }

        # Add filters
        if data_type:
            query["bool"]["filter"].append({"term": {"data_type": data_type.value}})

        if jurisdiction:
            query["bool"]["filter"].append(
                {"term": {"jurisdiction": jurisdiction.value}}
            )

        # Set the index
        index = self._get_index(data_type)
        original_index = self.index
        self.index = index

        # Set sorting
        sort = [{"effective_date": {"order": "desc"}}]

        try:
            result = await self.search(query, page=page, size=size, sort=sort)
            return result.hits
        finally:
            self.index = original_index

    async def get_by_topics(
        self,
        topics: List[str],
        match_all: bool = False,
        data_type: Optional[RegulatoryDataType] = None,
        jurisdiction: Optional[RegulatoryJurisdiction] = None,
        page: int = 1,
        size: int = 20,
    ) -> List[RegulatoryDocument]:
        """Get regulatory documents by topics.

        Args:
            topics: Topics to filter by
            match_all: Whether to match all topics (AND) or any topic (OR)
            data_type: Data type to filter by
            jurisdiction: Jurisdiction to filter by
            page: Page number
            size: Page size

        Returns:
            List[RegulatoryDocument]: Matching documents
        """
        # Build the query
        query = {"bool": {"filter": []}}

        # Add topic filter
        if match_all:
            # Must match all topics (AND)
            for topic in topics:
                query["bool"]["filter"].append({"term": {"topics": topic}})
        else:
            # Match any topic (OR)
            query["bool"]["filter"].append({"terms": {"topics": topics}})

        # Add other filters
        if data_type:
            query["bool"]["filter"].append({"term": {"data_type": data_type.value}})

        if jurisdiction:
            query["bool"]["filter"].append(
                {"term": {"jurisdiction": jurisdiction.value}}
            )

        # Set the index
        index = self._get_index(data_type)
        original_index = self.index
        self.index = index

        try:
            result = await self.search(query, page=page, size=size)
            return result.hits
        finally:
            self.index = original_index

    async def get_by_industry(
        self,
        industry: str,
        data_type: Optional[RegulatoryDataType] = None,
        jurisdiction: Optional[RegulatoryJurisdiction] = None,
        page: int = 1,
        size: int = 20,
    ) -> List[RegulatoryDocument]:
        """Get regulatory documents by industry.

        Args:
            industry: Industry to filter by
            data_type: Data type to filter by
            jurisdiction: Jurisdiction to filter by
            page: Page number
            size: Page size

        Returns:
            List[RegulatoryDocument]: Matching documents
        """
        # Build the query
        query = {"bool": {"filter": [{"term": {"industries": industry}}]}}

        # Add other filters
        if data_type:
            query["bool"]["filter"].append({"term": {"data_type": data_type.value}})

        if jurisdiction:
            query["bool"]["filter"].append(
                {"term": {"jurisdiction": jurisdiction.value}}
            )

        # Set the index
        index = self._get_index(data_type)
        original_index = self.index
        self.index = index

        try:
            result = await self.search(query, page=page, size=size)
            return result.hits
        finally:
            self.index = original_index

    async def get_by_issuing_body(
        self,
        issuing_body: str,
        data_type: Optional[RegulatoryDataType] = None,
        jurisdiction: Optional[RegulatoryJurisdiction] = None,
        page: int = 1,
        size: int = 20,
    ) -> List[RegulatoryDocument]:
        """Get regulatory documents by issuing body.

        Args:
            issuing_body: Issuing body to filter by
            data_type: Data type to filter by
            jurisdiction: Jurisdiction to filter by
            page: Page number
            size: Page size

        Returns:
            List[RegulatoryDocument]: Matching documents
        """
        # Build the query
        query = {"bool": {"filter": [{"term": {"issuing_body.keyword": issuing_body}}]}}

        # Add other filters
        if data_type:
            query["bool"]["filter"].append({"term": {"data_type": data_type.value}})

        if jurisdiction:
            query["bool"]["filter"].append(
                {"term": {"jurisdiction": jurisdiction.value}}
            )

        # Set the index
        index = self._get_index(data_type)
        original_index = self.index
        self.index = index

        try:
            result = await self.search(query, page=page, size=size)
            return result.hits
        finally:
            self.index = original_index
