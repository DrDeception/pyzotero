"""Pyzotero Academic Extensions.

This package extends Pyzotero with academic and research-oriented functionality.

All modifications to Zotero are performed via the Zotero API only - no local
database writes are performed.

Modules:
    enrichment: Metadata enhancement from external sources
    organize: Smart organization and duplicate detection
    quality: Library quality control and validation

Classes:
    MetadataEnricher: Enrich items with metadata from external sources
    SmartOrganizer: Duplicate detection and smart organization
    QualityController: Library quality control and validation
"""

__version__ = "0.1.0"
__author__ = "Pyzotero Academic Contributors"

# Import main classes for convenience
from pyzotero_academic.enrichment import MetadataEnricher
from pyzotero_academic.organize import SmartOrganizer
from pyzotero_academic.quality import QualityController

__all__ = [
    "MetadataEnricher",
    "SmartOrganizer",
    "QualityController",
]
