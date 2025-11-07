#!/usr/bin/env python3
"""
Deterministic article quality validation.
Ensures scraped content is complete and contains substantial fashion advice.
"""

import sqlite3
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass
import hashlib


@dataclass
class ArticleQualityMetrics:
    """Metrics for evaluating article quality."""
    url: str
    source: str
    title: str

    # Size metrics
    word_count: int
    char_count: int
    paragraph_count: int
    sentence_count: int

    # Content quality indicators
    has_fashion_terms: bool
    fashion_term_count: int
    has_actionable_advice: bool
    has_product_mentions: bool
    has_style_descriptions: bool

    # Completeness indicators
    has_introduction: bool
    has_conclusion: bool
    has_lists: bool
    has_headers: bool

    # Data quality
    truncated_likelihood: float  # 0-1 score
    quality_score: float  # 0-100 overall score

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'url': self.url,
            'source': self.source,
            'title': self.title,
            'word_count': self.word_count,
            'char_count': self.char_count,
            'paragraph_count': self.paragraph_count,
            'sentence_count': self.sentence_count,
            'has_fashion_terms': self.has_fashion_terms,
            'fashion_term_count': self.fashion_term_count,
            'has_actionable_advice': self.has_actionable_advice,
            'has_product_mentions': self.has_product_mentions,
            'has_style_descriptions': self.has_style_descriptions,
            'has_introduction': self.has_introduction,
            'has_conclusion': self.has_conclusion,
            'has_lists': self.has_lists,
            'has_headers': self.has_headers,
            'truncated_likelihood': round(self.truncated_likelihood, 2),
            'quality_score': round(self.quality_score, 1)
        }


