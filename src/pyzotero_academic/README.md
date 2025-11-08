# Pyzotero Academic Extensions

Academic and research-oriented extensions for Pyzotero.

**All modifications to Zotero are performed via the Zotero API only** - no local database writes.

## Features

### 1. Metadata Enrichment (`enrichment.py`)

Automatically enrich your Zotero library with missing metadata from external sources:

- **External API Integration**: CrossRef, OpenAlex, Semantic Scholar
- **Auto-fill missing fields**: Abstract, publication date, journal, volume/issue/pages, ISSN
- **Citation counts**: Track citation counts from multiple sources
- **Dry-run mode**: Preview changes before applying

**Example:**

```python
from pyzotero import zotero
from pyzotero_academic.enrichment import MetadataEnricher

zot = zotero.Zotero(library_id, 'user', api_key)
enricher = MetadataEnricher(zot, email='your.email@example.com')

# Find items missing metadata
incomplete = enricher.find_incomplete_items(
    require_fields=['DOI', 'abstractNote', 'date']
)

# Preview enrichment
stats = enricher.enrich_from_doi(incomplete, dry_run=True)
print(f"Would enrich {stats['enriched']} items")

# Apply enrichment
stats = enricher.enrich_from_doi(incomplete, dry_run=False)
print(f"Enriched {stats['enriched']} items")

enricher.close()
```

### 2. Smart Organization (`organize.py`)

Intelligent organization and duplicate detection:

- **Duplicate detection**: Fuzzy matching on title, authors, DOI
- **Merge suggestions**: Recommends which item to keep and what data to merge
- **Auto-tagging**: Tag items based on keywords in title/abstract
- **Collection suggestions**: Group items by topic

**Example:**

```python
from pyzotero_academic.organize import SmartOrganizer

organizer = SmartOrganizer(zot)

# Find duplicates
duplicates = organizer.find_duplicates(similarity_threshold=0.85)
print(f"Found {len(duplicates)} duplicate groups")

# Get merge suggestions
strategy = organizer.suggest_merge_strategy(duplicates[0])
print(f"Keep: {strategy['keep_item']['data']['title']}")

# Execute merge
organizer.execute_merge(strategy, delete_duplicates=True)

# Auto-tag items
keyword_map = {
    'machine-learning': ['ML', 'neural network', 'deep learning'],
    'climate-science': ['climate', 'carbon', 'greenhouse']
}
stats = organizer.auto_tag_by_keywords(keyword_map=keyword_map)
print(f"Tagged {stats['tagged']} items")
```

### 3. Quality Control (`quality.py`)

Library quality control and validation:

- **Comprehensive audit**: Find missing fields, invalid DOIs, broken URLs, malformed dates
- **DOI validation**: Check format and resolution
- **URL validation**: Test for broken links
- **Author name normalization**: Standardize capitalization and formatting
- **Date standardization**: Convert to consistent format (YYYY-MM-DD)

**Example:**

```python
from pyzotero_academic.quality import QualityController

qc = QualityController(zot)

# Audit library
report = qc.audit_library()
print(f"Total issues: {report['summary']['total_issues']}")
print(f"Missing fields: {report['summary']['missing_fields']}")
print(f"Invalid DOIs: {report['summary']['invalid_dois']}")

# Validate DOIs
doi_report = qc.validate_dois(check_resolution=True)
print(f"Valid: {len(doi_report['valid_format'])}")
print(f"Invalid: {len(doi_report['invalid_format'])}")

# Normalize author names
stats = qc.normalize_author_names(dry_run=False)
print(f"Normalized {stats['normalized']} items")

# Standardize dates
stats = qc.fix_date_formats(target_format='YYYY-MM-DD')
print(f"Fixed {stats['fixed']} dates")

qc.close()
```

## Installation

```bash
# Install pyzotero if not already installed
pip install pyzotero

# Install academic extensions dependencies
pip install httpx
```

