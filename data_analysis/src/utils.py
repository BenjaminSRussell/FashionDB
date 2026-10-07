import json
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"

def load_json(filepath: Path) -> Any:
    """Load JSON file with error handling."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as e:
        print(f"JSON decode error in {filepath}: {e}")
        return None

def save_json(data: Any, filepath: Path, indent: int = 4):
    """Save data to JSON file."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)

def load_posts(data_path: Path) -> List[Dict]:
    """Load posts from Reddit JSON data."""
    data = load_json(data_path)
    if not data:
        return []

    posts = []
    for subreddit, subreddit_posts in data.items():
        posts.extend(subreddit_posts)
    return posts

def get_top_comment(post: Dict) -> Optional[Dict]:
    """Get highest scoring comment from a post."""
    comments = post.get('comments', [])
    if not comments:
        return None
    return max(comments, key=lambda c: c.get('score', 0))

def normalize_whitespace(text: str) -> str:
    """Collapse multiple whitespace into single space."""
    import re
    return re.sub(r'\s+', ' ', text).strip()
