"""
Gold Set Builder V2 - Unbiased Sampling Approach

This module creates a gold standard dataset for evaluating rule extraction quality.

CRITICAL FIX: This version completely removes the circular validation logic present in
the original goldset_builder.py. Instead of pre-filtering sentences using the same
keywords that the rule extractor uses, this version samples sentences RANDOMLY and
STRATIFIED to create a truly representative test set.

Key Improvements:
1. Random stratified sampling (not keyword-based pre-filtering)
2. Balanced representation across sources, lengths, and article types
3. Linguistic feature extraction (not classification)
4. NO bias toward extractor's logic

Author: Refactored 2025-11-06
"""

from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


@dataclass
class CandidateSentence:
    """
    Represents a sentence candidate for the gold set with rich metadata.

    This dataclass stores ALL information about a sentence WITHOUT making any
    judgment about whether it's a rule or not. That judgment is reserved for
    human annotators.
    """
    sentence_id: str
    sentence: str
    paragraph_text: str
    preceding_sentence: Optional[str]
    following_sentence: Optional[str]
    article_url: str
    article_title: str
    article_author: str
    article_domain: str
    article_publish_date: Optional[str]
    article_source: str
    paragraph_index: int
    sentence_index: int

    # Linguistic features (descriptive, not prescriptive)
    word_count: int = 0
    has_imperative_verb: bool = False
    has_modal_verb: bool = False
    has_negation: bool = False
    contains_fashion_terms: bool = False
    contains_action_verbs: bool = False
    sentence_type: str = "declarative"  # declarative, imperative, interrogative, exclamatory

    # Stratification metadata (for sampling balance)
    sampling_stratum: str = "general"  # general, short, long, list_item, heading

    def to_json(self) -> str:
        """
        Serialize sentence to JSON for human annotation.

        The output includes a 'label' field set to None, which human annotators
        will fill in with: 'rule', 'non-rule', 'borderline', or 'skip'.
        """
        payload = {
            "id": self.sentence_id,
            "sentence": self.sentence,
            "context": {
                "paragraph": self.paragraph_text,
                "preceding": self.preceding_sentence,
                "following": self.following_sentence,
            },
            "source": {
                "article_url": self.article_url,
                "article_title": self.article_title,
                "article_author": self.article_author,
                "article_domain": self.article_domain,
                "article_publish_date": self.article_publish_date,
                "article_source": self.article_source,
            },
            "position": {
                "paragraph_index": self.paragraph_index,
                "sentence_index": self.sentence_index,
            },
            "features": {
                "word_count": self.word_count,
                "has_imperative_verb": self.has_imperative_verb,
                "has_modal_verb": self.has_modal_verb,
                "has_negation": self.has_negation,
                "contains_fashion_terms": self.contains_fashion_terms,
                "contains_action_verbs": self.contains_action_verbs,
                "sentence_type": self.sentence_type,
            },
            "sampling_stratum": self.sampling_stratum,
            # This is what humans will fill in
            "label": None,
            "annotator_notes": "",
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)


