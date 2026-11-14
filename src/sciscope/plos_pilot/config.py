"""Fixed PLOS pilot search settings and per-run request limits."""

QUERY_ARMS = (
    'title:"Apis mellifera"',
    'abstract:"Apis mellifera"',
    'title:"honey bee"',
    'abstract:"honey bee"',
    "title:honeybee",
    "abstract:honeybee",
)
FILTER_QUERIES = ("doc_type:full", 'article_type:"research article"')
SOLR_FIELDS = ("id", "title", "journal", "publication_date", "abstract")
MAX_ROWS = 100
MIN_REQUEST_SPACING_SECONDS = 6.0
MAX_REQUESTS_PER_RUN = 300
SEARCH_URL = "https://api.plos.org/search"
JOURNAL_HOST = "journals.plos.org"
JOURNAL_ROUTES = {"PLOS ONE": "plosone"}
