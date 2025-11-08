"""Metadata enrichment from external academic sources.

This module provides functionality to automatically enrich Zotero items with
missing metadata from external sources like CrossRef, OpenAlex, and Semantic Scholar.

All writes are performed via the Zotero API only.
"""

import re
from typing import Any, Optional

from pyzotero.zotero import Zotero

from pyzotero_academic.utils.external_apis import (
    CrossRefAPI,
    OpenAlexAPI,
    SemanticScholarAPI,
)


class MetadataEnricher:
    """Enrich Zotero items with metadata from external sources.

    This class provides methods to:
    - Find items with missing metadata
    - Fetch metadata from CrossRef, OpenAlex, Semantic Scholar
    - Update Zotero items via API with enriched data
    """

    def __init__(
        self,
        zotero_client: Zotero,
        email: Optional[str] = None,
        use_crossref: bool = True,
        use_openalex: bool = True,
        use_semantic_scholar: bool = True
    ):
        """Initialize metadata enricher.

        Args:
            zotero_client: Authenticated Zotero client instance
            email: Email for polite API access (recommended)
            use_crossref: Enable CrossRef API
            use_openalex: Enable OpenAlex API
            use_semantic_scholar: Enable Semantic Scholar API
        """
        self.zot = zotero_client
        self.email = email

        # Initialize external API clients
        self.crossref = CrossRefAPI(email=email) if use_crossref else None
        self.openalex = OpenAlexAPI(email=email) if use_openalex else None
        self.semantic_scholar = SemanticScholarAPI() if use_semantic_scholar else None

    def find_incomplete_items(
        self,
        require_fields: Optional[list[str]] = None,
        item_types: Optional[list[str]] = None
    ) -> list[dict[str, Any]]:
        """Find items missing critical metadata fields.

        Args:
            require_fields: List of field names that should be present.
                           Default: ['DOI', 'abstractNote', 'date']
            item_types: Filter by item types. Default: journal articles, conference papers

        Returns:
            List of Zotero items missing one or more required fields
        """
        if require_fields is None:
            require_fields = ['DOI', 'abstractNote', 'date']

        if item_types is None:
            item_types = ['journalArticle', 'conferencePaper', 'preprint']

        # Fetch all items
        all_items = self.zot.everything(self.zot.items())

        incomplete = []

        for item in all_items:
            # Skip non-regular items (notes, attachments)
            if item.get('itemType') not in item_types:
                continue

            data = item.get('data', {})

            # Check if any required field is missing or empty
            missing_fields = []
            for field in require_fields:
                value = data.get(field, '').strip()
                if not value:
                    missing_fields.append(field)

            if missing_fields:
                item['_missing_fields'] = missing_fields
                incomplete.append(item)

        return incomplete

    def extract_doi(self, item: dict[str, Any]) -> Optional[str]:
        """Extract DOI from a Zotero item.

        Checks DOI field, extra field, and URL field.

        Args:
            item: Zotero item dict

        Returns:
            Clean DOI string or None if not found
        """
        data = item.get('data', {})

        # Check DOI field
        doi = data.get('DOI', '').strip()
        if doi:
            return self._clean_doi(doi)

        # Check extra field for DOI
        extra = data.get('extra', '')
        doi_match = re.search(r'DOI:\s*([^\s]+)', extra, re.IGNORECASE)
        if doi_match:
            return self._clean_doi(doi_match.group(1))

        # Check URL field
        url = data.get('url', '')
        if 'doi.org' in url:
            doi_match = re.search(r'doi\.org/(.+)$', url)
            if doi_match:
                return self._clean_doi(doi_match.group(1))

        return None

    def _clean_doi(self, doi: str) -> str:
        """Clean and normalize DOI string.

        Args:
            doi: Raw DOI string

        Returns:
            Cleaned DOI
        """
        doi = doi.strip()
        doi = doi.replace('https://doi.org/', '')
        doi = doi.replace('http://doi.org/', '')
        doi = doi.replace('doi:', '')
        return doi.strip()

    def enrich_from_doi(
        self,
        items: list[dict[str, Any]],
        fields_to_update: Optional[list[str]] = None,
        dry_run: bool = False
    ) -> dict[str, Any]:
        """Enrich items using their DOI.

        Fetches metadata from external sources and updates via Zotero API.

        Args:
            items: List of Zotero items to enrich
            fields_to_update: List of fields to update. If None, updates missing fields only.
                             Options: 'abstractNote', 'date', 'publicationTitle',
                                     'volume', 'issue', 'pages', 'ISSN'
            dry_run: If True, return proposed changes without writing to Zotero

        Returns:
            Dict with statistics: {
                'total': int,
                'enriched': int,
                'skipped': int,
                'errors': int,
                'updates': list[dict]  # Only in dry_run mode
            }
        """
        if fields_to_update is None:
            # Default: update common missing fields
            fields_to_update = [
                'abstractNote', 'date', 'publicationTitle',
                'volume', 'issue', 'pages', 'ISSN'
            ]

        stats = {
            'total': len(items),
            'enriched': 0,
            'skipped': 0,
            'errors': 0
        }

        if dry_run:
            stats['updates'] = []

        for item in items:
            try:
                doi = self.extract_doi(item)
                if not doi:
                    stats['skipped'] += 1
                    continue

                # Try to fetch metadata from available sources
                metadata = self._fetch_metadata_by_doi(doi)
                if not metadata:
                    stats['skipped'] += 1
                    continue

                # Prepare updates
                updates = self._prepare_updates(item, metadata, fields_to_update)

                if not updates:
                    stats['skipped'] += 1
                    continue

                if dry_run:
                    stats['updates'].append({
                        'item_key': item.get('key'),
                        'title': item.get('data', {}).get('title', 'Untitled'),
                        'doi': doi,
                        'updates': updates
                    })
                    stats['enriched'] += 1
                else:
                    # Apply updates via Zotero API
                    success = self._update_item(item, updates)
                    if success:
                        stats['enriched'] += 1
                    else:
                        stats['errors'] += 1

            except Exception as e:
                print(f"Error enriching item {item.get('key')}: {e}")
                stats['errors'] += 1

        return stats

    def _fetch_metadata_by_doi(self, doi: str) -> Optional[dict[str, Any]]:
        """Fetch metadata from external sources by DOI.

        Tries sources in order: OpenAlex, CrossRef, Semantic Scholar.

        Args:
            doi: DOI string

        Returns:
            Unified metadata dict or None
        """
        # Try OpenAlex first (most comprehensive)
        if self.openalex:
            try:
                data = self.openalex.get_work_by_doi(doi)
                if data:
                    return self._normalize_openalex_metadata(data)
            except Exception:
                pass

        # Try CrossRef
        if self.crossref:
            try:
                data = self.crossref.get_work_by_doi(doi)
                if data:
                    return self._normalize_crossref_metadata(data)
            except Exception:
                pass

        # Try Semantic Scholar
        if self.semantic_scholar:
            try:
                data = self.semantic_scholar.get_paper_by_doi(doi)
                if data:
                    return self._normalize_semantic_scholar_metadata(data)
            except Exception:
                pass

        return None

    def _normalize_openalex_metadata(self, data: dict[str, Any]) -> dict[str, Any]:
        """Convert OpenAlex metadata to unified format.

        Args:
            data: OpenAlex work dict

        Returns:
            Normalized metadata dict
        """
        normalized = {}

        # Abstract
        if data.get('abstract_inverted_index'):
            normalized['abstract'] = self._reconstruct_abstract(
                data['abstract_inverted_index']
            )

        # Publication date
        if data.get('publication_date'):
            normalized['date'] = data['publication_date']

        # Journal/venue
        if data.get('primary_location', {}).get('source', {}).get('display_name'):
            normalized['publicationTitle'] = data['primary_location']['source']['display_name']

        # ISSN
        if data.get('primary_location', {}).get('source', {}).get('issn'):
            issns = data['primary_location']['source']['issn']
            if issns:
                normalized['ISSN'] = issns[0]

        # Volume, issue, pages from biblio
        biblio = data.get('biblio', {})
        if biblio.get('volume'):
            normalized['volume'] = biblio['volume']
        if biblio.get('issue'):
            normalized['issue'] = biblio['issue']
        if biblio.get('first_page') and biblio.get('last_page'):
            normalized['pages'] = f"{biblio['first_page']}-{biblio['last_page']}"

        # Citation count (add to extra field)
        if data.get('cited_by_count'):
            normalized['citationCount'] = data['cited_by_count']

        # OpenAlex ID (add to extra field)
        if data.get('id'):
            normalized['openalexId'] = data['id']

        return normalized

    def _normalize_crossref_metadata(self, data: dict[str, Any]) -> dict[str, Any]:
        """Convert CrossRef metadata to unified format.

        Args:
            data: CrossRef work dict

        Returns:
            Normalized metadata dict
        """
        normalized = {}

        # Abstract
        if data.get('abstract'):
            normalized['abstract'] = data['abstract']

        # Publication date
        if data.get('published', {}).get('date-parts'):
            date_parts = data['published']['date-parts'][0]
            if len(date_parts) >= 1:
                year = date_parts[0]
                month = date_parts[1] if len(date_parts) >= 2 else 1
                day = date_parts[2] if len(date_parts) >= 3 else 1
                normalized['date'] = f"{year}-{month:02d}-{day:02d}"

        # Journal
        if data.get('container-title'):
            normalized['publicationTitle'] = data['container-title'][0]

        # ISSN
        if data.get('ISSN'):
            normalized['ISSN'] = data['ISSN'][0]

        # Volume, issue, pages
        if data.get('volume'):
            normalized['volume'] = data['volume']
        if data.get('issue'):
            normalized['issue'] = data['issue']
        if data.get('page'):
            normalized['pages'] = data['page']

        # Citation count
        if data.get('is-referenced-by-count'):
            normalized['citationCount'] = data['is-referenced-by-count']

        return normalized

    def _normalize_semantic_scholar_metadata(self, data: dict[str, Any]) -> dict[str, Any]:
        """Convert Semantic Scholar metadata to unified format.

        Args:
            data: Semantic Scholar paper dict

        Returns:
            Normalized metadata dict
        """
        normalized = {}

        # Abstract
        if data.get('abstract'):
            normalized['abstract'] = data['abstract']

        # Publication date
        if data.get('publicationDate'):
            normalized['date'] = data['publicationDate']

        # Venue
        if data.get('venue'):
            normalized['publicationTitle'] = data['venue']

        # Citation count
        if data.get('citationCount') is not None:
            normalized['citationCount'] = data['citationCount']

        # Influential citation count
        if data.get('influentialCitationCount'):
            normalized['influentialCitationCount'] = data['influentialCitationCount']

        # TL;DR summary
        if data.get('tldr', {}).get('text'):
            normalized['tldr'] = data['tldr']['text']

        # Semantic Scholar ID
        if data.get('paperId'):
            normalized['semanticScholarId'] = data['paperId']

        return normalized

    def _reconstruct_abstract(self, inverted_index: dict[str, list[int]]) -> str:
        """Reconstruct abstract text from OpenAlex inverted index.

        Args:
            inverted_index: Dict mapping words to position indices

        Returns:
            Reconstructed abstract text
        """
        # Find max position
        max_pos = 0
        for positions in inverted_index.values():
            max_pos = max(max_pos, max(positions))

        # Build array
        words = [''] * (max_pos + 1)
        for word, positions in inverted_index.items():
            for pos in positions:
                words[pos] = word

        return ' '.join(words)

    def _prepare_updates(
        self,
        item: dict[str, Any],
        metadata: dict[str, Any],
        fields_to_update: list[str]
    ) -> dict[str, Any]:
        """Prepare update dict for Zotero item.

        Only updates empty fields unless explicitly specified.

        Args:
            item: Original Zotero item
            metadata: Fetched metadata
            fields_to_update: Fields allowed to be updated

        Returns:
            Dict of field updates to apply
        """
        updates = {}
        data = item.get('data', {})
        extra_updates = []

        # Map metadata fields to Zotero fields
        field_mapping = {
            'abstract': 'abstractNote',
            'date': 'date',
            'publicationTitle': 'publicationTitle',
            'volume': 'volume',
            'issue': 'issue',
            'pages': 'pages',
            'ISSN': 'ISSN'
        }

        for meta_field, zotero_field in field_mapping.items():
            if zotero_field not in fields_to_update:
                continue

            current_value = data.get(zotero_field, '').strip()
            new_value = metadata.get(meta_field, '').strip()

            # Only update if current is empty and new value exists
            if not current_value and new_value:
                updates[zotero_field] = new_value

        # Handle extra field additions (citation count, IDs)
        current_extra = data.get('extra', '').strip()

        if metadata.get('citationCount') is not None:
            extra_updates.append(f"Citation Count: {metadata['citationCount']}")

        if metadata.get('openalexId'):
            extra_updates.append(f"OpenAlex ID: {metadata['openalexId']}")

        if metadata.get('semanticScholarId'):
            extra_updates.append(f"Semantic Scholar ID: {metadata['semanticScholarId']}")

        if metadata.get('tldr'):
            extra_updates.append(f"TL;DR: {metadata['tldr']}")

        if extra_updates:
            if current_extra:
                new_extra = current_extra + '\n' + '\n'.join(extra_updates)
            else:
                new_extra = '\n'.join(extra_updates)
            updates['extra'] = new_extra

        return updates

    def _update_item(self, item: dict[str, Any], updates: dict[str, Any]) -> bool:
        """Update Zotero item via API.

        Args:
            item: Original Zotero item
            updates: Dict of field updates

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get item data
            item_data = item.get('data', {}).copy()

            # Apply updates
            for field, value in updates.items():
                item_data[field] = value

            # Update via API
            self.zot.update_item(item_data)
            return True

        except Exception as e:
            print(f"Failed to update item {item.get('key')}: {e}")
            return False

    def enrich_citation_counts(
        self,
        items: Optional[list[dict[str, Any]]] = None,
        dry_run: bool = False
    ) -> dict[str, Any]:
        """Add citation counts to items from external sources.

        Args:
            items: List of items to process. If None, processes all items with DOIs.
            dry_run: If True, return proposed changes without writing

        Returns:
            Statistics dict
        """
        if items is None:
            items = self.zot.everything(self.zot.items())

        stats = {
            'total': len(items),
            'updated': 0,
            'skipped': 0,
            'errors': 0
        }

        if dry_run:
            stats['updates'] = []

        for item in items:
            try:
                doi = self.extract_doi(item)
                if not doi:
                    stats['skipped'] += 1
                    continue

                # Fetch citation count
                citation_count = None

                if self.openalex:
                    try:
                        data = self.openalex.get_work_by_doi(doi)
                        if data and data.get('cited_by_count') is not None:
                            citation_count = data['cited_by_count']
                    except Exception:
                        pass

                if citation_count is None and self.semantic_scholar:
                    try:
                        data = self.semantic_scholar.get_paper_by_doi(doi)
                        if data and data.get('citationCount') is not None:
                            citation_count = data['citationCount']
                    except Exception:
                        pass

                if citation_count is None:
                    stats['skipped'] += 1
                    continue

                # Prepare update
                data = item.get('data', {})
                current_extra = data.get('extra', '').strip()

                # Check if citation count already exists
                if re.search(r'Citation Count:', current_extra, re.IGNORECASE):
                    # Update existing
                    new_extra = re.sub(
                        r'Citation Count:\s*\d+',
                        f'Citation Count: {citation_count}',
                        current_extra,
                        flags=re.IGNORECASE
                    )
                else:
                    # Add new
                    if current_extra:
                        new_extra = current_extra + f'\nCitation Count: {citation_count}'
                    else:
                        new_extra = f'Citation Count: {citation_count}'

                if dry_run:
                    stats['updates'].append({
                        'item_key': item.get('key'),
                        'title': data.get('title', 'Untitled'),
                        'citation_count': citation_count
                    })
                    stats['updated'] += 1
                else:
                    # Update via API
                    success = self._update_item(item, {'extra': new_extra})
                    if success:
                        stats['updated'] += 1
                    else:
                        stats['errors'] += 1

            except Exception as e:
                print(f"Error processing item {item.get('key')}: {e}")
                stats['errors'] += 1

        return stats

    def close(self):
        """Close all external API clients."""
        if self.crossref:
            self.crossref.close()
        if self.openalex:
            self.openalex.close()
        if self.semantic_scholar:
            self.semantic_scholar.close()
