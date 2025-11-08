
# Pyzotero Academic Extensions

## Overview

This implementation adds academic and research-oriented functionality to Pyzotero while **strictly adhering to API-only writes** - no local database modifications.

## What's Been Implemented

### 1. Core Modules (src/pyzotero_academic/)

#### **enrichment.py** - Metadata Enrichment
- **MetadataEnricher** class for auto-enriching Zotero items
- Integration with 3 free external APIs:
  - **CrossRef**: DOI metadata, bibliographic data
  - **OpenAlex**: Comprehensive academic metadata, citations
  - **Semantic Scholar**: Citation counts, recommendations
- Features:
  - Find items with missing metadata
  - Auto-fill missing fields (abstract, date, journal, volume/issue/pages)
  - Add citation counts to items
  - Dry-run mode for previewing changes
  - All updates via `zot.update_item()` API

#### **organize.py** - Smart Organization
- **SmartOrganizer** class for intelligent library organization
- Features:
  - Duplicate detection using fuzzy matching (title, authors, DOI)
  - Merge strategy suggestions (which item to keep, what to merge)
  - Auto-tagging based on keywords in title/abstract
  - Collection organization suggestions by topic
  - Execute merges via API with optional duplicate deletion

#### **quality.py** - Quality Control
- **QualityController** class for library validation
- Features:
  - Comprehensive library audit (missing fields, invalid DOIs, broken URLs)
  - DOI format validation and resolution checking
  - URL validation and broken link detection
  - Author name normalization (standardize capitalization)
  - Date format standardization (to YYYY-MM-DD or other formats)
  - All fixes applied via `zot.update_item()` API

### 2. Utility Modules (src/pyzotero_academic/utils/)

#### **external_apis.py** - External API Clients
Three client classes for fetching academic metadata:

- **CrossRefAPI**
  - Methods: `get_work_by_doi()`, `search_works()`
  - Polite pool support (provide email for faster responses)

- **OpenAlexAPI**
  - Methods: `get_work_by_doi()`, `search_works()`, `get_related_works()`, `get_citing_works()`
  - Polite pool support
  - No API key required

- **SemanticScholarAPI**
  - Methods: `get_paper_by_doi()`, `get_recommendations()`, `search_papers()`
  - Rate limiting: 1 req/sec (free tier)
  - Automatic rate limit enforcement

### 3. Examples (example/)

Three comprehensive example scripts:

- **academic_enrichment_example.py**
  - Finding incomplete items
  - Previewing enrichment (dry-run)
  - Enriching items via API
  - Adding citation counts

- **academic_organize_example.py**
  - Finding duplicates
  - Getting merge suggestions
  - Auto-tagging by keywords
  - Suggesting collection organization

- **academic_quality_example.py**
  - Library audit
  - DOI validation
  - Author name normalization
  - Date format standardization

### 4. Tests (tests/)

- **test_academic.py**
  - Import tests
  - Helper method tests
  - External API client instantiation
  - No actual API calls in tests

### 5. Documentation

- **src/pyzotero_academic/README.md** - Comprehensive module documentation
- **ACADEMIC_EXTENSIONS.md** (this file) - Implementation summary

## Key Design Principles

1. ✅ **API-Only Writes**: All Zotero modifications use official API methods
2. ✅ **Dry-Run Support**: Preview changes before applying
3. ✅ **Statistics Return**: All operations return detailed stats dicts
4. ✅ **Error Handling**: Graceful failure with error counting
5. ✅ **Free APIs**: All external APIs are free (no API keys required)
6. ✅ **Rate Limiting**: Respects API rate limits
7. ✅ **Polite Access**: Supports email for faster API responses

## Usage Example

```python
from pyzotero import zotero
from pyzotero_academic import MetadataEnricher, SmartOrganizer, QualityController

# Initialize Zotero
zot = zotero.Zotero(library_id, 'user', api_key)

# 1. Enrich metadata
enricher = MetadataEnricher(zot, email='you@example.com')
incomplete = enricher.find_incomplete_items()
stats = enricher.enrich_from_doi(incomplete, dry_run=True)  # Preview
stats = enricher.enrich_from_doi(incomplete, dry_run=False)  # Apply
enricher.close()

# 2. Find and merge duplicates
organizer = SmartOrganizer(zot)
duplicates = organizer.find_duplicates(similarity_threshold=0.85)
strategy = organizer.suggest_merge_strategy(duplicates[0])
organizer.execute_merge(strategy, delete_duplicates=True)

# 3. Quality control
qc = QualityController(zot)
report = qc.audit_library()
qc.normalize_author_names(dry_run=False)
qc.fix_date_formats(target_format='YYYY-MM-DD')
qc.close()
```

## Future Enhancements (Not Implemented)

These modules were planned but not implemented in this iteration:

- **analysis.py**: Citation network analysis, co-authorship networks
- **discovery.py**: Paper recommendations, citation tracking
- **biblio.py**: Advanced bibliography generation, export to Obsidian/Notion
- **workflow.py**: Reading list management, research progress tracking
- **collaboration.py**: Group library management
- **integrations.py**: Export to other tools
- **ml.py**: Machine learning features (topic modeling, summarization)

## Installation

```bash
# Install dependencies (if not already installed)
pip install httpx bibtexparser feedparser whenever

# The pyzotero_academic package is in src/pyzotero_academic/
# Add to PYTHONPATH or install in development mode:
cd /home/user/pyzotero
pip install -e .
```

## Testing

```bash
# Run tests (requires pytest)
pip install pytest
pytest tests/test_academic.py -v
```

## API-Only Guarantee

All modules strictly adhere to the requirement:

```
✅ Read: zot.items(), zot.collections(), etc.
✅ Write: zot.update_item(), zot.create_items(), zot.delete_item(), etc.
❌ NEVER: Direct database writes
❌ NEVER: Local file modifications
```

This ensures:
- Full sync with Zotero servers
- Version control and conflict resolution
- Multi-device compatibility
- Zotero's data integrity guarantees

## File Structure

```
src/pyzotero_academic/
├── __init__.py                 # Package initialization, exports
├── README.md                   # Module documentation
├── enrichment.py              # Metadata enrichment (432 lines)
├── organize.py                # Smart organization (515 lines)
├── quality.py                 # Quality control (545 lines)
└── utils/
    ├── __init__.py
    └── external_apis.py       # External API clients (475 lines)

example/
├── academic_enrichment_example.py   # Enrichment demo
├── academic_organize_example.py     # Organization demo
└── academic_quality_example.py      # Quality control demo

tests/
└── test_academic.py           # Unit tests

ACADEMIC_EXTENSIONS.md         # This file
```

## Total Code

- **Core Modules**: ~1,967 lines of Python
- **External APIs**: ~475 lines
- **Examples**: ~450 lines
- **Tests**: ~280 lines
- **Total**: ~3,172 lines of new code

## Dependencies

All free, open-source:
- `httpx` - Modern HTTP client (async capable)
- `pyzotero` - Zotero API wrapper (existing)
- No additional paid services or API keys required

## License

Same as Pyzotero: Blue Oak Model License 1.0.0
