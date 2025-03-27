"""Data Access Object for regulatory data (read-only operations)."""
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from ..clients.opensearch_client import OpenSearchClient, SearchResult

# Configure logging
logger = logging.getLogger(__name__)


class RegulatoryDataType(str, Enum):
    """Types of regulatory data."""

    REGULATION = "regulation"
    GUIDANCE = "guidance"
    POLICY = "policy"
    STANDARD = "standard"
    FRAMEWORKS = "framework"


class RegulatoryJurisdiction(str, Enum):
    """Regulatory jurisdictions."""

    GLOBAL = "global"
    US = "us"
    EU = "eu"
    UK = "uk"
    APAC = "apac"


@dataclass
class RegulationSearchRequest:
    """Parameters for searching regulations."""

    query_text: Optional[str] = None
    data_type: Optional[Union[RegulatoryDataType, List[RegulatoryDataType]]] = None
    jurisdiction: Optional[
        Union[RegulatoryJurisdiction, List[RegulatoryJurisdiction]]
    ] = None
    effective_date_start: Optional[datetime] = None
    effective_date_end: Optional[datetime] = None
    industry: Optional[Union[str, List[str]]] = None
    topic: Optional[Union[str, List[str]]] = None
    page: int = 1
    size: int = 20
    sort_by: str = "effective_date"
    sort_order: str = "desc"


