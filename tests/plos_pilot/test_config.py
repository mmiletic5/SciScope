"""Behavior checks for fixed PLOS search configuration."""

from sciscope.plos_pilot import config


def test_six_query_arms_and_solr_fields() -> None:
    """Search configuration covers both fields and all three expressions."""
    assert config.QUERY_ARMS == (
        'title:"Apis mellifera"',
        'abstract:"Apis mellifera"',
        'title:"honey bee"',
        'abstract:"honey bee"',
        "title:honeybee",
        "abstract:honeybee",
    )
    assert config.FILTER_QUERIES == (
        "doc_type:full",
        'article_type:"research article"',
    )
    assert config.SOLR_FIELDS == (
        "id",
        "title",
        "journal",
        "publication_date",
        "abstract",
    )


def test_request_limits_and_hosts() -> None:
    """Fixed limits and hosts are safe for the pilot."""
    assert 1 <= config.MAX_ROWS <= 100
    assert config.MIN_REQUEST_SPACING_SECONDS == 6.0
    assert config.MAX_REQUESTS_PER_RUN == 300
    assert config.SEARCH_URL == "https://api.plos.org/search"
    assert config.JOURNAL_HOST == "journals.plos.org"
