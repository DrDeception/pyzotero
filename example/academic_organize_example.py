"""Example: Smart organization and duplicate detection.

This script demonstrates how to use the SmartOrganizer to:
1. Find duplicate items
2. Get merge suggestions
3. Auto-tag items by keywords
4. Suggest collection organization

All updates are performed via the Zotero API.
"""

from pyzotero import zotero
from pyzotero_academic.organize import SmartOrganizer

# Configuration
LIBRARY_ID = 'your_library_id'  # Replace with your library ID
LIBRARY_TYPE = 'user'  # or 'group'
API_KEY = 'your_api_key'  # Replace with your API key

def main():
    # Initialize Zotero client
    print("Connecting to Zotero...")
    zot = zotero.Zotero(LIBRARY_ID, LIBRARY_TYPE, API_KEY)

    # Initialize organizer
    print("Initializing smart organizer...")
    organizer = SmartOrganizer(zot)

    # Example 1: Find duplicates
    print("\n" + "="*60)
    print("Example 1: Finding duplicate items")
    print("="*60)

    duplicates = organizer.find_duplicates(
        similarity_threshold=0.85
    )

    print(f"Found {len(duplicates)} duplicate groups")

    for i, dup_group in enumerate(duplicates[:3], 1):  # Show first 3 groups
        print(f"\nDuplicate Group {i}:")
        print(f"  Similarity: {dup_group['similarity']:.2f}")
        print(f"  Reason: {dup_group['match_reason']}")
        print(f"  Items ({len(dup_group['items'])}):")

        for item in dup_group['items']:
            data = item.get('data', {})
            print(f"    - {data.get('title', 'Untitled')[:60]}...")
            print(f"      Key: {item.get('key')}")
            print(f"      DOI: {data.get('DOI', 'N/A')}")

    # Example 2: Get merge suggestions
    if duplicates:
        print("\n" + "="*60)
        print("Example 2: Merge suggestions")
        print("="*60)

        # Get merge strategy for first duplicate group
        first_group = duplicates[0]
        strategy = organizer.suggest_merge_strategy(first_group)

        keep_item = strategy['keep_item']
        merge_items = strategy['merge_items']
        merge_plan = strategy['merge_plan']

        print(f"\nRecommended to KEEP:")
        keep_data = keep_item.get('data', {})
        print(f"  Title: {keep_data.get('title', 'Untitled')[:60]}...")
        print(f"  Key: {keep_item.get('key')}")

        print(f"\nRecommended to MERGE ({len(merge_items)} items):")
        for item in merge_items:
            data = item.get('data', {})
            print(f"  - {data.get('title', 'Untitled')[:60]}...")
            print(f"    Key: {item.get('key')}")

        print(f"\nMerge plan ({len(merge_plan)} field updates):")
        for field, plan in merge_plan.items():
            print(f"  {field}: {plan['action']}")
            if plan['action'] == 'replace' and field != 'tags':
                print(f"    Value: {str(plan['value'])[:60]}...")

        print("\nTo execute merge (COMMENTED OUT):")
        print("""
        # organizer.execute_merge(strategy, delete_duplicates=True)
        """)

    # Example 3: Auto-tag by keywords
    print("\n" + "="*60)
    print("Example 3: Auto-tagging by keywords (dry run)")
    print("="*60)

    # Get some items to tag
    sample_items = zot.items(limit=20)

    # Custom keyword map
    keyword_map = {
        'climate-science': ['climate', 'global warming', 'carbon', 'greenhouse'],
        'machine-learning': ['machine learning', 'neural network', 'deep learning', 'AI'],
        'public-health': ['public health', 'epidemiology', 'disease', 'healthcare'],
        'economics': ['economic', 'market', 'GDP', 'inflation'],
    }

    stats = organizer.auto_tag_by_keywords(
        items=sample_items,
        keyword_map=keyword_map,
        dry_run=True
    )

    print(f"\nAuto-tagging results:")
    print(f"  Total items: {stats['total']}")
    print(f"  Items that would be tagged: {len(stats['suggestions'])}")

    if stats['suggestions']:
        print("\nSample suggestions:")
        for suggestion in stats['suggestions'][:5]:
            print(f"\n  {suggestion['title'][:60]}...")
            print(f"  Suggested tags: {', '.join(suggestion['suggested_tags'])}")

        print("\nTo apply tags (COMMENTED OUT):")
        print("""
        # stats = organizer.auto_tag_by_keywords(
        #     items=sample_items,
        #     keyword_map=keyword_map,
        #     dry_run=False
        # )
        # print(f"Tagged {stats['tagged']} items")
        """)

    # Example 4: Suggest collection organization
    print("\n" + "="*60)
    print("Example 4: Collection organization suggestions")
    print("="*60)

    # Get items to organize
    items_to_organize = zot.items(limit=30)

    topics = organizer.suggest_collections_by_topic(
        items=items_to_organize,
        num_topics=5
    )

    print(f"\nSuggested collection structure ({len(topics)} topics):")

    for topic, items in sorted(topics.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"\n  Collection: '{topic}' ({len(items)} items)")

        for item in items[:3]:  # Show first 3 items per collection
            data = item.get('data', {})
            print(f"    - {data.get('title', 'Untitled')[:60]}...")

        if len(items) > 3:
            print(f"    ... and {len(items) - 3} more")

    print("\n" + "="*60)
    print("Done!")

if __name__ == '__main__':
    main()
