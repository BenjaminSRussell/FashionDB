"""Scraping configuration - all settings in one place."""

from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "independent_content.db"

# Scraping settings (deterministic)
SCRAPING_CONFIG = {
    'max_retries': 3,
    'retry_delay_seconds': 2.0,
    'request_delay_seconds': 1.0,
    'min_content_length': 300,
    'request_timeout_seconds': 30,
    'user_agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
}

# Quality thresholds
QUALITY_THRESHOLDS = {
    'high_quality_score': 70,
    'medium_quality_score': 40,
    'min_fashion_terms': 5,
    'min_paragraphs': 3,
    'min_words_high_quality': 1000
}

# Fashion terms for validation
FASHION_TERMS = {
    'suit', 'jacket', 'blazer', 'pants', 'trousers', 'shirt', 'tie',
    'shoes', 'boots', 'sneakers', 'loafers', 'denim', 'jeans', 'chinos',
    'style', 'fashion', 'outfit', 'wardrobe', 'fit', 'tailoring',
    'casual', 'formal', 'preppy', 'classic', 'streetwear', 'minimalist',
    'cotton', 'wool', 'linen', 'silk', 'leather', 'suede',
    'navy', 'gray', 'black', 'brown', 'khaki'
}
