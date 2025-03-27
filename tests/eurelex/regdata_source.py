"""Regulations data source implementation (read-only)."""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from ..clients.opensearch_client import OpenSearchClient, SearchResult
from .data_source import OpenSearchReadOnlyDataSource
from .regulatory_document import RegulationDocument

# Configure logging
logger = logging.getLogger(__name__)


class RegulationsDataSource(OpenSearchReadOnlyDataSource[RegulationDocument]):
    """Regulations data source using OpenSearch (read-only)."""

    def __init__(
        self,
        client: OpenSearchClient,
        index_prefix: str = "regulations",
    ):
        """Initialize the data source.

        Args:
            client: OpenSearch client
            index_prefix: Prefix for regulations indices
        """
        super().__init__(client, f"{index_prefix}-*")
        self.index_prefix = index_prefix

    def _get_index(self, language: Optional[str] = None) -> str:
        """Get index name for language.

        Args:
            language: Document language

        Returns:
            str: Index name
        """
        if language:
            return f"{self.index_prefix}-{language}"
        return self.index

    def transform_record(self, record: Dict[str, Any]) -> RegulationDocument:
        """Transform record from OpenSearch to RegulationDocument.

        Args:
            record: Record from OpenSearch

        Returns:
            RegulationDocument: Transformed document
        """
        return RegulationDocument.from_dict(record)

    async def search_by_text(
        self,
        text: str,
        language: Optional[str] = None,
        page: int = 1,
        size: int = 20,
    ) -> List[RegulationDocument]:
        """Search for regulations by text.

        Args:
            text: Text to search for
            language: Document language
            page: Page number
            size: Page size

        Returns:
            List[RegulationDocument]: Matching documents
        """
        # Build the query
        query = {
            "bool": {
                "must": [
                    {
                        "multi_match": {
                            "query": text,
                            "fields": ["title^3", "full_name^2", "name"],
                        }
                    }
                ],
                "filter": [],
            }
        }

        # Add language filter if specified
        if language:
            query["bool"]["filter"].append({"term": {"language": language}})

        # Set the index
        index = self._get_index(language)
        original_index = self.index
        self.index = index

        try:
            result = await self.search(query, page=page, size=size)
            return result.hits
        finally:
            self.index = original_index

    async def get_by_celex(
        self,
        celex: str,
        language: str = "en",
        kind: Optional[str] = None,
        page: int = 1,
        size: int = 100,
    ) -> List[RegulationDocument]:
        """Get regulations by CELEX identifier.

        Args:
            celex: CELEX identifier
            language: Document language
            kind: Kind of document (article, section, etc.)
            page: Page number
            size: Page size

        Returns:
            List[RegulationDocument]: Matching documents
        """
        # Build the query
        query = {
            "bool": {
                "filter": [{"term": {"celex": celex}}, {"term": {"language": language}}]
            }
        }

        # Add kind filter if specified
        if kind:
            query["bool"]["filter"].append({"term": {"kind": kind}})

        # Set the index
        index = self._get_index(language)
        original_index = self.index
        self.index = index

        # Set sorting by position for hierarchical order
        sort = [{"position": {"order": "asc"}}]

        try:
            result = await self.search(query, page=page, size=size, sort=sort)
            return result.hits
        finally:
            self.index = original_index

    async def get_by_kind(
        self,
        kind: str,
        language: Optional[str] = None,
        legally_binding: Optional[bool] = None,
        page: int = 1,
        size: int = 20,
    ) -> List[RegulationDocument]:
        """Get regulations by kind.

        Args:
            kind: Kind of document (article, section, etc.)
            language: Document language
            legally_binding: Whether document is legally binding
            page: Page number
            size: Page size

        Returns:
            List[RegulationDocument]: Matching documents
        """
        # Build the query
        query = {"bool": {"filter": [{"term": {"kind": kind}}]}}

        # Add filters
        if language:
            query["bool"]["filter"].append({"term": {"language": language}})

        if legally_binding is not None:
            query["bool"]["filter"].append(
                {"term": {"legally_binding": legally_binding}}
            )

        # Set the index
        index = self._get_index(language)
        original_index = self.index
        self.index = index

        try:
            result = await self.search(query, page=page, size=size)
            return result.hits
        finally:
            self.index = original_index

    async def get_by_wildcard_id(
        self,
        id_pattern: str,
        language: Optional[str] = None,
        page: int = 1,
        size: int = 100,
    ) -> List[RegulationDocument]:
        """Get regulations by ID pattern using wildcard.

        Args:
            id_pattern: ID pattern with wildcards (*)
            language: Document language
            page: Page number
            size: Page size

        Returns:
            List[RegulationDocument]: Matching documents
        """
        # Build wildcard query
        query = {"wildcard": {"id": {"value": id_pattern}}}

        # Set the index
        index = self._get_index(language)
        original_index = self.index
        self.index = index

        # Sort by position for hierarchical order
        sort = [{"position": {"order": "asc"}}]

        try:
            result = await self.search(query, page=page, size=size, sort=sort)
            return result.hits
        finally:
            self.index = original_index

    async def get_related_articles(
        self,
        regulation_id: str,
        language: Optional[str] = None,
    ) -> List[RegulationDocument]:
        """Get related articles for a regulation.

        Args:
            regulation_id: Regulation ID
            language: Document language

        Returns:
            List[RegulationDocument]: Related articles
        """
        # Extract document base from ID
        if "/" in regulation_id:
            base_parts = []
            # Try to extract doc and lang parts
            for part in regulation_id.split("/")[:2]:
                if part.startswith("doc=") or part.startswith("lang="):
                    base_parts.append(part)

            if base_parts:
                base_id = "/".join(base_parts)
                id_pattern = f"{base_id}/*art=*"
            else:
                id_parts = regulation_id.split("/")
                id_pattern = f"{id_parts[0]}/*art=*"
        else:
            id_pattern = f"{regulation_id}/*art=*"

        # Get articles using wildcard pattern
        return await self.get_by_wildcard_id(
            id_pattern=id_pattern,
            language=language,
            size=500,  # Articles can be numerous
        )

    async def get_document_hierarchy(
        self,
        document_id: str,
        language: Optional[str] = None,
    ) -> Dict[str, List[RegulationDocument]]:
        """Get document hierarchy (parts, titles, chapters, sections, articles).

        Args:
            document_id: Document base ID
            language: Document language

        Returns:
            Dict[str, List[RegulationDocument]]: Document parts by kind
        """
        # Extract base document ID pattern
        if "/" in document_id:
            # Get first part (likely doc=...)
            base_id = document_id.split("/")[0]
            id_pattern = f"{base_id}/*"
        else:
            id_pattern = f"{document_id}/*"

        # Get all parts
        documents = await self.get_by_wildcard_id(
            id_pattern=id_pattern,
            language=language,
            size=1000,  # Large enough for a complete document
        )

        # Group by kind
        hierarchy = {}
        for doc in documents:
            kind = doc.kind
            if kind not in hierarchy:
                hierarchy[kind] = []
            hierarchy[kind].append(doc)

        return hierarchy
