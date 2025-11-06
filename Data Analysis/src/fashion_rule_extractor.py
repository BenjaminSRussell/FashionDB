"""
Extract fashion rules from Reddit posts using MLX-LM.

This script processes Reddit fashion posts and uses a large language model
to extract specific fashion rules or advice mentioned in the post titles,
selftext, and top comments.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

try:
    from mlx_lm import load, generate
except ImportError:
    load = None
    generate = None

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"


@dataclass
class Config:
    input_path: Path = DATA_DIR / "reddit_fashion_data_unique.json"
    output_path: Path = DATA_DIR / "fashion_rules_extracted.json"
    # Using Mistral-7B-Instruct with MLX for fast inference on Apple Silicon
    model_name: str = "mlx-community/Mistral-7B-Instruct-v0.2-4bit"
    max_posts: Optional[int] = None  # Set to None to process all posts
    batch_size: int = 50  # Progress update frequency
    max_tokens: int = 512
    temperature: float = 0.3  # Lower for more consistent outputs


SYSTEM_PROMPT = """You are a fashion expert analyzing Reddit posts from fashion communities.

Your task is to extract specific fashion rules, advice, or guidelines mentioned in the post.

For each post, you should:
1. Identify if the post mentions any specific fashion rules, guidelines, or advice
2. Extract those rules in a clear, concise format
3. Indicate if NO fashion rules are being discussed (e.g., just a question, discussion, or off-topic)

Return your response as a JSON object with this EXACT structure:
{
  "has_fashion_rule": true,
  "rules": [
    "Rule 1: Clear statement of the fashion rule",
    "Rule 2: Another fashion rule if multiple are mentioned"
  ],
  "category": "fit",
  "confidence": "high"
}

Categories: fit, color, style, formality, accessories, general, none
Confidence levels: high, medium, low

Examples:
Input: "Never button the bottom button of a suit jacket"
Output: {"has_fashion_rule": true, "rules": ["Never button the bottom button of a suit jacket"], "category": "formality", "confidence": "high"}

Input: "Black shoes don't go with brown belts"
Output: {"has_fashion_rule": true, "rules": ["Black shoes don't go with brown belts"], "category": "color", "confidence": "high"}

Input: "Where can I buy cheap jeans?"
Output: {"has_fashion_rule": false, "rules": [], "category": "none", "confidence": "high"}

Return ONLY valid JSON, no other text."""


def ensure_mlx_available():
    """Check if mlx_lm is installed."""
    if load is None or generate is None:
        raise RuntimeError(
            "Missing mlx_lm package. Install it with: pip install mlx-lm"
        )


def load_posts(path: Path) -> List[dict]:
    """Load all posts from JSON file."""
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    posts = []
    for category, items in data.items():
        if isinstance(items, list):
            for post in items:
                if isinstance(post, dict):
                    post["source_category"] = category
                    posts.append(post)

    return posts


def get_top_comment(post: dict) -> str:
    """Extract the body of the highest-scoring comment."""
    comments = post.get("comments", [])
    if not comments:
        return ""

    top = max(comments, key=lambda c: c.get("score", 0))
    return top.get("body", "").strip()


def create_extraction_prompt(post: dict) -> str:
    """Create a prompt for the model to extract fashion rules from a post."""
    title = post.get("title", "").strip()
    selftext = post.get("selftext", "").strip()
    top_comment = get_top_comment(post)

    # Truncate to avoid token limits
    if selftext and len(selftext) > 500:
        selftext = selftext[:500] + "..."
    if top_comment and len(top_comment) > 300:
        top_comment = top_comment[:300] + "..."

    parts = [f"Title: {title}"]
    if selftext:
        parts.append(f"Post Content: {selftext}")
    if top_comment:
        parts.append(f"Top Comment: {top_comment}")

    content = "\n\n".join(parts)

    # Format for Mistral instruction format
    return f"""<s>[INST] {SYSTEM_PROMPT}

Analyze this Reddit fashion post and extract any fashion rules or advice:

{content}