## External APIs Used

All APIs are **free** and don't require API keys (though providing an email for polite access is recommended):

### CrossRef
- **Purpose**: DOI metadata, bibliographic data
- **URL**: https://api.crossref.org
- **Polite pool**: Provide email for faster responses

### OpenAlex
- **Purpose**: Comprehensive academic metadata, citations, author info
- **URL**: https://openalex.org
- **Polite pool**: Provide email via `mailto` parameter

### Semantic Scholar
- **Purpose**: Citation counts, paper recommendations, abstracts
- **URL**: https://www.semanticscholar.org
- **Rate limit**: 1 request/second (free tier)

## Usage Patterns

### Dry-Run Pattern

All write operations support dry-run mode to preview changes:

```python
# Preview changes
stats = enricher.enrich_from_doi(items, dry_run=True)
for update in stats['updates']:
    print(f"Would update: {update['title']}")
    print(f"  Changes: {update['updates']}")

# Apply changes
stats = enricher.enrich_from_doi(items, dry_run=False)
print(f"Updated {stats['enriched']} items")
```

### Error Handling

All operations return statistics dicts with error counts:

```python
stats = enricher.enrich_from_doi(items)
print(f"Total: {stats['total']}")
print(f"Enriched: {stats['enriched']}")
print(f"Skipped: {stats['skipped']}")
print(f"Errors: {stats['errors']}")
```

### Batch Processing

Process items in batches to avoid rate limits:

```python
import time

all_items = zot.everything(zot.items())

# Process in batches of 50
batch_size = 50
for i in range(0, len(all_items), batch_size):
    batch = all_items[i:i+batch_size]
    stats = enricher.enrich_from_doi(batch)
    print(f"Batch {i//batch_size + 1}: Enriched {stats['enriched']}")
    time.sleep(2)  # Rate limiting
```

## Examples

See the `example/` directory for complete working examples:

- `academic_enrichment_example.py` - Metadata enrichment
- `academic_organize_example.py` - Duplicate detection and organization
- `academic_quality_example.py` - Quality control and validation

## API-Only Guarantee

All modules strictly adhere to API-only writes:

- ✅ Read from Zotero via API (`zot.items()`, `zot.collections()`, etc.)
- ✅ Write to Zotero via API (`zot.update_item()`, `zot.create_items()`, etc.)
- ❌ **Never** write to local Zotero database
- ❌ **Never** modify files directly

This ensures:
- Full sync with Zotero servers
- Version control and conflict resolution
- Multi-device compatibility
- Zotero's data integrity guarantees

## Performance Tips

1. **Use dry-run first**: Always preview changes before applying
2. **Provide email**: Get faster API responses from polite pools
3. **Batch processing**: Process large libraries in chunks
4. **Rate limiting**: Add delays between batches to respect API limits
5. **Cache results**: Store external API responses to avoid redundant calls

## Troubleshooting

### "No metadata found"
- Check if item has a valid DOI
- Try different external sources (OpenAlex vs CrossRef)
- Some older papers may not be in external databases

### Rate limit errors
- Add delays between requests
- Provide email for polite API access
- Consider processing in smaller batches

### API write failures
- Check Zotero API key permissions
- Verify library ID and type
- Ensure internet connection
- Check Zotero API status

## Future Modules (Planned)

- **Citation Network Analysis**: Build citation graphs, co-authorship networks
- **Paper Discovery**: Related paper recommendations, citation tracking
- **Bibliography Builder**: Advanced export to Obsidian, Notion, LaTeX
- **ML Features**: Topic modeling, abstract summarization, key phrase extraction

## Contributing

Contributions welcome! Please ensure:

- All writes use Zotero API only
- Include dry-run mode for write operations
- Return statistics dicts from operations
- Add examples to demonstrate features
- Follow existing code patterns

## License

Same as Pyzotero: Blue Oak Model License 1.0.0
