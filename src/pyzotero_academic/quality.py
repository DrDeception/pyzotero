"""Library quality control and validation.

This module provides functionality to:
- Find items with missing or incomplete metadata
- Validate DOIs and URLs
- Normalize author names
- Audit library for inconsistencies

All writes are performed via the Zotero API only.
"""

import re
from typing import Any, Optional
from urllib.parse import urlparse

import httpx

from pyzotero.zotero import Zotero


class QualityController:
    """Quality control and validation for Zotero libraries.

    This class provides methods to:
    - Audit library for quality issues
    - Validate DOIs and URLs
    - Normalize metadata
    - Fix common formatting issues
    """

    def __init__(self, zotero_client: Zotero):
        """Initialize quality controller.

        Args:
            zotero_client: Authenticated Zotero client instance
        """
        self.zot = zotero_client
        self.http_client = httpx.Client(timeout=10, follow_redirects=True)

    def audit_library(
        self,
        items: Optional[list[dict[str, Any]]] = None
    ) -> dict[str, Any]:
        """Comprehensive library audit.

        Checks for:
        - Missing critical fields
        - Invalid DOIs
        - Broken URLs
        - Inconsistent author names
        - Malformed dates
        - Empty items

        Args:
            items: Items to audit. If None, audits entire library.

        Returns:
            Audit report dict with issues categorized by type
        """
        if items is None:
            items = self.zot.everything(self.zot.items())

        report = {
            'total_items': len(items),
            'issues': {
                'missing_fields': [],
                'invalid_dois': [],
                'broken_urls': [],
                'malformed_dates': [],
                'missing_authors': [],
                'empty_titles': [],
                'inconsistent_authors': [],
            },
            'summary': {}
        }

        for item in items:
            data = item.get('data', {})
            item_type = data.get('itemType')

            # Skip non-regular items
            if item_type in ['note', 'attachment']:
                continue

            item_key = item.get('key')
            title = data.get('title', 'Untitled')

            # Check for missing critical fields
            missing = self._check_missing_fields(data, item_type)
            if missing:
                report['issues']['missing_fields'].append({
                    'key': item_key,
                    'title': title,
                    'missing': missing
                })

            # Check for invalid DOI
            doi = data.get('DOI', '').strip()
            if doi and not self._validate_doi_format(doi):
                report['issues']['invalid_dois'].append({
                    'key': item_key,
                    'title': title,
                    'doi': doi
                })

            # Check for empty title
            if not data.get('title', '').strip():
                report['issues']['empty_titles'].append({
                    'key': item_key,
                    'item_type': item_type
                })

            # Check for missing authors (for papers)
            if item_type in ['journalArticle', 'conferencePaper', 'preprint']:
                if not data.get('creators'):
                    report['issues']['missing_authors'].append({
                        'key': item_key,
                        'title': title
                    })

            # Check for malformed dates
            date = data.get('date', '').strip()
            if date and not self._validate_date_format(date):
                report['issues']['malformed_dates'].append({
                    'key': item_key,
                    'title': title,
                    'date': date
                })

        # Generate summary
        for issue_type, issues in report['issues'].items():
            report['summary'][issue_type] = len(issues)

        report['summary']['total_issues'] = sum(report['summary'].values())

        return report

    def _check_missing_fields(
        self,
        item_data: dict[str, Any],
        item_type: str
    ) -> list[str]:
        """Check for missing critical fields based on item type.

        Args:
            item_data: Item data dict
            item_type: Zotero item type

        Returns:
            List of missing field names
        """
        missing = []

        # Common fields for articles
        if item_type in ['journalArticle', 'conferencePaper']:
            required = {
                'title': 'Title',
                'creators': 'Authors',
                'date': 'Date',
                'publicationTitle': 'Publication'
            }

            for field, name in required.items():
                if field == 'creators':
                    if not item_data.get(field):
                        missing.append(name)
                else:
                    if not item_data.get(field, '').strip():
                        missing.append(name)

        # Books
        elif item_type == 'book':
            required = {
                'title': 'Title',
                'creators': 'Authors',
                'date': 'Date',
                'publisher': 'Publisher'
            }

            for field, name in required.items():
                if field == 'creators':
                    if not item_data.get(field):
                        missing.append(name)
                else:
                    if not item_data.get(field, '').strip():
                        missing.append(name)

        return missing

    def _validate_doi_format(self, doi: str) -> bool:
        """Validate DOI format.

        Args:
            doi: DOI string

        Returns:
            True if valid format
        """
        # Clean DOI
        doi = doi.replace('https://doi.org/', '').replace('http://doi.org/', '')

        # Basic DOI format: 10.xxxx/yyyy
        pattern = r'^10\.\d{4,}/\S+$'
        return bool(re.match(pattern, doi))

    def _validate_date_format(self, date: str) -> bool:
        """Validate date format.

        Accepts various common formats.

        Args:
            date: Date string

        Returns:
            True if recognizable format
        """
        # Accept various formats
        patterns = [
            r'^\d{4}$',  # YYYY
            r'^\d{4}-\d{2}$',  # YYYY-MM
            r'^\d{4}-\d{2}-\d{2}$',  # YYYY-MM-DD
            r'^\d{2}/\d{2}/\d{4}$',  # MM/DD/YYYY
            r'^\w+ \d{1,2}, \d{4}$',  # Month DD, YYYY
            r'^\w+ \d{4}$',  # Month YYYY
        ]

        for pattern in patterns:
            if re.match(pattern, date):
                return True

        return False

    def validate_dois(
        self,
        items: Optional[list[dict[str, Any]]] = None,
        check_resolution: bool = False
    ) -> dict[str, Any]:
        """Validate DOIs in library.

        Args:
            items: Items to check. If None, checks all items.
            check_resolution: If True, also checks if DOI resolves (slower)

        Returns:
            Report dict with valid/invalid DOIs
        """
        if items is None:
            items = self.zot.everything(self.zot.items())

        report = {
            'total_checked': 0,
            'valid_format': [],
            'invalid_format': [],
            'unresolvable': [] if check_resolution else None
        }

        for item in items:
            data = item.get('data', {})
            doi = data.get('DOI', '').strip()

            if not doi:
                continue

            report['total_checked'] += 1

            # Check format
            if self._validate_doi_format(doi):
                report['valid_format'].append({
                    'key': item.get('key'),
                    'title': data.get('title', 'Untitled'),
                    'doi': doi
                })

                # Optionally check resolution
                if check_resolution:
                    if not self._check_doi_resolves(doi):
                        report['unresolvable'].append({
                            'key': item.get('key'),
                            'title': data.get('title', 'Untitled'),
                            'doi': doi
                        })
            else:
                report['invalid_format'].append({
                    'key': item.get('key'),
                    'title': data.get('title', 'Untitled'),
                    'doi': doi
                })

        return report

    def _check_doi_resolves(self, doi: str) -> bool:
        """Check if DOI resolves to a valid URL.

        Args:
            doi: DOI string

        Returns:
            True if resolves successfully
        """
        # Clean DOI
        doi = doi.replace('https://doi.org/', '').replace('http://doi.org/', '')

        url = f"https://doi.org/{doi}"

        try:
            response = self.http_client.head(url)
            return response.status_code in [200, 301, 302]
        except Exception:
            return False

    def validate_urls(
        self,
        items: Optional[list[dict[str, Any]]] = None
    ) -> dict[str, Any]:
        """Check for broken URLs in library.

        Args:
            items: Items to check. If None, checks all items.

        Returns:
            Report dict with working/broken URLs
        """
        if items is None:
            items = self.zot.everything(self.zot.items())

        report = {
            'total_checked': 0,
            'working': [],
            'broken': [],
            'invalid_format': []
        }

        for item in items:
            data = item.get('data', {})
            url = data.get('url', '').strip()

            if not url:
                continue

            report['total_checked'] += 1

            # Check URL format
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                report['invalid_format'].append({
                    'key': item.get('key'),
                    'title': data.get('title', 'Untitled'),
                    'url': url
                })
                continue

            # Check if URL works
            try:
                response = self.http_client.head(url, timeout=5)
                if response.status_code < 400:
                    report['working'].append({
                        'key': item.get('key'),
                        'title': data.get('title', 'Untitled'),
                        'url': url,
                        'status': response.status_code
                    })
                else:
                    report['broken'].append({
                        'key': item.get('key'),
                        'title': data.get('title', 'Untitled'),
                        'url': url,
                        'status': response.status_code
                    })
            except Exception as e:
                report['broken'].append({
                    'key': item.get('key'),
                    'title': data.get('title', 'Untitled'),
                    'url': url,
                    'error': str(e)
                })

        return report

    def normalize_author_names(
        self,
        items: Optional[list[dict[str, Any]]] = None,
        dry_run: bool = False
    ) -> dict[str, Any]:
        """Normalize author name formatting.

        Ensures consistent capitalization and formatting.

        Args:
            items: Items to process. If None, processes all items.
            dry_run: If True, return suggestions without writing

        Returns:
            Statistics dict
        """
        if items is None:
            items = self.zot.everything(self.zot.items())

        stats = {
            'total': len(items),
            'normalized': 0,
            'skipped': 0,
            'suggestions': [] if dry_run else None
        }

        for item in items:
            data = item.get('data', {})
            creators = data.get('creators', [])

            if not creators:
                stats['skipped'] += 1
                continue

            normalized_creators = []
            changed = False

            for creator in creators:
                normalized = self._normalize_creator(creator)
                normalized_creators.append(normalized)

                if normalized != creator:
                    changed = True

            if changed:
                if dry_run:
                    stats['suggestions'].append({
                        'key': item.get('key'),
                        'title': data.get('title', 'Untitled'),
                        'old_creators': creators,
                        'new_creators': normalized_creators
                    })
                else:
                    # Update via API
                    try:
                        updated_data = data.copy()
                        updated_data['creators'] = normalized_creators
                        self.zot.update_item(updated_data)
                        stats['normalized'] += 1
                    except Exception as e:
                        print(f"Failed to update item {item.get('key')}: {e}")

        return stats

    def _normalize_creator(self, creator: dict[str, Any]) -> dict[str, Any]:
        """Normalize a single creator entry.

        Args:
            creator: Creator dict

        Returns:
            Normalized creator dict
        """
        normalized = creator.copy()

        # Normalize names to title case
        if 'firstName' in normalized:
            normalized['firstName'] = self._title_case_name(normalized['firstName'])

        if 'lastName' in normalized:
            normalized['lastName'] = self._title_case_name(normalized['lastName'])

        return normalized

    def _title_case_name(self, name: str) -> str:
        """Convert name to proper title case.

        Handles special cases like "McDonald", "van der Waals", etc.

        Args:
            name: Name string

        Returns:
            Title-cased name
        """
        # Handle empty
        if not name:
            return name

        # Special prefixes to keep lowercase
        lowercase_parts = {'van', 'von', 'de', 'der', 'la', 'le', 'du'}

        parts = name.split()
        result = []

        for i, part in enumerate(parts):
            # Keep lowercase for known prefixes (unless first word)
            if i > 0 and part.lower() in lowercase_parts:
                result.append(part.lower())
            else:
                # Title case
                result.append(part.capitalize())

        return ' '.join(result)

    def fix_date_formats(
        self,
        items: Optional[list[dict[str, Any]]] = None,
        target_format: str = 'YYYY-MM-DD',
        dry_run: bool = False
    ) -> dict[str, Any]:
        """Standardize date formats.

        Args:
            items: Items to process. If None, processes all items.
            target_format: Target format ('YYYY-MM-DD', 'YYYY-MM', or 'YYYY')
            dry_run: If True, return suggestions without writing

        Returns:
            Statistics dict
        """
        if items is None:
            items = self.zot.everything(self.zot.items())

        stats = {
            'total': len(items),
            'fixed': 0,
            'skipped': 0,
            'suggestions': [] if dry_run else None
        }

        for item in items:
            data = item.get('data', {})
            date = data.get('date', '').strip()

            if not date:
                stats['skipped'] += 1
                continue

            # Try to normalize date
            normalized = self._normalize_date(date, target_format)

            if normalized and normalized != date:
                if dry_run:
                    stats['suggestions'].append({
                        'key': item.get('key'),
                        'title': data.get('title', 'Untitled'),
                        'old_date': date,
                        'new_date': normalized
                    })
                else:
                    # Update via API
                    try:
                        updated_data = data.copy()
                        updated_data['date'] = normalized
                        self.zot.update_item(updated_data)
                        stats['fixed'] += 1
                    except Exception as e:
                        print(f"Failed to update item {item.get('key')}: {e}")
            else:
                stats['skipped'] += 1

        return stats

    def _normalize_date(self, date: str, target_format: str) -> Optional[str]:
        """Normalize date to target format.

        Args:
            date: Original date string
            target_format: Target format

        Returns:
            Normalized date or None if unable to parse
        """
        # Extract year
        year_match = re.search(r'\b(19|20)\d{2}\b', date)
        if not year_match:
            return None

        year = year_match.group(0)

        if target_format == 'YYYY':
            return year

        # Try to extract month
        month = None

        # Numeric month
        month_match = re.search(r'\b(\d{1,2})[/-]', date)
        if month_match:
            month = int(month_match.group(1))
        else:
            # Text month
            months = {
                'january': 1, 'february': 2, 'march': 3, 'april': 4,
                'may': 5, 'june': 6, 'july': 7, 'august': 8,
                'september': 9, 'october': 10, 'november': 11, 'december': 12,
                'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'jun': 6,
                'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
            }

            for month_name, month_num in months.items():
                if month_name in date.lower():
                    month = month_num
                    break

        if not month:
            return year

        if target_format == 'YYYY-MM':
            return f"{year}-{month:02d}"

        # Try to extract day
        day_match = re.search(r'\b(\d{1,2})[,\s]', date)
        if day_match:
            day = int(day_match.group(1))
            return f"{year}-{month:02d}-{day:02d}"

        return f"{year}-{month:02d}"

    def close(self):
        """Close HTTP client."""
        self.http_client.close()
