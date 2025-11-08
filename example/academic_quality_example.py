"""Example: Library quality control and validation.

This script demonstrates how to use the QualityController to:
1. Audit library for quality issues
2. Validate DOIs
3. Normalize author names
4. Fix date formats

All updates are performed via the Zotero API.
"""

from pyzotero import zotero
from pyzotero_academic.quality import QualityController

# Configuration
LIBRARY_ID = 'your_library_id'  # Replace with your library ID
LIBRARY_TYPE = 'user'  # or 'group'
API_KEY = 'your_api_key'  # Replace with your API key

def main():
    # Initialize Zotero client
    print("Connecting to Zotero...")
    zot = zotero.Zotero(LIBRARY_ID, LIBRARY_TYPE, API_KEY)

    # Initialize quality controller
    print("Initializing quality controller...")
    qc = QualityController(zot)

    # Example 1: Comprehensive library audit
    print("\n" + "="*60)
    print("Example 1: Library audit")
    print("="*60)

    # Audit first 50 items (for demo)
    sample_items = zot.items(limit=50)
    report = qc.audit_library(items=sample_items)

    print(f"\nAudit Results ({report['total_items']} items checked):")
    print(f"  Total issues: {report['summary']['total_issues']}")
    print("\nBreakdown:")

    for issue_type, count in report['summary'].items():
        if issue_type != 'total_issues' and count > 0:
            print(f"  {issue_type}: {count}")

    # Show some examples
    if report['issues']['missing_fields']:
        print("\nSample items with missing fields:")
        for item in report['issues']['missing_fields'][:3]:
            print(f"  - {item['title'][:60]}...")
            print(f"    Missing: {', '.join(item['missing'])}")

    if report['issues']['invalid_dois']:
        print("\nItems with invalid DOI format:")
        for item in report['issues']['invalid_dois'][:3]:
            print(f"  - {item['title'][:60]}...")
            print(f"    DOI: {item['doi']}")

    if report['issues']['malformed_dates']:
        print("\nItems with malformed dates:")
        for item in report['issues']['malformed_dates'][:3]:
            print(f"  - {item['title'][:60]}...")
            print(f"    Date: {item['date']}")

    # Example 2: Validate DOIs
    print("\n" + "="*60)
    print("Example 2: DOI validation")
    print("="*60)

    doi_report = qc.validate_dois(
        items=sample_items,
        check_resolution=False  # Set to True to check if DOIs resolve (slower)
    )

    print(f"\nDOI Validation Results:")
    print(f"  Total checked: {doi_report['total_checked']}")
    print(f"  Valid format: {len(doi_report['valid_format'])}")
    print(f"  Invalid format: {len(doi_report['invalid_format'])}")

    if doi_report['invalid_format']:
        print("\nInvalid DOIs:")
        for item in doi_report['invalid_format'][:3]:
            print(f"  - {item['title'][:60]}...")
            print(f"    DOI: {item['doi']}")

    # Example 3: Normalize author names (dry run)
    print("\n" + "="*60)
    print("Example 3: Author name normalization (dry run)")
    print("="*60)

    stats = qc.normalize_author_names(
        items=sample_items,
        dry_run=True
    )

    print(f"\nNormalization results:")
    print(f"  Total items: {stats['total']}")
    print(f"  Would normalize: {stats['normalized']}")
    print(f"  Skipped: {stats['skipped']}")

    if stats.get('suggestions'):
        print("\nSample normalizations:")
        for suggestion in stats['suggestions'][:3]:
            print(f"\n  {suggestion['title'][:60]}...")
            print(f"  Before:")
            for creator in suggestion['old_creators'][:2]:
                first = creator.get('firstName', '')
                last = creator.get('lastName', '')
                print(f"    {first} {last}")
            print(f"  After:")
            for creator in suggestion['new_creators'][:2]:
                first = creator.get('firstName', '')
                last = creator.get('lastName', '')
                print(f"    {first} {last}")

        print("\nTo apply normalization (COMMENTED OUT):")
        print("""
        # stats = qc.normalize_author_names(
        #     items=sample_items,
        #     dry_run=False
        # )
        # print(f"Normalized {stats['normalized']} items")
        """)

    # Example 4: Fix date formats (dry run)
    print("\n" + "="*60)
    print("Example 4: Date format standardization (dry run)")
    print("="*60)

    stats = qc.fix_date_formats(
        items=sample_items,
        target_format='YYYY-MM-DD',
        dry_run=True
    )

    print(f"\nDate standardization results:")
    print(f"  Total items: {stats['total']}")
    print(f"  Would fix: {stats['fixed']}")
    print(f"  Skipped: {stats['skipped']}")

    if stats.get('suggestions'):
        print("\nSample date fixes:")
        for suggestion in stats['suggestions'][:5]:
            print(f"  {suggestion['title'][:60]}...")
            print(f"    {suggestion['old_date']} → {suggestion['new_date']}")

        print("\nTo apply date fixes (COMMENTED OUT):")
        print("""
        # stats = qc.fix_date_formats(
        #     items=sample_items,
        #     target_format='YYYY-MM-DD',
        #     dry_run=False
        # )
        # print(f"Fixed {stats['fixed']} items")
        """)

    # Example 5: Validate URLs (optional - can be slow)
    print("\n" + "="*60)
    print("Example 5: URL validation (COMMENTED OUT - can be slow)")
    print("="*60)
    print("Uncomment to check for broken URLs:")
    print("""
    # url_report = qc.validate_urls(items=sample_items)
    # print(f"Total URLs checked: {url_report['total_checked']}")
    # print(f"Working: {len(url_report['working'])}")
    # print(f"Broken: {len(url_report['broken'])}")
    # print(f"Invalid format: {len(url_report['invalid_format'])}")
    """)

    # Cleanup
    print("\n" + "="*60)
    print("Cleaning up...")
    qc.close()
    print("Done!")

if __name__ == '__main__':
    main()
