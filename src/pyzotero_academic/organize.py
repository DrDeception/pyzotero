"""Smart organization and duplicate detection for Zotero libraries.

This module provides functionality to:
- Detect duplicate items using fuzzy matching
- Generate merge suggestions
- Auto-tag items based on content
- Suggest collection organization

All writes are performed via the Zotero API only.
"""

import re
from difflib import SequenceMatcher
from typing import Any, Optional

from pyzotero.zotero import Zotero


class SmartOrganizer:
    """Intelligent organization and duplicate detection for Zotero.

    This class provides methods to:
    - Find duplicate items
    - Generate merge strategies
    - Auto-tag based on content
    - Suggest collection organization
    """

    def __init__(self, zotero_client: Zotero):
        """Initialize smart organizer.

        Args:
            zotero_client: Authenticated Zotero client instance
        """
        self.zot = zotero_client

    def find_duplicates(
        self,
        similarity_threshold: float = 0.85,
        item_types: Optional[list[str]] = None
    ) -> list[dict[str, Any]]:
        """Find potential duplicate items.

        Uses fuzzy matching on title, authors, and DOI.

        Args:
            similarity_threshold: Minimum similarity score (0-1) to consider duplicates
            item_types: Filter by item types. Default: all regular items

        Returns:
            List of duplicate groups: [
                {
                    'items': [item1, item2, ...],
                    'similarity': float,
                    'match_reason': str
                },
                ...
            ]
        """
        if item_types is None:
            item_types = ['journalArticle', 'conferencePaper', 'book', 'bookSection', 'preprint']

        # Fetch all items
        all_items = self.zot.everything(self.zot.items())

        # Filter by type
        items = [
            item for item in all_items
            if item.get('data', {}).get('itemType') in item_types
        ]

        duplicates = []
        processed = set()

        for i, item1 in enumerate(items):
            if item1.get('key') in processed:
                continue

            data1 = item1.get('data', {})
            group = [item1]

            for item2 in items[i+1:]:
                if item2.get('key') in processed:
                    continue

                data2 = item2.get('data', {})

                # Check for duplicates
                similarity, reason = self._calculate_similarity(data1, data2)

                if similarity >= similarity_threshold:
                    group.append(item2)
                    processed.add(item2.get('key'))

            if len(group) > 1:
                duplicates.append({
                    'items': group,
                    'similarity': similarity,
                    'match_reason': reason
                })
                processed.add(item1.get('key'))

        return duplicates

    def _calculate_similarity(
        self,
        item1: dict[str, Any],
        item2: dict[str, Any]
    ) -> tuple[float, str]:
        """Calculate similarity between two items.

        Args:
            item1: First item data dict
            item2: Second item data dict

        Returns:
            Tuple of (similarity_score, match_reason)
        """
        # Check DOI first (exact match)
        doi1 = item1.get('DOI', '').strip().lower()
        doi2 = item2.get('DOI', '').strip().lower()

        if doi1 and doi2 and doi1 == doi2:
            return 1.0, 'Identical DOI'

        # Check title similarity
        title1 = self._normalize_title(item1.get('title', ''))
        title2 = self._normalize_title(item2.get('title', ''))

        if not title1 or not title2:
            return 0.0, 'Missing title'

        title_similarity = SequenceMatcher(None, title1, title2).ratio()

        # Check author similarity
        authors1 = self._extract_author_names(item1.get('creators', []))
        authors2 = self._extract_author_names(item2.get('creators', []))

        author_similarity = self._compare_author_lists(authors1, authors2)

        # Check year
        year1 = self._extract_year(item1.get('date', ''))
        year2 = self._extract_year(item2.get('date', ''))
        year_match = year1 == year2 if year1 and year2 else False

        # Calculate overall similarity
        if title_similarity > 0.95 and author_similarity > 0.7:
            return max(title_similarity, author_similarity), 'Title and authors match'
        elif title_similarity > 0.9 and year_match:
            return title_similarity, 'Title and year match'
        elif title_similarity > 0.85:
            return title_similarity, 'Similar titles'
        else:
            return title_similarity * 0.7 + author_similarity * 0.3, 'Partial match'

    def _normalize_title(self, title: str) -> str:
        """Normalize title for comparison.

        Args:
            title: Raw title string

        Returns:
            Normalized title
        """
        # Convert to lowercase
        title = title.lower()

        # Remove punctuation
        title = re.sub(r'[^\w\s]', '', title)

        # Remove extra whitespace
        title = ' '.join(title.split())

        return title

    def _extract_author_names(self, creators: list[dict[str, Any]]) -> list[str]:
        """Extract author last names from creators list.

        Args:
            creators: Zotero creators list

        Returns:
            List of last names
        """
        names = []
        for creator in creators:
            if creator.get('creatorType') in ['author', 'editor']:
                last_name = creator.get('lastName', '').strip().lower()
                if last_name:
                    names.append(last_name)
        return names

    def _compare_author_lists(self, authors1: list[str], authors2: list[str]) -> float:
        """Compare two author lists.

        Args:
            authors1: First author list
            authors2: Second author list

        Returns:
            Similarity score (0-1)
        """
        if not authors1 or not authors2:
            return 0.0

        # Calculate Jaccard similarity
        set1 = set(authors1)
        set2 = set(authors2)

        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))

        if union == 0:
            return 0.0

        return intersection / union

    def _extract_year(self, date_str: str) -> Optional[str]:
        """Extract year from date string.

        Args:
            date_str: Date string

        Returns:
            Year as string or None
        """
        if not date_str:
            return None

        match = re.search(r'\b(19|20)\d{2}\b', date_str)
        if match:
            return match.group(0)

        return None

    def suggest_merge_strategy(
        self,
        duplicate_group: dict[str, Any]
    ) -> dict[str, Any]:
        """Suggest merge strategy for duplicate items.

        Recommends which item to keep and what data to merge.

        Args:
            duplicate_group: Duplicate group dict from find_duplicates()

        Returns:
            Merge strategy: {
                'keep_item': item_dict,
                'merge_items': [item_dict, ...],
                'merge_plan': {
                    'field_name': {
                        'action': 'keep'|'replace'|'append',
                        'source': item_key,
                        'value': new_value
                    },
                    ...
                }
            }
        """
        items = duplicate_group['items']

        if len(items) < 2:
            return {}

        # Score each item by completeness
        scored_items = []
        for item in items:
            score = self._score_item_completeness(item.get('data', {}))
            scored_items.append((score, item))

        # Sort by score (highest first)
        scored_items.sort(reverse=True, key=lambda x: x[0])

        keep_item = scored_items[0][1]
        merge_items = [item for _, item in scored_items[1:]]

        # Generate merge plan
        merge_plan = self._generate_merge_plan(keep_item, merge_items)

        return {
            'keep_item': keep_item,
            'merge_items': merge_items,
            'merge_plan': merge_plan
        }

    def _score_item_completeness(self, item_data: dict[str, Any]) -> int:
        """Score item by metadata completeness.

        Args:
            item_data: Item data dict

        Returns:
            Completeness score (higher is better)
        """
        score = 0

        # Important fields
        important_fields = [
            'DOI', 'abstractNote', 'date', 'publicationTitle',
            'volume', 'issue', 'pages', 'ISSN', 'url'
        ]

        for field in important_fields:
            if item_data.get(field, '').strip():
                score += 2

        # Creators
        if item_data.get('creators'):
            score += len(item_data['creators'])

        # Tags
        if item_data.get('tags'):
            score += len(item_data['tags'])

        # Attachments (note: this requires checking children)
        # We approximate by checking if item has relations
        if item_data.get('relations'):
            score += 1

        # Extra field
        if item_data.get('extra', '').strip():
            score += 1

        return score

    def _generate_merge_plan(
        self,
        keep_item: dict[str, Any],
        merge_items: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Generate detailed merge plan.

        Args:
            keep_item: Item to keep
            merge_items: Items to merge into keep_item

        Returns:
            Merge plan dict
        """
        plan = {}
        keep_data = keep_item.get('data', {})

        # Fields to check for merging
        text_fields = [
            'abstractNote', 'DOI', 'url', 'publicationTitle',
            'volume', 'issue', 'pages', 'ISSN', 'date'
        ]

        for field in text_fields:
            keep_value = keep_data.get(field, '').strip()

            # Find best value from merge items
            for merge_item in merge_items:
                merge_data = merge_item.get('data', {})
                merge_value = merge_data.get(field, '').strip()

                if not keep_value and merge_value:
                    plan[field] = {
                        'action': 'replace',
                        'source': merge_item.get('key'),
                        'value': merge_value
                    }
                    break
                elif keep_value and merge_value and len(merge_value) > len(keep_value):
                    # Suggest replacement if merge value is more complete
                    plan[field] = {
                        'action': 'suggest_replace',
                        'source': merge_item.get('key'),
                        'current': keep_value,
                        'suggested': merge_value
                    }

        # Merge tags
        all_tags = set()
        for tag in keep_data.get('tags', []):
            all_tags.add(tag.get('tag', ''))

        for merge_item in merge_items:
            merge_data = merge_item.get('data', {})
            for tag in merge_data.get('tags', []):
                all_tags.add(tag.get('tag', ''))

        if len(all_tags) > len(keep_data.get('tags', [])):
            plan['tags'] = {
                'action': 'merge',
                'value': [{'tag': tag} for tag in sorted(all_tags)]
            }

        # Merge extra field
        extra_parts = [keep_data.get('extra', '').strip()]
        for merge_item in merge_items:
            merge_data = merge_item.get('data', {})
            merge_extra = merge_data.get('extra', '').strip()
            if merge_extra and merge_extra not in extra_parts:
                extra_parts.append(merge_extra)

        if len(extra_parts) > 1:
            plan['extra'] = {
                'action': 'merge',
                'value': '\n---\n'.join(filter(None, extra_parts))
            }

        return plan

    def execute_merge(
        self,
        merge_strategy: dict[str, Any],
        delete_duplicates: bool = False
    ) -> bool:
        """Execute a merge strategy via Zotero API.

        Args:
            merge_strategy: Strategy from suggest_merge_strategy()
            delete_duplicates: If True, delete merged items after merge

        Returns:
            True if successful, False otherwise
        """
        try:
            keep_item = merge_strategy['keep_item']
            merge_plan = merge_strategy['merge_plan']

            # Apply merge plan to keep_item
            keep_data = keep_item.get('data', {}).copy()

            for field, plan in merge_plan.items():
                if plan['action'] in ['replace', 'merge']:
                    keep_data[field] = plan['value']

            # Update via API
            self.zot.update_item(keep_data)

            # Optionally delete duplicates
            if delete_duplicates:
                merge_items = merge_strategy['merge_items']
                for item in merge_items:
                    self.zot.delete_item(item)

            return True

        except Exception as e:
            print(f"Failed to execute merge: {e}")
            return False

    def auto_tag_by_keywords(
        self,
        items: Optional[list[dict[str, Any]]] = None,
        keyword_map: Optional[dict[str, list[str]]] = None,
        dry_run: bool = False
    ) -> dict[str, Any]:
        """Automatically tag items based on keywords in title/abstract.

        Args:
            items: Items to tag. If None, processes all items.
            keyword_map: Dict mapping tag -> [keywords]. If None, uses default.
            dry_run: If True, return suggestions without writing

        Returns:
            Statistics dict with 'total', 'tagged', 'suggestions' (if dry_run)
        """
        if items is None:
            items = self.zot.everything(self.zot.items())

        if keyword_map is None:
            # Default keyword map for common research areas
            keyword_map = {
                'machine-learning': ['machine learning', 'neural network', 'deep learning', 'AI', 'artificial intelligence'],
                'climate-change': ['climate change', 'global warming', 'carbon emissions', 'greenhouse gas'],
                'public-health': ['public health', 'epidemiology', 'disease prevention', 'healthcare'],
                'education': ['pedagogy', 'teaching', 'learning', 'curriculum', 'student'],
                'economics': ['economic', 'market', 'GDP', 'inflation', 'monetary'],
                'neuroscience': ['brain', 'neural', 'cognitive', 'neuron', 'fMRI'],
                'genetics': ['gene', 'DNA', 'genome', 'genetic', 'mutation'],
            }

        stats = {
            'total': len(items),
            'tagged': 0,
            'suggestions': [] if dry_run else None
        }

        for item in items:
            data = item.get('data', {})

            # Get text to search
            title = data.get('title', '').lower()
            abstract = data.get('abstractNote', '').lower()
            text = f"{title} {abstract}"

            # Find matching tags
            suggested_tags = set()
            current_tags = {tag.get('tag', '') for tag in data.get('tags', [])}

            for tag, keywords in keyword_map.items():
                if tag in current_tags:
                    continue  # Already has this tag

                for keyword in keywords:
                    if keyword.lower() in text:
                        suggested_tags.add(tag)
                        break

            if suggested_tags:
                if dry_run:
                    stats['suggestions'].append({
                        'item_key': item.get('key'),
                        'title': data.get('title', 'Untitled'),
                        'suggested_tags': list(suggested_tags)
                    })
                else:
                    # Add tags via API
                    new_tags = list(current_tags.union(suggested_tags))
                    tag_list = [{'tag': tag} for tag in new_tags]

                    try:
                        updated_data = data.copy()
                        updated_data['tags'] = tag_list
                        self.zot.update_item(updated_data)
                        stats['tagged'] += 1
                    except Exception as e:
                        print(f"Failed to tag item {item.get('key')}: {e}")

        return stats

    def suggest_collections_by_topic(
        self,
        items: list[dict[str, Any]],
        num_topics: int = 5
    ) -> dict[str, list[dict[str, Any]]]:
        """Suggest collection groupings based on content similarity.

        Uses simple keyword extraction for topic clustering.

        Args:
            items: Items to organize
            num_topics: Number of topic groups to create

        Returns:
            Dict mapping topic_name -> [items]
        """
        # Simple implementation using common words in titles
        # For production, consider using proper topic modeling (LDA, etc.)

        from collections import Counter

        # Extract keywords from all titles
        all_keywords = []
        item_keywords = {}

        for item in items:
            data = item.get('data', {})
            title = data.get('title', '')
            keywords = self._extract_keywords(title)
            all_keywords.extend(keywords)
            item_keywords[item.get('key')] = set(keywords)

        # Find most common keywords
        keyword_counts = Counter(all_keywords)
        top_keywords = [word for word, _ in keyword_counts.most_common(num_topics)]

        # Group items by dominant keyword
        topics = {keyword: [] for keyword in top_keywords}
        topics['Other'] = []

        for item in items:
            item_key = item.get('key')
            keywords = item_keywords.get(item_key, set())

            # Find best matching topic
            best_topic = None
            max_match = 0

            for topic_keyword in top_keywords:
                if topic_keyword in keywords:
                    match_score = keyword_counts[topic_keyword]
                    if match_score > max_match:
                        max_match = match_score
                        best_topic = topic_keyword

            if best_topic:
                topics[best_topic].append(item)
            else:
                topics['Other'].append(item)

        # Remove empty topics
        return {k: v for k, v in topics.items() if v}

    def _extract_keywords(self, text: str, min_length: int = 4) -> list[str]:
        """Extract keywords from text.

        Args:
            text: Text to extract from
            min_length: Minimum keyword length

        Returns:
            List of keywords
        """
        # Simple keyword extraction - remove stop words
        stop_words = {
            'the', 'and', 'for', 'with', 'from', 'this', 'that', 'these',
            'those', 'what', 'which', 'who', 'when', 'where', 'how', 'why',
            'about', 'into', 'through', 'during', 'before', 'after', 'above',
            'below', 'between', 'under', 'again', 'further', 'then', 'once'
        }

        words = re.findall(r'\b\w+\b', text.lower())
        keywords = [
            word for word in words
            if len(word) >= min_length and word not in stop_words
        ]

        return keywords
