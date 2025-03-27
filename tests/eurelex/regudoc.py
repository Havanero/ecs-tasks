"""Regulatory document model for regulation data."""
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class DateRange:
    """Date range model for enforcement periods."""

    gte: Optional[str] = None
    lte: Optional[str] = None


@dataclass
class RegulationDocument:
    """Regulation document model based on the actual structure."""

    id: str
    kind: str  # article, chapter, section, etc.
    title: str
    name: str
    full_name: str
    celex: str
    document_type: str
    language: str
    cellar_id: Optional[str] = None
    formex_uri: Optional[str] = None
    document_date: Optional[str] = None
    eur_lex_url: Optional[str] = None
    legally_binding: bool = False
    depth: int = -1
    position: int = 0
    enforced_date_range: Optional[DateRange] = None
    creation_datetime: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RegulationDocument":
        """Create RegulationDocument from dictionary.

        Args:
            data: Dictionary containing document data

        Returns:
            RegulationDocument: Created document
        """
        # Create a copy to avoid modifying the input
        doc_dict = data.copy()

        # Handle date range special case
        enforced_date_range = None
        if "enforced_date_range" in doc_dict:
            range_data = doc_dict.pop("enforced_date_range")
            if isinstance(range_data, dict):
                enforced_date_range = DateRange(**range_data)

        # Create document
        return cls(**doc_dict, enforced_date_range=enforced_date_range)

    def to_dict(self) -> Dict[str, Any]:
        """Convert document to dictionary.

        Returns:
            Dict[str, Any]: Dictionary representation
        """
        result = {
            "id": self.id,
            "kind": self.kind,
            "title": self.title,
            "name": self.name,
            "full_name": self.full_name,
            "celex": self.celex,
            "document_type": self.document_type,
            "language": self.language,
            "depth": self.depth,
            "position": self.position,
            "legally_binding": self.legally_binding,
        }

        # Add optional fields if present
        if self.cellar_id:
            result["cellar_id"] = self.cellar_id
        if self.formex_uri:
            result["formex_uri"] = self.formex_uri
        if self.document_date:
            result["document_date"] = self.document_date
        if self.eur_lex_url:
            result["eur_lex_url"] = self.eur_lex_url
        if self.creation_datetime:
            result["creation_datetime"] = self.creation_datetime

        # Add enforced date range if present
        if self.enforced_date_range:
            result["enforced_date_range"] = {
                "gte": self.enforced_date_range.gte,
                "lte": self.enforced_date_range.lte,
            }

        return result

    @property
    def document_id_prefix(self) -> str:
        """Get the prefix part of the document ID before any slashes.

        Returns:
            str: Document ID prefix
        """
        if "/" in self.id:
            return self.id.split("/")[0]
        return self.id

    @property
    def document_parts(self) -> Dict[str, str]:
        """Parse the document ID into its component parts.

        Returns:
            Dict[str, str]: Dictionary of document parts
        """
        parts = {}
        if "/" not in self.id:
            return parts

        segments = self.id.split("/")
        for segment in segments:
            if "=" in segment:
                key, value = segment.split("=", 1)
                parts[key] = value

        return parts