Return only valid JSON. [/INST]"""


def extract_json_from_response(text: str) -> Optional[dict]:
    """Extract JSON object from model response, handling various formats."""
    # Remove common prefixes/suffixes
    text = text.strip()

    # Remove trailing commas before ] or } (common LLM mistake)
    text = re.sub(r',\s*([}\]])', r'\1', text)

    # Try to find JSON object in the text
    json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
    if json_match:
        cleaned = json_match.group()
        # Remove trailing commas again after extraction
        cleaned = re.sub(r',\s*([}\]])', r'\1', cleaned)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

    # Try parsing the whole text with comma fixes
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    return None


def extract_rule_from_post(model, tokenizer, post: dict, config: Config) -> dict:
    """Use the model to extract fashion rules from a single post."""
    prompt = create_extraction_prompt(post)

    try:
        # Generate response using MLX (temperature not supported, uses default sampling)
        response_text = generate(
            model,
            tokenizer,
            prompt=prompt,
            max_tokens=config.max_tokens,
            verbose=False,
        )

        # Extract JSON from response
        result = extract_json_from_response(response_text)

        if result is None:
            return {
                "post_id": post.get("post_id", ""),
                "title": post.get("title", ""),
                "source_category": post.get("source_category", ""),
                "url": post.get("url", ""),
                "extraction": None,
                "success": False,
                "error": f"Failed to parse JSON from response: {response_text[:200]}",
                "raw_response": response_text[:300],
            }

        # Validate required fields
        if "has_fashion_rule" not in result:
            result["has_fashion_rule"] = False
        if "rules" not in result:
            result["rules"] = []
        if "category" not in result:
            result["category"] = "none"
        if "confidence" not in result:
            result["confidence"] = "low"

        return {
            "post_id": post.get("post_id", ""),
            "title": post.get("title", ""),
            "source_category": post.get("source_category", ""),
            "url": post.get("url", ""),
            "extraction": result,
            "success": True,
        }

    except Exception as e:
        return {
            "post_id": post.get("post_id", ""),
            "title": post.get("title", ""),
            "source_category": post.get("source_category", ""),
            "url": post.get("url", ""),
            "extraction": None,
            "success": False,
            "error": str(e),
        }


def run_full_extraction(model, tokenizer, posts: List[dict], config: Config) -> List[dict]:
    """Run extraction on all posts with progress updates."""
    print(f"\n{'='*80}")
    print("RUNNING FULL EXTRACTION")
    print(f"{'='*80}\n")

    total = len(posts)
    results = []

    for i, post in enumerate(posts, 1):
        if i % config.batch_size == 1 or i == total:
            print(f"Processing post {i}/{total} ({i/total*100:.1f}%)...")

        result = extract_rule_from_post(model, tokenizer, post, config)
        results.append(result)

        # Stats every 100 posts
        if i % 100 == 0:
            successful = sum(1 for r in results if r["success"])
            with_rules = sum(1 for r in results if r["success"] and r["extraction"].get("has_fashion_rule"))
            print(f"  Stats: {successful}/{i} successful ({successful/i*100:.1f}%), {with_rules} with rules")

    return results


def save_results(results: List[dict], config: Config):
    """Save extraction results to JSON file."""
    # Calculate statistics
    total = len(results)
    successful = sum(1 for r in results if r["success"])
    has_rules = sum(1 for r in results if r["success"] and r["extraction"].get("has_fashion_rule"))

    # Count by category
    category_counts = {}
    confidence_counts = {}
    for r in results:
        if r["success"] and r["extraction"].get("has_fashion_rule"):
            cat = r["extraction"].get("category", "unknown")
            category_counts[cat] = category_counts.get(cat, 0) + 1

            conf = r["extraction"].get("confidence", "unknown")
            confidence_counts[conf] = confidence_counts.get(conf, 0) + 1

    output = {
        "metadata": {
            "model_name": config.model_name,
            "total_posts": total,
            "successful_extractions": successful,
            "failed_extractions": total - successful,
            "posts_with_rules": has_rules,
            "posts_without_rules": successful - has_rules,
            "category_distribution": category_counts,
            "confidence_distribution": confidence_counts,
        },
        "results": results,
    }

    with config.output_path.open("w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"\n{'='*80}")
    print(f"Results saved to {config.output_path}")
    print(f"\nFinal Statistics:")
    print(f"  Total posts processed: {total}")
    print(f"  Successful extractions: {successful} ({successful/total*100:.1f}%)")
    print(f"  Posts with fashion rules: {has_rules}")
    print(f"  Posts without rules: {successful - has_rules}")
    print(f"\nCategory Distribution:")
    for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {cat}: {count}")
    print(f"\nConfidence Distribution:")
    for conf, count in sorted(confidence_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {conf}: {count}")
    print(f"{'='*80}\n")


def main():
    """Main execution function."""
    ensure_mlx_available()

    config = Config()

    # Load posts
    print(f"Loading posts from {config.input_path}...")
    posts = load_posts(config.input_path)
    print(f"Loaded {len(posts)} posts")

    # Limit posts if specified
    if config.max_posts:
        posts = posts[:config.max_posts]
        print(f"Limited to {len(posts)} posts for processing")

    # Load model with MLX
    print(f"\nLoading model: {config.model_name}")
    print("This will be fast with MLX on Apple Silicon...")

    model, tokenizer = load(config.model_name)

    print("Model loaded successfully!\n")
    print(f"Processing {len(posts)} posts...\n")

    # Run full extraction
    results = run_full_extraction(model, tokenizer, posts, config)

    # Save results
    save_results(results, config)

    print("\nDone!")


if __name__ == "__main__":
    main()
