"""Basic tests for pyzotero_academic modules.

These tests verify:
1. Modules can be imported
2. Classes can be instantiated
3. Basic functionality works without API calls
"""

import pytest

# Test imports
def test_imports():
    """Test that all modules can be imported."""
    from pyzotero_academic import MetadataEnricher, SmartOrganizer, QualityController
    from pyzotero_academic.enrichment import MetadataEnricher as Enricher
    from pyzotero_academic.organize import SmartOrganizer as Organizer
    from pyzotero_academic.quality import QualityController as QC

    assert MetadataEnricher is Enricher
    assert SmartOrganizer is Organizer
    assert QualityController is QC


def test_external_apis_import():
    """Test that external API clients can be imported."""
    from pyzotero_academic.utils import CrossRefAPI, OpenAlexAPI, SemanticScholarAPI

    assert CrossRefAPI is not None
    assert OpenAlexAPI is not None
    assert SemanticScholarAPI is not None


def test_metadata_enricher_helpers():
    """Test MetadataEnricher helper methods without API calls."""
    from pyzotero_academic.enrichment import MetadataEnricher

    # Create mock Zotero client
    class MockZotero:
        pass

    mock_zot = MockZotero()
    enricher = MetadataEnricher(
        mock_zot,
        use_crossref=False,
        use_openalex=False,
        use_semantic_scholar=False
    )

    # Test DOI cleaning
    assert enricher._clean_doi("https://doi.org/10.1234/test") == "10.1234/test"
    assert enricher._clean_doi("http://doi.org/10.1234/test") == "10.1234/test"
    assert enricher._clean_doi("doi:10.1234/test") == "10.1234/test"
    assert enricher._clean_doi("10.1234/test") == "10.1234/test"

    # Test DOI extraction from item
    item = {
        'data': {
            'DOI': '10.1234/test',
            'title': 'Test Article'
        }
    }
    assert enricher.extract_doi(item) == "10.1234/test"

    # Test DOI extraction from extra field
    item_extra = {
        'data': {
            'extra': 'DOI: 10.5678/test',
            'title': 'Test Article'
        }
    }
    assert enricher.extract_doi(item_extra) == "10.5678/test"

    # Test inverted index reconstruction
    inverted_index = {
        'This': [0],
        'is': [1],
        'a': [2],
        'test': [3],
        'abstract': [4]
    }
    result = enricher._reconstruct_abstract(inverted_index)
    assert result == "This is a test abstract"


def test_smart_organizer_helpers():
    """Test SmartOrganizer helper methods."""
    from pyzotero_academic.organize import SmartOrganizer

    class MockZotero:
        pass

    organizer = SmartOrganizer(MockZotero())

    # Test title normalization
    assert organizer._normalize_title("Test: Article Title!") == "test article title"
    assert organizer._normalize_title("  Multiple   Spaces  ") == "multiple spaces"

    # Test author name extraction
    creators = [
        {'creatorType': 'author', 'lastName': 'Smith'},
        {'creatorType': 'author', 'lastName': 'Jones'},
        {'creatorType': 'editor', 'lastName': 'Brown'}
    ]
    authors = organizer._extract_author_names(creators)
    assert 'smith' in authors
    assert 'jones' in authors
    assert 'brown' in authors

    # Test year extraction
    assert organizer._extract_year('2023-01-01') == '2023'
    assert organizer._extract_year('January 2022') == '2022'
    assert organizer._extract_year('1999') == '1999'

    # Test keyword extraction
    keywords = organizer._extract_keywords('This is a test article about machine learning')
    assert 'test' in keywords
    assert 'article' in keywords
    assert 'machine' in keywords
    assert 'learning' in keywords
    assert 'this' not in keywords  # Stop word
    assert 'is' not in keywords  # Stop word


