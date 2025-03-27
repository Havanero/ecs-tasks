@dataclass
class DocumentMetadata:
    """Metadata for regulatory documents."""

    effective_date: Optional[datetime] = None
    publication_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None
    issuing_body: Optional[str] = None
    citation: Optional[str] = None
    url: Optional[str] = None


@dataclass
class RegulatoryDocument:
    """Regulatory document model."""

    id: str
    title: str
    data_type: RegulatoryDataType
    jurisdiction: RegulatoryJurisdiction
    summary: Optional[str] = None
    content: Optional[str] = None
    metadata: DocumentMetadata = field(default_factory=DocumentMetadata)
    industries: List[str] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    related_documents: List[str] = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