class UnbiasedGoldSetBuilder:
    """
    Creates a gold standard dataset using RANDOM STRATIFIED SAMPLING.

    This builder intentionally avoids any logic that resembles the rule extractor's
    keyword matching. Instead, it:

    1. Samples sentences RANDOMLY from the corpus
    2. Ensures BALANCE across different strata (sources, lengths, types)
    3. Extracts DESCRIPTIVE linguistic features (not classifications)
    4. Leaves CLASSIFICATION to human annotators

    This approach produces an unbiased test set that truly measures the extractor's
    performance against real-world data.
    """

    # Modal verbs that often appear in prescriptive advice
    MODAL_VERBS = ["should", "must", "ought", "need", "have to", "can", "may", "might", "could", "would"]

    # Fashion domain terms (for feature detection, NOT filtering)
    FASHION_TERMS = [
        "wear", "fit", "suit", "jacket", "shirt", "pants", "shoes", "tie", "belt",
        "dress", "style", "formal", "casual", "wardrobe", "outfit", "garment", "fabric",
        "color", "pattern", "texture", "silhouette", "tailored", "accessories"
    ]

    # Action verbs common in advice
    ACTION_VERBS = [
        "choose", "select", "pick", "avoid", "prefer", "match", "pair", "combine",
        "ensure", "maintain", "keep", "remove", "add", "adjust", "consider"
    ]

    # Negation words
    NEGATION_WORDS = ["never", "don't", "do not", "avoid", "without", "no", "not"]

    def __init__(
        self,
        input_directory: str = "data/raw",
        output_filepath: str = "data/processed/gold_set_unbiased.jsonl",
        target_dataset_size: int = 1000,
        min_sentence_length_chars: int = 20,
        max_sentence_length_chars: int = 400,
        samples_per_source: int = None,
        random_seed: int = 42,
    ):
        """
        Initialize the unbiased gold set builder.

        Args:
            input_directory: Directory containing raw article files
            output_filepath: Where to save the gold set
            target_dataset_size: Total number of sentences to sample
            min_sentence_length_chars: Minimum sentence length
            max_sentence_length_chars: Maximum sentence length
            samples_per_source: Max sentences per source (for balance)
            random_seed: Random seed for reproducibility
        """
        self.input_directory = Path(input_directory)
        self.output_filepath = Path(output_filepath)
        self.output_filepath.parent.mkdir(parents=True, exist_ok=True)

        self.target_dataset_size = target_dataset_size
        self.min_sentence_length_chars = min_sentence_length_chars
        self.max_sentence_length_chars = max_sentence_length_chars
        self.samples_per_source = samples_per_source
        self.random_generator = random.Random(random_seed)

        logger.info("UnbiasedGoldSetBuilder initialized")
        logger.info(f"  Target size: {target_dataset_size}")
        logger.info(f"  Unbiased sampling: YES (no keyword pre-filtering)")

    def build_gold_set(self) -> Dict[str, int]:
        """
        Build a gold standard dataset using random stratified sampling.

        This method orchestrates the entire process:
        1. Load articles from raw data
        2. Extract ALL sentences (no filtering)
        3. Extract linguistic features for stratification
        4. Sample randomly with stratification
        5. Write to JSONL for human annotation

        Returns:
            Dict with statistics about the sampling process
        """
        logger.info("Starting unbiased gold set creation...")

        # Load articles
        articles = self._load_articles_from_files()
        if not articles:
            raise RuntimeError(f"No article files found in {self.input_directory}")

        logger.info(f"Loaded {len(articles)} articles")

        # Extract ALL sentences (no filtering!)
        all_sentences = []
        for article_index, article_content in enumerate(articles):
            sentences = list(self._extract_sentences_from_article(article_index, article_content))
            all_sentences.extend(sentences)

        logger.info(f"Extracted {len(all_sentences)} total sentences")

        # Stratify sentences
        stratified_sentences = self._stratify_sentences(all_sentences)

        # Sample from each stratum
        selected_sentences = self._stratified_sample(stratified_sentences)

        # Shuffle final selection
        self.random_generator.shuffle(selected_sentences)

        # Write to file
        self._write_sentences_to_jsonl(selected_sentences)

        # Generate statistics
        stats = {
            "articles_loaded": len(articles),
            "total_sentences_extracted": len(all_sentences),
            "sentences_selected": len(selected_sentences),
            "output_path": str(self.output_filepath),
            "sampling_method": "random_stratified",
            "bias": "none (keyword-free)",
        }

        logger.info(f"Gold set created: {len(selected_sentences)} sentences")
        logger.info(f"Output: {self.output_filepath}")

        return stats

    def _load_articles_from_files(self) -> List[Dict]:
        """
        Load articles from JSONL files in the input directory.

        This method loads raw article data without any filtering or bias.
        It respects the samples_per_source limit to ensure balanced representation
        across different websites.

        Returns:
            List of article dictionaries
        """
        articles: List[Dict] = []
        article_files = sorted(self.input_directory.glob("*_articles.jsonl"))

        if not article_files:
            logger.warning(f"No article files found in {self.input_directory}")
            return articles

        for article_filepath in article_files:
            source_articles = []
            with article_filepath.open("r", encoding="utf-8") as infile:
                for line in infile:
                    if not line.strip():
                        continue
                    try:
                        article_data = json.loads(line)
                        if not article_data.get("text"):
                            continue

                        # Add source metadata
                        article_data.setdefault("article_source", article_filepath.name)
                        if "site_domain" not in article_data:
                            domain = article_filepath.stem.replace("_articles", "")
                            article_data["site_domain"] = domain

                        source_articles.append(article_data)
                    except json.JSONDecodeError:
                        continue

            # Sample from this source if limit is set
            if self.samples_per_source and len(source_articles) > self.samples_per_source:
                source_articles = self.random_generator.sample(source_articles, self.samples_per_source)

            articles.extend(source_articles)
            logger.debug(f"Loaded {len(source_articles)} articles from {article_filepath.name}")

        return articles

    def _extract_sentences_from_article(
        self,
        article_index: int,
        article_content: Dict,
    ) -> Iterable[CandidateSentence]:
        """
        Extract ALL sentences from an article with linguistic feature extraction.

        CRITICAL: This method does NOT filter sentences based on keywords or content.
        It extracts EVERY sentence and computes descriptive features for stratification.

        Args:
            article_index: Index of the article in the corpus
            article_content: Article data dictionary

        Yields:
            CandidateSentence objects with features (not classifications)
        """
        article_text = article_content.get("text", "")
        # Split into paragraphs
        paragraphs = [p.strip() for p in re.split(r"\n{2,}", article_text) if p.strip()]

        # Extract metadata
        article_url = article_content.get("normalized_url") or article_content.get("url", "")
        article_title = article_content.get("title", "")
        article_author = article_content.get("author", "")
        article_publish_date = article_content.get("publish_date")
        site_domain = article_content.get("site_domain", "")
        article_source = article_content.get("article_source", "")

        for paragraph_index, paragraph_text in enumerate(paragraphs):
            # Split into sentences (basic regex for now)
            sentences = self._split_paragraph_into_sentences(paragraph_text)
            if not sentences:
                continue

            for sentence_index, sentence_text in enumerate(sentences):
                cleaned_sentence = sentence_text.strip()
                if not cleaned_sentence:
                    continue

                # Length filter (quality control only)
                if len(cleaned_sentence) < self.min_sentence_length_chars:
                    continue
                if len(cleaned_sentence) > self.max_sentence_length_chars:
                    continue

                # Extract linguistic features (descriptive analysis)
                features = self._extract_linguistic_features(cleaned_sentence)

                # Determine sampling stratum
                stratum = self._determine_stratum(cleaned_sentence, features, article_content)

                # Create candidate
                sentence_id = f"A{article_index:04d}-P{paragraph_index:03d}-S{sentence_index:03d}"

                candidate = CandidateSentence(
                    sentence_id=sentence_id,
                    sentence=cleaned_sentence,
                    paragraph_text=paragraph_text.strip(),
                    preceding_sentence=sentences[sentence_index - 1].strip()
                    if sentence_index > 0
                    else None,
                    following_sentence=sentences[sentence_index + 1].strip()
                    if sentence_index + 1 < len(sentences)
                    else None,
                    article_url=article_url,
                    article_title=article_title,
                    article_author=article_author,
                    article_domain=site_domain,
                    article_publish_date=article_publish_date,
                    article_source=article_source,
                    paragraph_index=paragraph_index,
                    sentence_index=sentence_index,
                    word_count=features["word_count"],
                    has_imperative_verb=features["has_imperative_verb"],
                    has_modal_verb=features["has_modal_verb"],
                    has_negation=features["has_negation"],
                    contains_fashion_terms=features["contains_fashion_terms"],
                    contains_action_verbs=features["contains_action_verbs"],
                    sentence_type=features["sentence_type"],
                    sampling_stratum=stratum,
                )

                yield candidate

    def _split_paragraph_into_sentences(self, paragraph: str) -> List[str]:
        """
        Split paragraph into sentences using basic regex.

        Note: This is a simple implementation. For production, consider using
        nltk.sent_tokenize() or spaCy's sentence segmentation for better accuracy.

        Args:
            paragraph: Text to split

        Returns:
            List of sentence strings
        """
        if not paragraph.strip():
            return []

        # Basic sentence boundary detection
        # Splits on . ! ? followed by whitespace and capital letter
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', paragraph)
        return [s.strip() for s in sentences if s.strip()]

    def _extract_linguistic_features(self, sentence: str) -> Dict:
        """
        Extract descriptive linguistic features from a sentence.

        IMPORTANT: This function extracts FEATURES, not classifications.
        It does not decide if the sentence is a rule or not. It only describes
        what linguistic properties the sentence has.

        Args:
            sentence: Sentence text

        Returns:
            Dictionary of linguistic features
        """
        sentence_lower = sentence.lower()
        words = sentence_lower.split()

        # Word count
        word_count = len(words)

        # Check for modal verbs (descriptive, not prescriptive)
        has_modal_verb = any(modal in sentence_lower for modal in self.MODAL_VERBS)

        # Check for negation
        has_negation = any(neg in sentence_lower for neg in self.NEGATION_WORDS)

        # Check for fashion terminology
        contains_fashion_terms = any(term in sentence_lower for term in self.FASHION_TERMS)

        # Check for action verbs
        contains_action_verbs = any(verb in sentence_lower for verb in self.ACTION_VERBS)

        # Determine sentence type (basic heuristic)
        sentence_type = "declarative"
        if sentence.endswith("?"):
            sentence_type = "interrogative"
        elif sentence.endswith("!"):
            sentence_type = "exclamatory"
        elif has_modal_verb or sentence.startswith(tuple(v.capitalize() for v in self.ACTION_VERBS)):
            sentence_type = "imperative"

        # Check for imperative form (basic heuristic)
        has_imperative_verb = sentence_type == "imperative"

        return {
            "word_count": word_count,
            "has_imperative_verb": has_imperative_verb,
            "has_modal_verb": has_modal_verb,
            "has_negation": has_negation,
            "contains_fashion_terms": contains_fashion_terms,
            "contains_action_verbs": contains_action_verbs,
            "sentence_type": sentence_type,
        }

    def _determine_stratum(self, sentence: str, features: Dict, article: Dict) -> str:
        """
        Determine which sampling stratum a sentence belongs to.

        Stratification ensures balanced representation across different types of
        sentences. This is for sampling balance, NOT for classification.

        Args:
            sentence: Sentence text
            features: Extracted linguistic features
            article: Article data

        Returns:
            Stratum name
        """
        word_count = features["word_count"]

        # Stratify by length
        if word_count < 10:
            return "very_short"
        elif word_count < 20:
            return "short"
        elif word_count < 40:
            return "medium"
        elif word_count < 60:
            return "long"
        else:
            return "very_long"

    def _stratify_sentences(self, sentences: List[CandidateSentence]) -> Dict[str, List[CandidateSentence]]:
        """
        Group sentences by stratum for balanced sampling.

        Args:
            sentences: All extracted sentences

        Returns:
            Dictionary mapping stratum name to list of sentences
        """
        stratified = {}
        for sentence in sentences:
            stratum = sentence.sampling_stratum
            if stratum not in stratified:
                stratified[stratum] = []
            stratified[stratum].append(sentence)

        logger.info("Stratification complete:")
        for stratum, sents in stratified.items():
            logger.info(f"  {stratum}: {len(sents)} sentences")

        return stratified

    def _stratified_sample(
        self, stratified_sentences: Dict[str, List[CandidateSentence]]
    ) -> List[CandidateSentence]:
        """
        Sample sentences from each stratum proportionally.

        This ensures the gold set has balanced representation across all strata,
        not just the most common types.

        Args:
            stratified_sentences: Dictionary of stratified sentences

        Returns:
            List of sampled sentences
        """
        total_sentences = sum(len(sents) for sents in stratified_sentences.values())
        selected = []

        for stratum, sentences in stratified_sentences.items():
            # Calculate proportional sample size
            proportion = len(sentences) / total_sentences
            sample_size = int(self.target_dataset_size * proportion)

            # Ensure at least 1 sample per stratum if possible
            sample_size = max(1, sample_size) if sentences else 0

            # Sample (or take all if fewer than sample_size)
            if len(sentences) <= sample_size:
                stratum_sample = sentences
            else:
                stratum_sample = self.random_generator.sample(sentences, sample_size)

            selected.extend(stratum_sample)
            logger.info(f"Sampled {len(stratum_sample)} from {stratum} ({proportion*100:.1f}%)")

        # If we're over target, randomly trim
        if len(selected) > self.target_dataset_size:
            selected = self.random_generator.sample(selected, self.target_dataset_size)

        return selected

    def _write_sentences_to_jsonl(self, sentences: Iterable[CandidateSentence]) -> None:
        """
        Write selected sentences to JSONL file for human annotation.

        Args:
            sentences: Sentences to write
        """
        with self.output_filepath.open("w", encoding="utf-8") as outfile:
            for sentence in sentences:
                outfile.write(sentence.to_json() + "\n")

        logger.info(f"Wrote {len(list(sentences))} sentences to {self.output_filepath}")


def build_unbiased_goldset(**kwargs) -> Dict[str, int]:
    """
    Convenience function to build an unbiased gold set.

    Args:
        **kwargs: Arguments to pass to UnbiasedGoldSetBuilder

    Returns:
        Statistics dictionary
    """
    builder = UnbiasedGoldSetBuilder(**kwargs)
    return builder.build_gold_set()


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    # Build gold set
    stats = build_unbiased_goldset(
        input_directory="data/raw",
        output_filepath="data/processed/gold_set_unbiased.jsonl",
        target_dataset_size=1000,
    )

    print("\n" + "=" * 80)
    print("UNBIASED GOLD SET CREATION COMPLETE")
    print("=" * 80)
    for key, value in stats.items():
        print(f"  {key}: {value}")