def test_quality_controller_helpers():
    """Test QualityController helper methods."""
    from pyzotero_academic.quality import QualityController

    class MockZotero:
        pass

    qc = QualityController(MockZotero())

    # Test DOI format validation
    assert qc._validate_doi_format('10.1234/test') is True
    assert qc._validate_doi_format('10.1234/test.v1') is True
    assert qc._validate_doi_format('invalid') is False
    assert qc._validate_doi_format('10.12/') is False

    # Test date format validation
    assert qc._validate_date_format('2023') is True
    assert qc._validate_date_format('2023-01') is True
    assert qc._validate_date_format('2023-01-15') is True
    assert qc._validate_date_format('01/15/2023') is True
    assert qc._validate_date_format('January 2023') is True
    assert qc._validate_date_format('Jan 15, 2023') is True
    assert qc._validate_date_format('invalid') is False

    # Test title case name formatting
    assert qc._title_case_name('john smith') == 'John Smith'
    assert qc._title_case_name('JOHN SMITH') == 'John Smith'
    assert qc._title_case_name('jean-luc picard') == 'Jean-Luc Picard'
    assert qc._title_case_name('van der Waals') == 'Van der Waals'

    # Test date normalization
    assert qc._normalize_date('2023-01-15', 'YYYY') == '2023'
    assert qc._normalize_date('January 2023', 'YYYY-MM') == '2023-01'
    assert qc._normalize_date('2023', 'YYYY') == '2023'

    # Test missing fields check
    item_data = {
        'itemType': 'journalArticle',
        'title': 'Test',
        'creators': [{'lastName': 'Smith'}],
        # Missing 'date' and 'publicationTitle'
    }
    missing = qc._check_missing_fields(item_data, 'journalArticle')
    assert 'Date' in missing
    assert 'Publication' in missing


def test_external_api_clients():
    """Test that external API clients can be instantiated."""
    from pyzotero_academic.utils.external_apis import (
        CrossRefAPI,
        OpenAlexAPI,
        SemanticScholarAPI
    )

    # Test instantiation (no actual API calls)
    crossref = CrossRefAPI(email='test@example.com')
    assert crossref is not None
    crossref.close()

    openalex = OpenAlexAPI(email='test@example.com')
    assert openalex is not None
    openalex.close()

    scholar = SemanticScholarAPI()
    assert scholar is not None
    scholar.close()


def test_completeness_scoring():
    """Test item completeness scoring."""
    from pyzotero_academic.organize import SmartOrganizer

    class MockZotero:
        pass

    organizer = SmartOrganizer(MockZotero())

    # Empty item
    empty_item = {}
    assert organizer._score_item_completeness(empty_item) == 0

    # Item with some fields
    partial_item = {
        'DOI': '10.1234/test',
        'title': 'Test',
        'abstractNote': 'This is a test abstract',
        'creators': [{'lastName': 'Smith'}]
    }
    score1 = organizer._score_item_completeness(partial_item)
    assert score1 > 0

    # Item with more fields
    complete_item = {
        'DOI': '10.1234/test',
        'title': 'Test',
        'abstractNote': 'This is a test abstract',
        'date': '2023',
        'publicationTitle': 'Test Journal',
        'volume': '1',
        'issue': '2',
        'pages': '1-10',
        'creators': [{'lastName': 'Smith'}, {'lastName': 'Jones'}],
        'tags': [{'tag': 'test'}]
    }
    score2 = organizer._score_item_completeness(complete_item)
    assert score2 > score1


def test_author_list_comparison():
    """Test author list comparison."""
    from pyzotero_academic.organize import SmartOrganizer

    class MockZotero:
        pass

    organizer = SmartOrganizer(MockZotero())

    # Identical authors
    authors1 = ['smith', 'jones', 'brown']
    authors2 = ['smith', 'jones', 'brown']
    assert organizer._compare_author_lists(authors1, authors2) == 1.0

    # Partial overlap
    authors3 = ['smith', 'jones']
    authors4 = ['smith', 'jones', 'brown', 'white']
    similarity = organizer._compare_author_lists(authors3, authors4)
    assert 0 < similarity < 1

    # No overlap
    authors5 = ['smith', 'jones']
    authors6 = ['brown', 'white']
    assert organizer._compare_author_lists(authors5, authors6) == 0

    # Empty lists
    assert organizer._compare_author_lists([], []) == 0
    assert organizer._compare_author_lists(['smith'], []) == 0
