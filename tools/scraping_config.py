"""
Deterministic scraping configuration.
All settings in one place for replicable runs.
"""

from pathlib import Path
from typing import List, Dict

# Base paths (deterministic)
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "independent_content.db"
REPORTS_DIR = BASE_DIR / "reports"
VALIDATION_DIR = BASE_DIR / "validation"

# Scraping parameters (deterministic)
SCRAPING_CONFIG = {
    # Retry behavior
    'max_retries': 3,
    'retry_delay_seconds': 2.0,  # Fixed delay between retries

    # Rate limiting
    'request_delay_seconds': 1.0,  # Fixed delay between requests
    'batch_delay_seconds': 5.0,    # Fixed delay between URL batches

    # Content quality thresholds
    'min_content_length': 300,     # Minimum chars to consider valid
    'min_word_count': 50,          # Minimum words for quality article

    # Timeout settings
    'request_timeout_seconds': 30,
    'max_scraping_time_minutes': 60,

    # User agent (deterministic)
    'user_agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',

    # Headers (deterministic)
    'headers': {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
}

# Article quality thresholds (deterministic)
QUALITY_THRESHOLDS = {
    'high_quality_score': 70,      # 70+ = high quality
    'medium_quality_score': 40,    # 40-69 = medium quality
    'low_quality_score': 40,       # <40 = low quality

    'complete_truncation_threshold': 0.2,   # <0.2 = complete
    'truncated_threshold': 0.5,              # >0.5 = likely truncated

    'min_fashion_terms': 5,        # Minimum fashion terms for relevance
    'min_paragraphs': 3,           # Minimum paragraphs for structure
    'min_words_high_quality': 1000 # Minimum words for high quality
}

# Source prioritization (deterministic)
# Sources with proven high success rates
RELIABLE_SOURCES = [
    'putthison.com',
    'ivy-style.com',
    'dappered.com',
    'stitchdown.com',
    'primermagazine.com',
    'hespokestyle.com',
    'permanentstyle.com',
    'effortlessgent.com',
    'gentlemansgazette.com',
    'denimhunters.com',
    'heddels.com',
    'highsnobiety.com',
    'valetmag.com'
]

# Known problematic sources (deterministic)
# These have bot protection or require JavaScript
BLOCKED_SOURCES = [
    'mrporter.com',           # Cloudflare 503
    'thearmoury.com',         # JavaScript-heavy
    'oxfordclothbuttondown.com',  # Cloudflare 503
    'hypebeast.com',          # 405 Method Not Allowed
    'grailed.com'             # Cloudflare 503
]

# URL filtering patterns (deterministic)
URL_SKIP_PATTERNS = [
    r'reddit\.com',           # No Reddit
    r'/amp/',                 # No AMP pages
    r'/print/',               # No print versions
    r'/feed/',                # No RSS feeds
    r'\.pdf$',                # No PDFs
    r'\.jpg$', r'\.png$',     # No images
    r'/tag/',                 # No tag pages
    r'/category/',            # No category pages
    r'/author/',              # No author pages
    r'/page/\d+',             # No pagination pages
]

# Fashion terminology (deterministic - used for content validation)
FASHION_TERMS = {
    # Garments
    'suit', 'jacket', 'blazer', 'pants', 'trousers', 'shirt', 'tie',
    'shoes', 'boots', 'sneakers', 'loafers', 'denim', 'jeans', 'chinos',
    'sweater', 'cardigan', 'coat', 'overcoat',

    # Styles
    'style', 'fashion', 'outfit', 'wardrobe', 'fit', 'tailoring',
    'casual', 'formal', 'preppy', 'classic', 'modern', 'vintage',
    'streetwear', 'minimalist',

    # Materials
    'cotton', 'wool', 'linen', 'silk', 'leather', 'suede',
    'tweed', 'flannel', 'chambray', 'oxford',

    # Colors
    'navy', 'gray', 'grey', 'black', 'brown', 'khaki', 'olive',

    # Fit terms
    'slim', 'regular', 'relaxed', 'tapered', 'bespoke', 'tailored'
}

# Database schema version (for migrations)
DB_VERSION = 1

def get_scraping_config() -> Dict:
    """Get scraping configuration as dictionary."""
    return SCRAPING_CONFIG.copy()

def get_quality_thresholds() -> Dict:
    """Get quality thresholds as dictionary."""
    return QUALITY_THRESHOLDS.copy()

def is_reliable_source(url: str) -> bool:
    """Check if URL is from a reliable source."""
    return any(source in url for source in RELIABLE_SOURCES)

def is_blocked_source(url: str) -> bool:
    """Check if URL is from a known blocked source."""
    return any(source in url for source in BLOCKED_SOURCES)

def should_skip_url(url: str) -> bool:
    """Check if URL should be skipped based on patterns."""
    import re
    return any(re.search(pattern, url, re.IGNORECASE)
              for pattern in URL_SKIP_PATTERNS)
