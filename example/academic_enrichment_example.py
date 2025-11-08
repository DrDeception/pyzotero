"""Example: Enrich Zotero library with metadata from external sources.

This script demonstrates how to use the MetadataEnricher to:
1. Find items with missing metadata
2. Enrich items using their DOI
3. Add citation counts to items

All updates are performed via the Zotero API.
"""

from pyzotero import zotero
from pyzotero_academic.enrichment import MetadataEnricher

# Configuration
LIBRARY_ID = 'your_library_id'  # Replace with your library ID
LIBRARY_TYPE = 'user'  # or 'group'
API_KEY = 'your_api_key'  # Replace with your API key
EMAIL = 'your.email@example.com'  # For polite API access

def main():
    # Initialize Zotero client
    print("Connecting to Zotero...")
    zot = zotero.Zotero(LIBRARY_ID, LIBRARY_TYPE, API_KEY)

    # Initialize metadata enricher
    print("Initializing metadata enricher...")
    enricher = MetadataEnricher(zot, email=EMAIL)

    # Example 1: Find items with missing metadata
    print("\n" + "="*60)
    print("Example 1: Finding items with missing metadata")
    print("="*60)

    incomplete_items = enricher.find_incomplete_items(
        require_fields=['DOI', 'abstractNote', 'date'],
        item_types=['journalArticle', 'conferencePaper']
    )

    print(f"Found {len(incomplete_items)} items with missing metadata")

    for item in incomplete_items[:5]:  # Show first 5
        data = item.get('data', {})
        missing = item.get('_missing_fields', [])
        print(f"\n  Title: {data.get('title', 'Untitled')[:60]}...")
        print(f"  Missing: {', '.join(missing)}")
        print(f"  DOI: {data.get('DOI', 'N/A')}")

    # Example 2: Dry run enrichment to preview changes
    if incomplete_items:
        print("\n" + "="*60)
        print("Example 2: Preview enrichment (dry run)")
        print("="*60)

        # Limit to first 3 items for demo
        sample_items = incomplete_items[:3]

        stats = enricher.enrich_from_doi(
            sample_items,
            dry_run=True
        )

        print(f"\nDry run results:")
        print(f"  Total: {stats['total']}")
        print(f"  Would enrich: {stats['enriched']}")
        print(f"  Would skip: {stats['skipped']}")
        print(f"  Errors: {stats['errors']}")

        if stats.get('updates'):
            print("\nProposed updates:")
            for update in stats['updates'][:2]:  # Show first 2
                print(f"\n  Title: {update['title'][:60]}...")
                print(f"  DOI: {update['doi']}")
                print(f"  Updates:")
                for field, value in update['updates'].items():
                    if field == 'abstractNote':
                        print(f"    {field}: {value[:80]}...")
                    else:
                        print(f"    {field}: {value}")

    # Example 3: Actually enrich items (commented out for safety)
    print("\n" + "="*60)
    print("Example 3: Enrich items via API (COMMENTED OUT)")
    print("="*60)
    print("Uncomment the code below to actually update your library:")
    print("""
    # stats = enricher.enrich_from_doi(
    #     incomplete_items,
    #     fields_to_update=['abstractNote', 'date', 'publicationTitle'],
    #     dry_run=False
    # )
    # print(f"Enriched {stats['enriched']} items")
    """)

    # Example 4: Add citation counts
    print("\n" + "="*60)
    print("Example 4: Add citation counts (dry run)")
    print("="*60)

    # Get items with DOIs
    all_items = zot.items(limit=10)  # Just get first 10 for demo

    stats = enricher.enrich_citation_counts(
        items=all_items,
        dry_run=True
    )

    print(f"\nCitation count results:")
    print(f"  Total: {stats['total']}")
    print(f"  Would update: {stats['updated']}")
    print(f"  Skipped: {stats['skipped']}")

    if stats.get('updates'):
        print("\nSample citation counts:")
        for update in stats['updates'][:5]:
            print(f"  {update['title'][:60]}... - {update['citation_count']} citations")

    # Cleanup
    print("\n" + "="*60)
    print("Cleaning up...")
    enricher.close()
    print("Done!")

if __name__ == '__main__':
    main()
