@dataclass
class RegulationSearchRequest:
    """Request for searching regulations."""

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
    # ...

    async def search_regulations(
        self, request: RegulationSearchRequest
    ) -> SearchResult:
        """Search for regulatory documents.

        Args:
            request: Search request parameters

        Returns:
            SearchResult: Search results
        """
        # Build the query using request parameters
        # ...