class RegulatoryDAO:
    """Data Access Object for regulatory data (read-only)."""

    def __init__(
        self,
        opensearch_client: OpenSearchClient,
        index_prefix: str = "regulatory",
    ):
        """Initialize the DAO.

        Args:
            opensearch_client: OpenSearch client
            index_prefix: Prefix for regulatory indices
        """
        self.client = opensearch_client
        self.index_prefix = index_prefix

    def _get_index_name(self, data_type: Optional[RegulatoryDataType] = None) -> str:
        """Get the index name for the specified data type.

        Args:
            data_type: Type of regulatory data

        Returns:
            str: Index name
        """
        if data_type:
            return f"{self.index_prefix}_{data_type.value}"
        return f"{self.index_prefix}_*"

    async def search_regulations(
        self, request: RegulationSearchRequest
    ) -> SearchResult:
        """Search for regulatory documents.

        Args:
            request: Search parameters

        Returns:
            SearchResult: Search results
        """
        # Build the query
        query: Dict[str, Any] = {"bool": {"must": [], "filter": []}}

        # Full-text search
        if request.query_text:
            query["bool"]["must"].append(
                {
                    "multi_match": {
                        "query": request.query_text,
                        "fields": ["title^3", "summary^2", "content", "keywords^2"],
                    }
                }
            )

        # Data type filter
        if request.data_type:
            data_types = (
                [request.data_type]
                if isinstance(request.data_type, RegulatoryDataType)
                else request.data_type
            )
            query["bool"]["filter"].append(
                {"terms": {"data_type": [dt.value for dt in data_types]}}
            )

        # Jurisdiction filter
        if request.jurisdiction:
            jurisdictions = (
                [request.jurisdiction]
                if isinstance(request.jurisdiction, RegulatoryJurisdiction)
                else request.jurisdiction
            )
            query["bool"]["filter"].append(
                {"terms": {"jurisdiction": [j.value for j in jurisdictions]}}
            )

        # Effective date range
        if request.effective_date_start or request.effective_date_end:
            date_filter = {"range": {"effective_date": {}}}
            if request.effective_date_start:
                date_filter["range"]["effective_date"][
                    "gte"
                ] = request.effective_date_start.isoformat()
            if request.effective_date_end:
                date_filter["range"]["effective_date"][
                    "lte"
                ] = request.effective_date_end.isoformat()
            query["bool"]["filter"].append(date_filter)

        # Industry filter
        if request.industry:
            industries = (
                [request.industry]
                if isinstance(request.industry, str)
                else request.industry
            )
            query["bool"]["filter"].append({"terms": {"industries": industries}})

        # Topic filter
        if request.topic:
            topics = (
                [request.topic] if isinstance(request.topic, str) else request.topic
            )
            query["bool"]["filter"].append({"terms": {"topics": topics}})

        # If no specific criteria, match all
        if not query["bool"]["must"] and not query["bool"]["filter"]:
            query = {"match_all": {}}

        # Sorting
        sort = [{request.sort_by: {"order": request.sort_order}}]

        # Fields to return
        source_includes = [
            "id",
            "title",
            "summary",
            "data_type",
            "jurisdiction",
            "effective_date",
            "publication_date",
            "issuing_body",
            "industries",
            "topics",
            "keywords",
        ]

        # Aggregations
        aggs = {
            "data_types": {"terms": {"field": "data_type"}},
            "jurisdictions": {"terms": {"field": "jurisdiction"}},
            "industries": {"terms": {"field": "industries", "size": 20}},
            "topics": {"terms": {"field": "topics", "size": 20}},
            "effective_date_histogram": {
                "date_histogram": {
                    "field": "effective_date",
                    "calendar_interval": "quarter",
                }
            },
        }

        # Determine the index to search
        if isinstance(request.data_type, RegulatoryDataType) and not isinstance(
            request.data_type, list
        ):
            index = self._get_index_name(request.data_type)
        else:
            index = self._get_index_name()

        # Execute the search
        return await self.client.search(
            index=index,
            query=query,
            sort=sort,
            page=request.page,
            size=request.size,
            source_includes=source_includes,
            aggs=aggs,
        )

    async def get_regulation_by_id(
        self,
        regulation_id: str,
        data_type: Optional[RegulatoryDataType] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get a regulation by ID.

        Args:
            regulation_id: Regulation ID
            data_type: Type of regulatory data

        Returns:
            Optional[Dict[str, Any]]: Regulation document if found
        """
        # Try with specific data type first if provided
        if data_type:
            index = self._get_index_name(data_type)
            document = await self.client.get_document(index, regulation_id)
            if document:
                return document

        # If no data_type or document not found, try all indices
        if not data_type:
            # Try each data type
            for dt in RegulatoryDataType:
                index = self._get_index_name(dt)
                document = await self.client.get_document(index, regulation_id)
                if document:
                    return document

        return None

    async def get_related_regulations(
        self,
        regulation_id: str,
        max_results: int = 5,
    ) -> List[Dict[str, Any]]:
        """Get related regulations for a specific regulation.

        Args:
            regulation_id: Regulation ID
            max_results: Maximum number of related regulations to return

        Returns:
            List[Dict[str, Any]]: List of related regulations
        """
        # Get the original regulation
        regulation = await self.get_regulation_by_id(regulation_id)
        if not regulation:
            return []

        # Extract key information for the more-like-this query
        fields = ["title", "summary", "content", "topics", "keywords"]
        like_text = " ".join(
            [str(regulation.get(field, "")) for field in fields if field in regulation]
        )

        # Build more-like-this query
        query = {
            "bool": {
                "must": [
                    {
                        "more_like_this": {
                            "fields": ["title", "summary", "content"],
                            "like": like_text,
                            "min_term_freq": 1,
                            "max_query_terms": 20,
                            "min_doc_freq": 1,
                        }
                    }
                ],
                "must_not": [{"term": {"id": regulation_id}}],
            }
        }

        # Add filters based on original document
        if "jurisdiction" in regulation:
            query["bool"]["should"] = [
                {"term": {"jurisdiction": regulation["jurisdiction"]}}
            ]
            query["bool"]["minimum_should_match"] = 1

        # If there are industries, boost documents with the same industries
        if "industries" in regulation and regulation["industries"]:
            query["bool"]["should"].append(
                {"terms": {"industries": regulation["industries"]}}
            )

        # Search for related regulations
        source_includes = [
            "id",
            "title",
            "summary",
            "data_type",
            "jurisdiction",
            "effective_date",
            "issuing_body",
        ]

        result = await self.client.search(
            index=self._get_index_name(),
            query=query,
            size=max_results,
            source_includes=source_includes,
        )

        return result.hits

    async def get_regulations_by_topic(
        self,
        topic: str,
        page: int = 1,
        size: int = 20,
    ) -> SearchResult:
        """Get regulations by topic.

        Args:
            topic: Topic to search for
            page: Page number
            size: Page size

        Returns:
            SearchResult: Search results
        """
        query = {"bool": {"must": [{"term": {"topics": topic}}]}}

        source_includes = [
            "id",
            "title",
            "summary",
            "data_type",
            "jurisdiction",
            "effective_date",
            "issuing_body",
        ]

        return await self.client.search(
            index=self._get_index_name(),
            query=query,
            page=page,
            size=size,
            source_includes=source_includes,
        )

    async def get_latest_regulations(
        self,
        days: int = 30,
        jurisdiction: Optional[RegulatoryJurisdiction] = None,
        page: int = 1,
        size: int = 20,
    ) -> SearchResult:
        """Get latest regulations.

        Args:
            days: Number of days to look back
            jurisdiction: Jurisdiction to filter by
            page: Page number
            size: Page size

        Returns:
            SearchResult: Search results
        """
        query = {
            "bool": {
                "filter": [{"range": {"publication_date": {"gte": f"now-{days}d/d"}}}]
            }
        }

        if jurisdiction:
            query["bool"]["filter"].append(
                {"term": {"jurisdiction": jurisdiction.value}}
            )

        source_includes = [
            "id",
            "title",
            "summary",
            "data_type",
            "jurisdiction",
            "effective_date",
            "publication_date",
            "issuing_body",
        ]

        sort = [{"publication_date": {"order": "desc"}}]

        return await self.client.search(
            index=self._get_index_name(),
            query=query,
            sort=sort,
            page=page,
            size=size,
            source_includes=source_includes,
        )
