"""
Rules Extractor V2 - Enhanced with MinHash Deduplication

This module is the SINGLE SOURCE OF TRUTH for extracting fashion rules from articles.

CRITICAL FIXES:
1. Integrates advanced MinHash LSH deduplication (replaces simple in-memory set)
2. Adds linguistic feature extraction for ML training
3. Improves sentence tokenization
4. Adds confidence scoring based on multiple factors
5. Comprehensive function-level documentation

Author: Refactored 2025-11-06
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Set, Optional
from collections import defaultdict
import logging

# Import our advanced deduplicator
from deduplicator import RuleDeduplicator

logger = logging.getLogger(__name__)


def split_into_sentences(text: str) -> List[str]:
    """
    Split text into sentences using improved regex-based tokenization.

    This function handles common edge cases better than simple regex splitting:
    - Abbreviations (Mr., Dr., U.S.A.)
    - Decimal numbers (3.14)
    - Ellipsis (...)
    - Quotes with punctuation

    For production use, consider using nltk.sent_tokenize() or spaCy for
    more robust sentence boundary detection.

    Args:
        text: Input text to split

    Returns:
        List of sentence strings

    Example:
        >>> split_into_sentences("Dr. Smith said, 'Never!' I agreed.")
        ["Dr. Smith said, 'Never!'", "I agreed."]
    """
    if not text or not text.strip():
        return []

    # Improved regex that handles more edge cases
    # Splits on sentence-ending punctuation followed by space and capital letter
    # Uses negative lookbehind to avoid splitting on abbreviations
    pattern = r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s+(?=[A-Z])'

    sentences = re.split(pattern, text)

    # Clean and filter
    sentences = [s.strip() for s in sentences if s.strip()]

    return sentences


class EnhancedRulesExtractor:
    """
    Extracts fashion rules from articles using keyword matching + linguistic features.

    This is the ONLY rule extractor in the pipeline. It combines:
    1. Keyword-based filtering (high recall)
    2. Linguistic feature extraction (for ML training)
    3. Advanced MinHash LSH deduplication
    4. Multi-factor confidence scoring

    The keyword approach is intentionally kept as a *filter* (to maximize recall),
    while additional features enable training a more sophisticated ML classifier.
    """

    # Prescriptive language indicators
    # These words often appear in advice/rules
    RULE_KEYWORDS = [
        "should", "must", "always", "never", "avoid", "ensure",
        "make sure", "remember", "rule", "principle", "guideline",
        "recommend", "don't", "do not", "appropriate", "suitable",
        "proper", "ideal", "best", "typically", "usually", "prefer",
        "opt for", "choose", "consider", "important"
    ]

    # Fashion domain vocabulary
    FASHION_KEYWORDS = [
        "wear", "fit", "color", "match", "pair", "dress", "style", "fashion",
        "shirt", "pants", "jacket", "suit", "shoes", "tie", "belt", "watch",
        "formal", "casual", "business", "wardrobe", "outfit", "garment",
        "trouser", "blazer", "sportcoat", "oxford", "loafer", "fabric",
        "tailoring", "accessories", "pattern", "texture", "silhouette"
    ]

    # Noise indicators (promotional/non-content text)
    NOISE_INDICATORS = [
        "subscribe", "newsletter", "click here", "read more", "buy now",
        "shop now", "related posts", "follow us", "advertisement",
        "sponsored", "affiliate", "disclosure", "comment below"
    ]

    def __init__(
        self,
        input_directory: str = "data/raw",
        output_directory: str = "data/processed",
        min_rule_character_length: int = 30,
        max_rule_character_length: int = 500,
        use_advanced_deduplication: bool = True,
        dedup_similarity_threshold: float = 0.85,
    ):
        """
        Initialize the enhanced rules extractor.

        Args:
            input_directory: Directory with raw article JSONL files
            output_directory: Directory for processed rules output
            min_rule_character_length: Minimum length for a valid rule
            max_rule_character_length: Maximum length for a valid rule
            use_advanced_deduplication: Use MinHash LSH (True) or simple set (False)
            dedup_similarity_threshold: Threshold for fuzzy deduplication (0-1)
        """
        self.input_directory = Path(input_directory)
        self.output_directory = Path(output_directory)
        self.output_directory.mkdir(parents=True, exist_ok=True)

        self.min_rule_character_length = min_rule_character_length
        self.max_rule_character_length = max_rule_character_length
        self.use_advanced_deduplication = use_advanced_deduplication

        # Output files
        self.rules_output_filepath = self.output_directory / "rules.jsonl"
        self.articles_output_filepath = self.output_directory / "articles.jsonl"

        # Deduplication setup
        if use_advanced_deduplication:
            self.deduplicator = RuleDeduplicator(
                fuzzy_similarity_threshold=int(dedup_similarity_threshold * 100)
            )
            logger.info("Using advanced MinHash LSH deduplication")
        else:
            self.deduplicator = None
            self.seen_rule_signatures: Set[str] = set()
            logger.info("Using simple deduplication")

        # Article tracking
        self.seen_article_urls: Set[str] = set()

        # Statistics
        self.extraction_stats = {
            "articles_processed": 0,
            "rules_extracted": 0,
            "rules_deduplicated": 0,
            "articles_deduplicated": 0,
        }

        self._load_existing_data()

        logger.info("EnhancedRulesExtractor initialized")
        logger.info(f"  Input: {self.input_directory}")
        logger.info(f"  Output: {self.output_directory}")
        logger.info(f"  Advanced deduplication: {use_advanced_deduplication}")

    def _load_existing_data(self):
        """
        Load previously extracted rules and articles to avoid reprocessing.

        This makes the extraction process idempotent - safe to run multiple times
        without creating duplicates.
        """
        # Load existing rules
        if self.rules_output_filepath.exists():
            with self.rules_output_filepath.open("r") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        rule = json.loads(line)
                        rule_text = rule.get("rule_text", "")

                        if self.use_advanced_deduplication and self.deduplicator:
                            self.deduplicator.add_rule_to_index(rule_text)
                        else:
                            signature = self._create_simple_signature(rule_text)
                            self.seen_rule_signatures.add(signature)
                    except json.JSONDecodeError:
                        continue

        # Load existing articles
        if self.articles_output_filepath.exists():
            with self.articles_output_filepath.open("r") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        article = json.loads(line)
                        url = article.get("url", "")
                        if url:
                            self.seen_article_urls.add(self._normalize_url(url))
                    except json.JSONDecodeError:
                        continue

        logger.info(f"Loaded existing data:")
        if self.use_advanced_deduplication and self.deduplicator:
            stats = self.deduplicator.get_deduplication_stats()
            logger.info(f"  Existing rules: {stats['total_rules']}")
        else:
            logger.info(f"  Existing rules: {len(self.seen_rule_signatures)}")
        logger.info(f"  Existing articles: {len(self.seen_article_urls)}")

    def _normalize_url(self, url: str) -> str:
        """
        Normalize URL for consistent comparison.

        Args:
            url: URL to normalize

        Returns:
            Normalized URL string
        """
        # Simple normalization (for more robust version, use url_utils.normalize_url)
        return url.lower().rstrip("/").split("?")[0].split("#")[0]

    def _create_simple_signature(self, text: str) -> str:
        """
        Create a simple normalized signature for text deduplication.

        This is used only when advanced deduplication is disabled.

        Args:
            text: Text to create signature from

        Returns:
            Normalized signature string
        """
        if not text:
            return ""

        # Normalize: lowercase, remove punctuation, collapse whitespace
        normalized = text.lower()
        normalized = re.sub(r"[^\w\s]", " ", normalized)
        normalized = " ".join(normalized.split())

        return normalized.strip()

    def extract_rules_from_article(self, article_data: Dict) -> List[Dict]:
        """
        Extract fashion rules from a single article.

        This is the main extraction method. It processes both structured content
        (lists) and unstructured content (paragraphs), applies filtering logic,
        and returns a list of extracted rules with rich metadata.

        Args:
            article_data: Article dictionary with 'text', 'lists', 'paragraphs', etc.

        Returns:
            List of rule dictionaries with metadata and features

        Processing Pipeline:
            1. Extract from structured lists (higher confidence)
            2. Extract from paragraphs/sentences (lower confidence)
            3. Apply length filters
            4. Apply keyword filters
            5. Apply noise filters
            6. Check for duplicates
            7. Extract linguistic features
            8. Calculate confidence score
        """
        extracted_rules = []

        # Process lists (high-confidence source)
        for list_item in article_data.get("lists", []):
            if isinstance(list_item, dict):
                items = list_item.get("items", [])
            elif isinstance(list_item, list):
                items = list_item
            else:
                items = [str(list_item)]

            for item in items:
                if not isinstance(item, str):
                    continue

                rule = self._extract_rule_from_text(
                    text=item,
                    article=article_data,
                    source_type="list"
                )

                if rule:
                    extracted_rules.append(rule)

        # Process paragraphs
        for paragraph in article_data.get("paragraphs", []):
            # Use improved sentence tokenization
            sentences = split_into_sentences(paragraph)

            for sentence in sentences:
                sentence = sentence.strip()

                rule = self._extract_rule_from_text(
                    text=sentence,
                    article=article_data,
                    source_type="paragraph"
                )

                if rule:
                    extracted_rules.append(rule)

        return extracted_rules

    def _extract_rule_from_text(
        self,
        text: str,
        article: Dict,
        source_type: str = "paragraph"
    ) -> Optional[Dict]:
        """
        Determine if a text snippet is a fashion rule and extract features.

        This function implements the core extraction logic using multiple filters
        and feature extractors. It's designed to have HIGH RECALL (catch most rules)
        at the cost of some precision (some false positives).

        The extracted features enable training an ML classifier for better precision.

        Args:
            text: Text snippet to evaluate
            article: Parent article data
            source_type: "list" or "paragraph" (affects confidence)

        Returns:
            Rule dictionary with metadata and features, or None if not a rule

        Filtering Pipeline:
            1. Length check (quality filter)
            2. Rule keyword check (recall filter)
            3. Fashion keyword check (domain filter)
            4. Noise check (precision filter)
            5. Deduplication check
            6. Feature extraction
            7. Confidence scoring
        """
        # --- Filter 1: Length ---
        if len(text) < self.min_rule_character_length:
            return None
        if len(text) > self.max_rule_character_length:
            return None

        text_lower = text.lower()

        # --- Filter 2: Rule Keywords (RECALL optimization) ---
        rule_keywords_found = [kw for kw in self.RULE_KEYWORDS if kw in text_lower]
        has_rule_keyword = len(rule_keywords_found) > 0

        if not has_rule_keyword:
            return None

        # --- Filter 3: Fashion Keywords (DOMAIN filter) ---
        fashion_keywords_found = [kw for kw in self.FASHION_KEYWORDS if kw in text_lower]
        has_fashion_keyword = len(fashion_keywords_found) > 0

        if not has_fashion_keyword:
            return None

        # --- Filter 4: Noise Indicators (PRECISION filter) ---
        noise_found = [kw for kw in self.NOISE_INDICATORS if kw in text_lower]
        has_noise = len(noise_found) > 0

        if has_noise:
            return None

        # --- Filter 5: Deduplication ---
        if self.use_advanced_deduplication and self.deduplicator:
            is_duplicate, duplicate_of = self.deduplicator.is_rule_a_duplicate(text)
            if is_duplicate:
                self.extraction_stats["rules_deduplicated"] += 1
                return None
        else:
            signature = self._create_simple_signature(text)
            if signature in self.seen_rule_signatures:
                self.extraction_stats["rules_deduplicated"] += 1
                return None
            self.seen_rule_signatures.add(signature)

        # --- Feature Extraction ---
        features = self._extract_linguistic_features(text)

        # --- Categorization ---
        category = self._categorize_rule(text)
        garment = self._extract_garment(text)
        context = self._extract_context(text)
        rule_type = self._determine_type(text)

        # --- Confidence Scoring ---
        confidence = self._calculate_confidence(
            text=text,
            source_type=source_type,
            features=features,
            rule_keywords_count=len(rule_keywords_found),
            fashion_keywords_count=len(fashion_keywords_found)
        )

        # --- Build Rule Dictionary ---
        rule_data = {
            # Core data
            "rule_text": text.strip(),
            "rule_type": rule_type,
            "category": category,
            "garment": garment,
            "context": context,

            # Source metadata
            "source_type": source_type,
            "confidence": confidence,
            "source_url": self._normalize_url(article.get("normalized_url") or article.get("url", "")),
            "source_title": article.get("title", ""),
            "source_author": article.get("author", ""),
            "source_domain": article.get("site_domain", ""),

            # Features for ML training
            "features": features,

            # Keywords found (for debugging/analysis)
            "rule_keywords_found": rule_keywords_found,
            "fashion_keywords_found": fashion_keywords_found,

            # Basic metrics
            "rule_length": len(text),
            "word_count": len(text.split()),
        }

        return rule_data

    def _extract_linguistic_features(self, text: str) -> Dict:
        """
        Extract linguistic features from text for ML training.

        These features can be used to train a more sophisticated classifier
        that goes beyond simple keyword matching.

        Args:
            text: Text to analyze

        Returns:
            Dictionary of linguistic features

        Features Extracted:
            - Sentence structure (question, imperative, declarative)
            - Presence of modals (should, must, can)
            - Presence of negation (never, don't, avoid)
            - Verb tense indicators
            - Specificity indicators
            - Authority indicators
        """
        text_lower = text.lower()
        words = text_lower.split()

        features = {
            # Sentence type
            "is_question": text.endswith("?"),
            "is_exclamation": text.endswith("!"),
            "is_imperative": any(text_lower.startswith(v) for v in ["choose", "wear", "avoid", "ensure", "match", "pair"]),

            # Modal verbs (indicates prescription)
            "has_should": "should" in text_lower,
            "has_must": "must" in text_lower,
            "has_can": " can " in text_lower or text_lower.startswith("can "),
            "has_may": " may " in text_lower,

            # Negation (important for rule polarity)
            "has_never": "never" in text_lower,
            "has_not": " not " in text_lower or "n't" in text_lower,
            "has_avoid": "avoid" in text_lower,

            # Quantifiers (specificity indicators)
            "has_always": "always" in text_lower,
            "has_usually": "usually" in text_lower or "typically" in text_lower,
            "has_sometimes": "sometimes" in text_lower or "occasionally" in text_lower,

            # Authority indicators
            "has_rule": "rule" in text_lower,
            "has_principle": "principle" in text_lower,
            "has_guideline": "guideline" in text_lower,

            # Metrics
            "word_count": len(words),
            "char_count": len(text),
            "avg_word_length": sum(len(w) for w in words) / len(words) if words else 0,
        }

        return features

    def _categorize_rule(self, text: str) -> str:
        """
        Categorize the rule by topic using keyword matching.

        Args:
            text: Rule text

        Returns:
            Category name
        """
        text_lower = text.lower()

        category_keywords = {
            "fit": ["fit", "size", "tailor", "hem", "sleeve", "rise", "inseam"],
            "color": ["color", "hue", "tone", "shade", "match", "complement", "contrast"],
            "coordination": ["pair", "wear with", "combine", "outfit", "mix", "layer"],
            "dress_code": ["dress code", "black tie", "formal", "business casual", "smart casual"],
            "proportion": ["proportion", "balance", "silhouette", "scale"],
            "fabric": ["fabric", "material", "cotton", "wool", "linen", "silk"],
            "seasonality": ["season", "summer", "winter", "spring", "fall", "weather"],
            "footwear": ["shoe", "boot", "sneaker", "oxford", "derby", "loafer"],
            "accessories": ["tie", "belt", "watch", "pocket square", "hat", "scarf"],
            "grooming": ["groom", "hair", "beard", "shave", "fragrance"],
        }

        for category, keywords in category_keywords.items():
            if any(kw in text_lower for kw in keywords):
                return category

        return "general"

    def _extract_garment(self, text: str) -> Optional[str]:
        """
        Extract the primary garment mentioned in the rule.

        Args:
            text: Rule text

        Returns:
            Garment name or None
        """
        text_lower = text.lower()

        garment_keywords = {
            "shirt": ["shirt", "button-down", "dress shirt", "polo"],
            "pants": ["pants", "trousers", "chinos", "jeans", "slacks"],
            "jacket": ["jacket", "blazer", "sports coat", "sport coat"],
            "suit": ["suit", "two-piece", "three-piece"],
            "shoes": ["shoes", "boots", "sneakers", "oxfords", "loafers"],
            "tie": ["tie", "neckwear", "necktie", "bow tie"],
            "belt": ["belt"],
            "watch": ["watch", "timepiece"],
            "socks": ["socks", "hosiery"],
            "coat": ["coat", "overcoat", "topcoat"],
        }

        for garment, keywords in garment_keywords.items():
            if any(kw in text_lower for kw in keywords):
                return garment

        return None

    def _extract_context(self, text: str) -> Optional[str]:
        """
        Extract the wear context (formal, casual, business, etc.).

        Args:
            text: Rule text

        Returns:
            Context name or None
        """
        text_lower = text.lower()

        context_keywords = {
            "formal": ["formal", "black tie", "white tie", "tuxedo"],
            "business": ["business", "office", "professional", "work"],
            "smart_casual": ["smart casual", "business casual"],
            "casual": ["casual", "weekend", "everyday"],
        }

        for context, keywords in context_keywords.items():
            if any(kw in text_lower for kw in keywords):
                return context

        return None

    def _determine_type(self, text: str) -> str:
        """
        Determine if the rule is positive (do this) or negative (don't do this).

        Args:
            text: Rule text

        Returns:
            "positive" or "negative"
        """
        text_lower = text.lower()
        negative_keywords = ["never", "avoid", "don't", "do not", "should not", "shouldn't"]

        if any(kw in text_lower for kw in negative_keywords):
            return "negative"

        return "positive"

    def _calculate_confidence(
        self,
        text: str,
        source_type: str,
        features: Dict,
        rule_keywords_count: int,
        fashion_keywords_count: int
    ) -> float:
        """
        Calculate a confidence score for the extracted rule.

        This multi-factor scoring helps prioritize higher-quality rules.

        Args:
            text: Rule text
            source_type: "list" or "paragraph"
            features: Extracted linguistic features
            rule_keywords_count: Number of rule keywords found
            fashion_keywords_count: Number of fashion keywords found

        Returns:
            Confidence score (0.0 to 1.0)

        Scoring Factors:
            - Source type (lists are higher confidence)
            - Number of rule keywords
            - Number of fashion keywords
            - Sentence structure
            - Presence of modals
            - Specificity indicators
        """
        confidence = 0.5  # Base score

        # Source type bonus
        if source_type == "list":
            confidence += 0.2
        else:
            confidence += 0.1

        # Keyword density bonus
        if rule_keywords_count >= 2:
            confidence += 0.1
        if fashion_keywords_count >= 2:
            confidence += 0.1

        # Linguistic feature bonuses
        if features.get("has_should") or features.get("has_must"):
            confidence += 0.05

        if features.get("has_always") or features.get("has_never"):
            confidence += 0.05

        if features.get("is_imperative"):
            confidence += 0.05

        # Penalties
        if features.get("is_question"):
            confidence -= 0.2

        # Clamp to [0, 1]
        confidence = max(0.0, min(1.0, confidence))

        return round(confidence, 2)

    def process_article_file(self, filepath: Path) -> int:
        """
        Process a single article file and extract rules.

        Args:
            filepath: Path to article JSONL file

        Returns:
            Number of rules extracted from this file
        """
        rules_extracted = 0

        with filepath.open("r") as f:
            for line in f:
                if not line.strip():
                    continue

                try:
                    article_data = json.loads(line)

                    # Skip if already processed
                    url = self._normalize_url(
                        article_data.get("normalized_url") or article_data.get("url", "")
                    )
                    if url in self.seen_article_urls:
                        self.extraction_stats["articles_deduplicated"] += 1
                        continue

                    # Extract rules
                    rules = self.extract_rules_from_article(article_data)

                    # Save rules
                    if rules:
                        self._save_rules(rules)
                        rules_extracted += len(rules)

                    # Save article reference
                    self._save_article_reference(article_data)

                    # Mark as processed
                    self.seen_article_urls.add(url)
                    self.extraction_stats["articles_processed"] += 1

                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error: {e}")
                    continue
                except Exception as e:
                    logger.error(f"Error processing article: {e}")
                    continue

        return rules_extracted

    def _save_rules(self, rules: List[Dict]):
        """
        Save extracted rules to JSONL file.

        Args:
            rules: List of rule dictionaries
        """
        with self.rules_output_filepath.open("a", encoding="utf-8") as f:
            for rule in rules:
                f.write(json.dumps(rule, ensure_ascii=False) + "\n")
                self.extraction_stats["rules_extracted"] += 1

    def _save_article_reference(self, article: Dict):
        """
        Save article metadata to reference file.

        Args:
            article: Article data dictionary
        """
        reference = {
            "url": self._normalize_url(article.get("normalized_url") or article.get("url", "")),
            "title": article.get("title", ""),
            "author": article.get("author", ""),
            "publish_date": article.get("publish_date", ""),
            "word_count": article.get("word_count", 0),
            "content_type": article.get("content_type", "general"),
            "site_name": article.get("site_name", ""),
            "site_domain": article.get("site_domain", ""),
        }

        with self.articles_output_filepath.open("a", encoding="utf-8") as f:
            f.write(json.dumps(reference, ensure_ascii=False) + "\n")

    def process_all_files(self) -> Dict:
        """
        Process all article files in the input directory.

        Returns:
            Statistics dictionary
        """
        logger.info("Processing article files...")

        article_files = list(self.input_directory.glob("*_articles.jsonl"))

        if not article_files:
            logger.warning(f"No article files found in {self.input_directory}")
            return self.extraction_stats

        logger.info(f"Found {len(article_files)} article files")

        for filepath in article_files:
            logger.info(f"Processing {filepath.name}...")
            rules_count = self.process_article_file(filepath)
            logger.info(f"  Extracted {rules_count} rules")

        logger.info("\n" + "=" * 60)
        logger.info("EXTRACTION COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Articles processed: {self.extraction_stats['articles_processed']}")
        logger.info(f"Articles skipped (duplicates): {self.extraction_stats['articles_deduplicated']}")
        logger.info(f"Rules extracted: {self.extraction_stats['rules_extracted']}")
        logger.info(f"Rules deduplicated: {self.extraction_stats['rules_deduplicated']}")
        logger.info(f"Output: {self.output_directory}")

        return self.extraction_stats


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Extract fashion rules from articles (V2)")
    parser.add_argument("--input", default="data/raw", help="Input directory")
    parser.add_argument("--output", default="data/processed", help="Output directory")
    parser.add_argument("--min-length", type=int, default=30, help="Min rule length")
    parser.add_argument("--max-length", type=int, default=500, help="Max rule length")
    parser.add_argument("--no-advanced-dedup", action="store_true", help="Disable MinHash deduplication")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    extractor = EnhancedRulesExtractor(
        input_directory=args.input,
        output_directory=args.output,
        min_rule_character_length=args.min_length,
        max_rule_character_length=args.max_length,
        use_advanced_deduplication=not args.no_advanced_dedup,
    )

    stats = extractor.process_all_files()

    print("\n" + "=" * 80)
    print("SUCCESS: Extraction complete!")
    print("=" * 80)
    print(f"   Rules extracted: {stats['rules_extracted']}")
    print(f"   Articles processed: {stats['articles_processed']}")
    print(f"   Output: {extractor.output_directory}")
