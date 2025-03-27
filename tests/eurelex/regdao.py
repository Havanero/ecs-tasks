"""Data Access Object for regulations data."""
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from ..clients.opensearch_client import OpenSearchClient, SearchResult
from ..sources.regulatory_document import RegulationDocument

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class RegulationSearchRequest:
    """Parameters for searching regulations."""

    query_text: Optional[str] = None
    kind: Optional[str] = None
    celex: Optional[str] = None
    document_type: Optional[str] = None
    language: Optional[str] = None
    legally_binding: Optional[bool] = None
    document_date_start: Optional[str] = None
    document_date_end: Optional[str] = None
    page: int = 1
    size: int = 20
    sort_by: str = "position"
    sort_order: str = "asc"


class RegulationsDAO:
    """Data Access Object for regulations data."""

    def __init__(
        self,
        opensearch_client: OpenSearchClient,
        index_prefix: str = "regulations",
    ):
        """Initialize the DAO.

        Args:
            opensearch_client: OpenSearch client
            index_prefix: Prefix for regulations indices
        """
        self.client = opensearch_client
        self.index_prefix = index_prefix

    def _get_index_name(self, language: Optional[str] = None) -> str:
        """Get the index name for the specified language.

        Args:
            language: Document language

        Returns:
            str: Index name
        """
        if language:
            return f"{self.index_prefix}-{language}"
        return f"{self.index_prefix}-*"

    async def search_regulations(
        self, request: RegulationSearchRequest
    ) -> SearchResult:
        """Search for regulations.

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
                        "fields": ["title^3", "full_name^2", "name"],
                    }
                }
            )

        # Kind filter
        if request.kind:
            query["bool"]["filter"].append({"term": {"kind": request.kind}})

        # CELEX filter
        if request.celex:
            query["bool"]["filter"].append({"term": {"celex": request.celex}})

        # Document type filter
        if request.document_type:
            query["bool"]["filter"].append(
                {"term": {"document_type": request.document_type}}
            )

        # Language filter
        if request.language:
            query["bool"]["filter"].append({"term": {"language": request.language}})

        # Legally binding filter
        if request.legally_binding is not None:
            query["bool"]["filter"].append(
                {"term": {"legally_binding": request.legally_binding}}
            )

        # Document date range
        if request.document_date_start or request.document_date_end:
            date_filter = {"range": {"document_date": {}}}
            if request.document_date_start:
                date_filter["range"]["document_date"][
                    "gte"
                ] = request.document_date_start
            if request.document_date_end:
                date_filter["range"]["document_date"]["lte"] = request.document_date_end
            query["bool"]["filter"].append(date_filter)

        # If no specific criteria, match all
        if not query["bool"]["must"] and not query["bool"]["filter"]:
            query = {"match_all": {}}

        # Sorting
        sort = [{request.sort_by: {"order": request.sort_order}}]

        # Fields to return
        source_includes = [
            "id",
            "kind",
            "title",
            "name",
            "full_name",
            "celex",
            "document_type",
            "language",
            "document_date",
            "legally_binding",
            "enforced_date_range",
            "depth",
            "position",
            "eur_lex_url",
        ]

        # Determine the index to search
        index = self._get_index_name(request.language)

        # Execute the search
        return await self.client.search(
            index=index,
            query=query,
            sort=sort,
            page=request.page,
            size=request.size,
            source_includes=source_includes,
        )

    async def get_regulation_by_id(
        self,
        regulation_id: str,
        language: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get a regulation by exact ID.

        Args:
            regulation_id: Regulation ID
            language: Document language

        Returns:
            Optional[Dict[str, Any]]: Regulation document if found
        """
        index = self._get_index_name(language)
        return await self.client.get_document(index, regulation_id)

    async def get_regulations_by_wildcard_id(
        self,
        id_pattern: str,
        language: Optional[str] = None,
        page: int = 1,
        size: int = 100,
    ) -> SearchResult:
        """Get regulations by ID pattern using wildcard.

        Args:
            id_pattern: ID pattern with wildcards
            language: Document language
            page: Page number
            size: Page size

        Returns:
            SearchResult: Search results
        """
        # Build wildcard query
        query = {"wildcard": {"id": {"value": id_pattern}}}

        index = self._get_index_name(language)

        # Execute the search
        return await self.client.search(
            index=index,
            query=query,
            page=page,
            size=size,
            sort=[{"position": {"order": "asc"}}],
        )

    async def get_related_regulations(
        self,
        regulation_id: str,
        language: Optional[str] = None,
        max_results: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get related regulations based on shared ID components.

        For example, if regulation_id is:
        "doc=02013R0575-20190101/lang=en/part=00003/title=00007/chap=00015/sec=00029/ssec=00022/art=00220"

        This will find all regulations with:
        "doc=02013R0575-20190101/lang=en*"

        Args:
            regulation_id: Regulation ID
            language: Document language
            max_results: Maximum number of results

        Returns:
            List[Dict[str, Any]]: List of related regulations
        """
        # Get base document ID pattern
        if "/" in regulation_id:
            # Extract the document base (everything before the first slash)
            base_segments = []
            segments = regulation_id.split("/")

            # Include document identifier and language
            for segment in segments[:2]:  # Usually doc= and lang= segments
                if segment.startswith("doc=") or segment.startswith("lang="):
                    base_segments.append(segment)

            if base_segments:
                id_pattern = "/".join(base_segments) + "/*"
            else:
                id_pattern = segments[0] + "/*"
        else:
            id_pattern = regulation_id + "/*"

        # Search for related documents
        result = await self.get_regulations_by_wildcard_id(
            id_pattern=id_pattern, language=language, size=max_results
        )

        return result.hits

    async def get_regulation_hierarchy(
        self,
        celex: str,
        language: str = "en",
        page: int = 1,
        size: int = 1000,
    ) -> SearchResult:
        """Get all parts of a regulation by CELEX identifier.

        Args:
            celex: CELEX identifier
            language: Document language
            page: Page number
            size: Page size

        Returns:
            SearchResult: Search results
        """
        # Build query for the specific CELEX identifier
        query = {
            "bool": {
                "filter": [{"term": {"celex": celex}}, {"term": {"language": language}}]
            }
        }

        index = self._get_index_name(language)

        # Execute the search with sorting by position for hierarchical order
        return await self.client.search(
            index=index,
            query=query,
            page=page,
            size=size,
            sort=[{"position": {"order": "asc"}}],
        )