class ArticleQualityValidator:
    """Validates article quality with deterministic metrics."""

    # Fashion-related terms to check for (deterministic set)
    FASHION_TERMS = {
        # Clothing items
        'suit', 'jacket', 'blazer', 'pants', 'trousers', 'shirt', 'tie',
        'shoes', 'boots', 'sneakers', 'loafers', 'denim', 'jeans', 'chinos',
        'sweater', 'cardigan', 'coat', 'overcoat', 'dress', 'skirt',

        # Style concepts
        'style', 'fashion', 'outfit', 'wardrobe', 'fit', 'tailoring',
        'casual', 'formal', 'preppy', 'classic', 'modern', 'vintage',
        'streetwear', 'minimalist', 'elegant', 'sophisticated',

        # Colors and patterns
        'navy', 'gray', 'grey', 'black', 'brown', 'khaki', 'olive',
        'stripe', 'plaid', 'check', 'pattern', 'solid', 'herringbone',

        # Materials and fabrics
        'cotton', 'wool', 'linen', 'silk', 'leather', 'suede', 'denim',
        'tweed', 'flannel', 'chambray', 'oxford', 'poplin', 'canvas',

        # Fit and construction
        'slim', 'regular', 'relaxed', 'tapered', 'bespoke', 'tailored',
        'custom', 'off-the-rack', 'made-to-measure', 'selvedge', 'raw',

        # Style advice terms
        'wear', 'style', 'pair', 'match', 'coordinate', 'accessorize',
        'layer', 'combine', 'dress', 'outfit', 'look'
    }

    # Actionable advice patterns (deterministic)
    ADVICE_PATTERNS = [
        r'\bhow to\b',
        r'\bshould\b',
        r'\bcan\b',
        r'\bwear\b.*\bwith\b',
        r'\bpair\b.*\bwith\b',
        r'\btry\b',
        r'\bconsider\b',
        r'\bavoid\b',
        r'\bchoose\b',
        r'\bopt for\b',
        r'\bmake sure\b',
        r'\bensure\b',
        r'\balways\b',
        r'\bnever\b',
        r'\brule\b',
        r'\btip\b',
        r'\bguide\b',
        r'\bessential\b'
    ]

    def __init__(self, db_path: Path):
        """Initialize validator with database path."""
        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row

    def analyze_article(self, article_row: sqlite3.Row) -> ArticleQualityMetrics:
        """
        Analyze a single article and return quality metrics.
        Deterministic - same input always produces same output.
        """
        body = article_row['body'] or ""
        title = article_row['title'] or "Untitled"
        url = article_row['url'] or ""
        source = article_row['source'] or ""

        # Basic counts
        word_count = len(body.split())
        char_count = len(body)
        paragraph_count = len([p for p in body.split('\n\n') if p.strip()])
        sentence_count = len([s for s in re.split(r'[.!?]+', body) if s.strip()])

        # Fashion term analysis
        body_lower = body.lower()
        fashion_term_count = sum(1 for term in self.FASHION_TERMS if term in body_lower)
        has_fashion_terms = fashion_term_count >= 5

        # Actionable advice detection
        advice_matches = sum(1 for pattern in self.ADVICE_PATTERNS
                           if re.search(pattern, body_lower))
        has_actionable_advice = advice_matches >= 3

        # Product/brand mentions (brands, specific items)
        has_product_mentions = bool(re.search(r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b', body))

        # Style descriptions (adjective + noun patterns)
        style_patterns = [
            r'\b(slim|regular|relaxed|tapered|fitted)\s+(fit|cut)\b',
            r'\b(casual|formal|smart|business)\s+(wear|attire|dress|style)\b',
            r'\b(navy|black|brown|gray|grey)\s+(suit|jacket|pants|shoes)\b'
        ]
        has_style_descriptions = any(re.search(p, body_lower) for p in style_patterns)

        # Structure indicators
        has_introduction = self._has_introduction(body)
        has_conclusion = self._has_conclusion(body)
        has_lists = bool(re.search(r'^\s*[\d\-\*•]+\s+', body, re.MULTILINE))
        has_headers = bool(re.search(r'^[A-Z][^\n]{5,60}$', body, re.MULTILINE))

        # Truncation detection
        truncated_likelihood = self._calculate_truncation_likelihood(body)

        # Overall quality score
        quality_score = self._calculate_quality_score(
            word_count=word_count,
            paragraph_count=paragraph_count,
            fashion_term_count=fashion_term_count,
            has_actionable_advice=has_actionable_advice,
            has_style_descriptions=has_style_descriptions,
            has_lists=has_lists,
            truncated_likelihood=truncated_likelihood
        )

        return ArticleQualityMetrics(
            url=url,
            source=source,
            title=title,
            word_count=word_count,
            char_count=char_count,
            paragraph_count=paragraph_count,
            sentence_count=sentence_count,
            has_fashion_terms=has_fashion_terms,
            fashion_term_count=fashion_term_count,
            has_actionable_advice=has_actionable_advice,
            has_product_mentions=has_product_mentions,
            has_style_descriptions=has_style_descriptions,
            has_introduction=has_introduction,
            has_conclusion=has_conclusion,
            has_lists=has_lists,
            has_headers=has_headers,
            truncated_likelihood=truncated_likelihood,
            quality_score=quality_score
        )

    def _has_introduction(self, body: str) -> bool:
        """Check if article has an introduction paragraph."""
        if len(body) < 200:
            return False
        first_para = body[:500].strip()
        # Check for intro patterns
        intro_patterns = [
            r'\bIn this\b',
            r'\bThis (article|guide|post)\b',
            r'\bWhen it comes to\b',
            r'\bIf you\'?re\b',
            r'\bLet\'?s\b'
        ]
        return any(re.search(p, first_para, re.IGNORECASE) for p in intro_patterns)

    def _has_conclusion(self, body: str) -> bool:
        """Check if article has a conclusion."""
        if len(body) < 500:
            return False
        last_para = body[-500:].strip()
        conclusion_patterns = [
            r'\bIn conclusion\b',
            r'\bTo sum up\b',
            r'\bFinally\b',
            r'\bOverall\b',
            r'\bRemember\b',
            r'\bNow you\b'
        ]
        return any(re.search(p, last_para, re.IGNORECASE) for p in conclusion_patterns)

    def _calculate_truncation_likelihood(self, body: str) -> float:
        """
        Calculate likelihood that article is truncated (0-1).
        Returns 0 for complete, 1 for likely truncated.
        """
        if len(body) < 300:
            return 0.9  # Very short = likely truncated

        score = 0.0

        # Check for abrupt ending (no punctuation in last 50 chars)
        last_chars = body[-50:].strip()
        if last_chars and last_chars[-1] not in '.!?"':
            score += 0.3

        # Check for incomplete sentence at end
        if body and not re.search(r'[.!?]\s*$', body.strip()):
            score += 0.2

        # Check for "Continue reading" or similar truncation markers
        truncation_markers = [
            'continue reading',
            'read more',
            'click here',
            '[...]',
            '...',
            'to be continued'
        ]
        if any(marker in body[-200:].lower() for marker in truncation_markers):
            score += 0.3

        return min(score, 1.0)

    def _calculate_quality_score(self, word_count: int, paragraph_count: int,
                                fashion_term_count: int, has_actionable_advice: bool,
                                has_style_descriptions: bool, has_lists: bool,
                                truncated_likelihood: float) -> float:
        """
        Calculate overall quality score (0-100).
        Deterministic scoring system.
        """
        score = 0.0

        # Length score (0-30 points)
        if word_count >= 1000:
            score += 30
        elif word_count >= 500:
            score += 20
        elif word_count >= 300:
            score += 10

        # Structure score (0-20 points)
        if paragraph_count >= 5:
            score += 10
        if has_lists:
            score += 10

        # Fashion content score (0-30 points)
        fashion_score = min(fashion_term_count, 30)
        score += fashion_score

        # Advice quality (0-10 points)
        if has_actionable_advice:
            score += 10

        # Style descriptions (0-10 points)
        if has_style_descriptions:
            score += 10

        # Penalize for truncation
        score *= (1.0 - truncated_likelihood * 0.5)

        return min(score, 100.0)

    def validate_all_articles(self) -> Tuple[List[ArticleQualityMetrics], Dict]:
        """
        Validate all articles in database.
        Returns metrics for each article and summary statistics.
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT content_id, source, title, url, body, scraped_at
            FROM scraped_content
            ORDER BY source, content_id
        """)

        articles = cursor.fetchall()
        metrics_list = []

        for article in articles:
            metrics = self.analyze_article(article)
            metrics_list.append(metrics)

        # Calculate summary statistics (deterministic)
        total = len(metrics_list)
        high_quality = sum(1 for m in metrics_list if m.quality_score >= 70)
        medium_quality = sum(1 for m in metrics_list if 40 <= m.quality_score < 70)
        low_quality = sum(1 for m in metrics_list if m.quality_score < 40)

        avg_word_count = sum(m.word_count for m in metrics_list) / total if total else 0
        avg_quality_score = sum(m.quality_score for m in metrics_list) / total if total else 0

        likely_truncated = sum(1 for m in metrics_list if m.truncated_likelihood > 0.5)
        complete_articles = sum(1 for m in metrics_list if m.truncated_likelihood < 0.2)

        summary = {
            'total_articles': total,
            'quality_distribution': {
                'high_quality': high_quality,
                'high_quality_pct': round(high_quality / total * 100, 1) if total else 0,
                'medium_quality': medium_quality,
                'medium_quality_pct': round(medium_quality / total * 100, 1) if total else 0,
                'low_quality': low_quality,
                'low_quality_pct': round(low_quality / total * 100, 1) if total else 0
            },
            'average_word_count': int(avg_word_count),
            'average_quality_score': round(avg_quality_score, 1),
            'completeness': {
                'likely_truncated': likely_truncated,
                'likely_truncated_pct': round(likely_truncated / total * 100, 1) if total else 0,
                'complete_articles': complete_articles,
                'complete_articles_pct': round(complete_articles / total * 100, 1) if total else 0
            }
        }

        return metrics_list, summary

    def export_sample_articles(self, output_dir: Path, sample_size: int = 10):
        """
        Export sample of high-quality articles for manual verification.
        Deterministically selects diverse samples.
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT content_id, source, title, url, body, scraped_at
            FROM scraped_content
            ORDER BY LENGTH(body) DESC
            LIMIT ?
        """, (sample_size,))

        articles = cursor.fetchall()
        output_dir.mkdir(parents=True, exist_ok=True)

        samples = []
        for i, article in enumerate(articles, 1):
            # Create deterministic hash for filename
            content_hash = hashlib.md5(article['url'].encode()).hexdigest()[:8]
            filename = f"sample_{i:02d}_{content_hash}.txt"

            filepath = output_dir / filename
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"URL: {article['url']}\n")
                f.write(f"Source: {article['source']}\n")
                f.write(f"Title: {article['title']}\n")
                f.write(f"Scraped: {article['scraped_at']}\n")
                f.write(f"Length: {len(article['body'])} chars\n")
                f.write("=" * 80 + "\n\n")
                f.write(article['body'])

            samples.append({
                'filename': filename,
                'url': article['url'],
                'source': article['source'],
                'title': article['title'],
                'word_count': len(article['body'].split()),
                'char_count': len(article['body'])
            })

        return samples

    def close(self):
        """Close database connection."""
        self.conn.close()


