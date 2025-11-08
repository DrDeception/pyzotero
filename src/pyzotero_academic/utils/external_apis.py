"""External API clients for academic metadata sources.

This module provides client classes for interacting with:
- CrossRef (DOI metadata)
- OpenAlex (comprehensive academic metadata)
- Semantic Scholar (citations, recommendations)

All APIs used are free and don't require API keys.
"""

import time
from typing import Any, Optional
from urllib.parse import quote

import httpx


class CrossRefAPI:
    """Client for CrossRef API (https://api.crossref.org).

    CrossRef provides metadata for DOIs. No API key required.
    Use polite pool by providing email in user agent.
    """

    BASE_URL = "https://api.crossref.org"

    def __init__(self, email: Optional[str] = None, timeout: int = 30):
        """Initialize CrossRef API client.

        Args:
            email: Email for polite pool (gets faster responses)
            timeout: Request timeout in seconds
        """
        headers = {
            "User-Agent": f"Pyzotero-Academic/0.1 (mailto:{email or 'anonymous'})"
        }
        self.client = httpx.Client(headers=headers, timeout=timeout)

    def get_work_by_doi(self, doi: str) -> Optional[dict[str, Any]]:
        """Fetch metadata for a DOI.

        Args:
            doi: The DOI to lookup (with or without https://doi.org/ prefix)

        Returns:
            Metadata dict or None if not found
        """
        # Clean DOI
        doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "")

        url = f"{self.BASE_URL}/works/{quote(doi, safe='')}"

        try:
            response = self.client.get(url)
            if response.status_code == 200:
                data = response.json()
                return data.get("message")
            return None
        except Exception:
            return None

    def search_works(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search for works by query string.

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of work metadata dicts
        """
        url = f"{self.BASE_URL}/works"
        params = {"query": query, "rows": limit}

        try:
            response = self.client.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                return data.get("message", {}).get("items", [])
            return []
        except Exception:
            return []

    def close(self):
        """Close the HTTP client."""
        self.client.close()


class OpenAlexAPI:
    """Client for OpenAlex API (https://openalex.org).

    OpenAlex provides comprehensive academic metadata including citations,
    author information, venues, and more. No API key required.
    """

    BASE_URL = "https://api.openalex.org"

    def __init__(self, email: Optional[str] = None, timeout: int = 30):
        """Initialize OpenAlex API client.

        Args:
            email: Email for polite pool (recommended)
            timeout: Request timeout in seconds
        """
        headers = {}
        self.params = {}
        if email:
            # OpenAlex uses email in query param for polite pool
            self.params["mailto"] = email

        self.client = httpx.Client(
            headers=headers,
            timeout=timeout,
            follow_redirects=True
        )

    def get_work_by_doi(self, doi: str) -> Optional[dict[str, Any]]:
        """Fetch work metadata by DOI.

        Args:
            doi: The DOI to lookup

        Returns:
            Work metadata dict or None if not found
        """
        # Clean DOI
        doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "")

        url = f"{self.BASE_URL}/works/doi:{doi}"

        try:
            response = self.client.get(url, params=self.params)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception:
            return None

    def get_work_by_id(self, openalex_id: str) -> Optional[dict[str, Any]]:
        """Fetch work metadata by OpenAlex ID.

        Args:
            openalex_id: OpenAlex work ID (e.g., 'W2741809807')

        Returns:
            Work metadata dict or None if not found
        """
        url = f"{self.BASE_URL}/works/{openalex_id}"

        try:
            response = self.client.get(url, params=self.params)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception:
            return None

    def search_works(
        self,
        query: str = None,
        title: str = None,
        author: str = None,
        limit: int = 10
    ) -> list[dict[str, Any]]:
        """Search for works.

        Args:
            query: General search query
            title: Search by title
            author: Search by author name
            limit: Maximum number of results

        Returns:
            List of work metadata dicts
        """
        url = f"{self.BASE_URL}/works"
        params = {**self.params, "per-page": limit}

        # Build filter query
        filters = []
        if title:
            params["search"] = title
        if query:
            params["search"] = query
        if author:
            filters.append(f"author.search:{author}")

        if filters:
            params["filter"] = ",".join(filters)

        try:
            response = self.client.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                return data.get("results", [])
            return []
        except Exception:
            return []

    def get_related_works(self, openalex_id: str, limit: int = 10) -> list[dict[str, Any]]:
        """Get works related to a given work.

        Args:
            openalex_id: OpenAlex work ID
            limit: Maximum number of results

        Returns:
            List of related work metadata dicts
        """
        url = f"{self.BASE_URL}/works/{openalex_id}/related_works"
        params = {**self.params, "per-page": limit}

        try:
            response = self.client.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                return data.get("results", [])
            return []
        except Exception:
            return []

    def get_citing_works(self, openalex_id: str, limit: int = 100) -> list[dict[str, Any]]:
        """Get works that cite a given work.

        Args:
            openalex_id: OpenAlex work ID
            limit: Maximum number of results

        Returns:
            List of citing work metadata dicts
        """
        url = f"{self.BASE_URL}/works"
        params = {
            **self.params,
            "filter": f"cites:{openalex_id}",
            "per-page": limit
        }

        try:
            response = self.client.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                return data.get("results", [])
            return []
        except Exception:
            return []

    def close(self):
        """Close the HTTP client."""
        self.client.close()


class SemanticScholarAPI:
    """Client for Semantic Scholar API (https://www.semanticscholar.org).

    Semantic Scholar provides paper metadata, citations, and recommendations.
    Free tier: 1 request/second, no API key required.
    """

    BASE_URL = "https://api.semanticscholar.org/graph/v1"

    def __init__(self, timeout: int = 30):
        """Initialize Semantic Scholar API client.

        Args:
            timeout: Request timeout in seconds
        """
        headers = {
            "User-Agent": "Pyzotero-Academic/0.1"
        }
        self.client = httpx.Client(headers=headers, timeout=timeout)
        self.last_request_time = 0
        self.rate_limit_delay = 1.0  # 1 second between requests

    def _rate_limit(self):
        """Enforce rate limiting (1 req/sec for free tier)."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = time.time()

    def get_paper_by_doi(self, doi: str, fields: Optional[list[str]] = None) -> Optional[dict[str, Any]]:
        """Fetch paper metadata by DOI.

        Args:
            doi: The DOI to lookup
            fields: List of fields to return (default: all common fields)

        Returns:
            Paper metadata dict or None if not found
        """
        self._rate_limit()

        if fields is None:
            fields = [
                "title", "abstract", "year", "authors", "citationCount",
                "influentialCitationCount", "references", "citations",
                "tldr", "venue", "publicationDate"
            ]

        # Clean DOI
        doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "")

        url = f"{self.BASE_URL}/paper/DOI:{doi}"
        params = {"fields": ",".join(fields)}

        try:
            response = self.client.get(url, params=params)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception:
            return None

    def get_paper_by_id(self, paper_id: str, fields: Optional[list[str]] = None) -> Optional[dict[str, Any]]:
        """Fetch paper metadata by Semantic Scholar ID.

        Args:
            paper_id: Semantic Scholar paper ID
            fields: List of fields to return

        Returns:
            Paper metadata dict or None if not found
        """
        self._rate_limit()

        if fields is None:
            fields = [
                "title", "abstract", "year", "authors", "citationCount",
                "influentialCitationCount", "tldr"
            ]

        url = f"{self.BASE_URL}/paper/{paper_id}"
        params = {"fields": ",".join(fields)}

        try:
            response = self.client.get(url, params=params)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception:
            return None

    def get_recommendations(self, paper_id: str, limit: int = 10) -> list[dict[str, Any]]:
        """Get paper recommendations based on a given paper.

        Args:
            paper_id: Semantic Scholar paper ID
            limit: Maximum number of recommendations

        Returns:
            List of recommended paper metadata dicts
        """
        self._rate_limit()

        url = f"{self.BASE_URL}/paper/{paper_id}/recommendations"
        params = {"limit": limit}

        try:
            response = self.client.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                return data.get("recommendedPapers", [])
            return []
        except Exception:
            return []

    def search_papers(
        self,
        query: str,
        limit: int = 10,
        fields: Optional[list[str]] = None
    ) -> list[dict[str, Any]]:
        """Search for papers by query.

        Args:
            query: Search query
            limit: Maximum number of results
            fields: List of fields to return

        Returns:
            List of paper metadata dicts
        """
        self._rate_limit()

        if fields is None:
            fields = ["title", "abstract", "year", "authors", "citationCount"]

        url = f"{self.BASE_URL}/paper/search"
        params = {
            "query": query,
            "limit": limit,
            "fields": ",".join(fields)
        }

        try:
            response = self.client.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                return data.get("data", [])
            return []
        except Exception:
            return []

    def close(self):
        """Close the HTTP client."""
        self.client.close()