def main():
    """Main validation execution."""
    base_dir = Path(__file__).parent.parent
    db_path = base_dir / "data" / "independent_content.db"
    output_dir = base_dir / "validation"

    print("=" * 80)
    print("ARTICLE QUALITY VALIDATION")
    print("Deterministic analysis of scraped fashion content")
    print("=" * 80)
    print()

    validator = ArticleQualityValidator(db_path)

    # Validate all articles
    print("Analyzing all articles...")
    metrics_list, summary = validator.validate_all_articles()

    # Print summary
    print(f"\nDatabase: {db_path}")
    print(f"Total articles analyzed: {summary['total_articles']}")
    print()

    print("QUALITY DISTRIBUTION:")
    print(f"  High quality (70-100):   {summary['quality_distribution']['high_quality']:3d} ({summary['quality_distribution']['high_quality_pct']:5.1f}%)")
    print(f"  Medium quality (40-69):  {summary['quality_distribution']['medium_quality']:3d} ({summary['quality_distribution']['medium_quality_pct']:5.1f}%)")
    print(f"  Low quality (0-39):      {summary['quality_distribution']['low_quality']:3d} ({summary['quality_distribution']['low_quality_pct']:5.1f}%)")
    print()

    print("CONTENT METRICS:")
    print(f"  Average word count: {summary['average_word_count']:,}")
    print(f"  Average quality score: {summary['average_quality_score']:.1f}/100")
    print()

    print("COMPLETENESS:")
    print(f"  Complete articles: {summary['completeness']['complete_articles']:3d} ({summary['completeness']['complete_articles_pct']:5.1f}%)")
    print(f"  Likely truncated:  {summary['completeness']['likely_truncated']:3d} ({summary['completeness']['likely_truncated_pct']:5.1f}%)")
    print()

    # Export detailed metrics
    metrics_file = output_dir / "article_quality_metrics.json"
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(metrics_file, 'w', encoding='utf-8') as f:
        json.dump({
            'summary': summary,
            'articles': [m.to_dict() for m in metrics_list]
        }, f, indent=2)

    print(f"✓ Detailed metrics saved to: {metrics_file}")

    # Export sample articles
    print("\nExporting sample articles for manual verification...")
    samples = validator.export_sample_articles(output_dir / "samples", sample_size=10)

    samples_index = output_dir / "samples" / "index.json"
    with open(samples_index, 'w', encoding='utf-8') as f:
        json.dump(samples, f, indent=2)

    print(f"✓ Exported {len(samples)} sample articles to: {output_dir / 'samples'}")
    print(f"✓ Sample index: {samples_index}")

    # Show top 10 highest quality articles
    print("\nTOP 10 HIGHEST QUALITY ARTICLES:")
    print("-" * 80)
    top_articles = sorted(metrics_list, key=lambda m: m.quality_score, reverse=True)[:10]
    for i, metrics in enumerate(top_articles, 1):
        print(f"{i:2d}. [{metrics.quality_score:5.1f}] {metrics.title[:60]}")
        print(f"    {metrics.source} | {metrics.word_count:,} words")
        print()

    validator.close()
    print("✓ Validation complete!")


if __name__ == "__main__":
    main()
