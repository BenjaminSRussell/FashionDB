import re
from typing import List, Set, Tuple, Optional
from datasketch import MinHash, MinHashLSH
from rapidfuzz import fuzz
import logging

logger = logging.getLogger(__name__)


class RuleDeduplicator:
    # Detects duplicate rules using MinHash and fuzzy matching.
    def __init__(
        self,
        minhash_similarity_threshold: float = 0.5,
        fuzzy_similarity_threshold: int = 80,
        minhash_permutations: int = 128,
    ):
        # Store thresholds used by the duplicate checks.
        self.minhash_similarity_threshold = minhash_similarity_threshold
        self.fuzzy_similarity_threshold = fuzzy_similarity_threshold
        self.minhash_permutations = minhash_permutations

        # Index and caches for reuse.
        self.lsh_index = MinHashLSH(
            threshold=minhash_similarity_threshold, num_perm=minhash_permutations
        )

        self.seen_normalized_rules: Set[str] = set()
        self.rule_to_minhash = {}
        self.rule_to_normalized_text = {}

    def _normalize_text(self, text: str) -> str:
        # Normalize rule text before comparison.
        text = text.lower()
        text = re.sub(r"https?://\S+", "", text)
        text = re.sub(r"\(source:.*?\)", "", text, flags=re.IGNORECASE)
        text = re.sub(r"source:.*$", "", text, flags=re.IGNORECASE)
        text = re.sub(r"[^\w\s]", " ", text)
        text = " ".join(text.split())
        return text.strip()

    def _create_minhash_signature(self, text: str) -> MinHash:
        # Build a MinHash signature from rule tokens and bigrams.
        normalized_text = self._normalize_text(text)
        minhash_signature = MinHash(num_perm=self.minhash_permutations)

        tokens = normalized_text.split()

        for token in tokens:
            minhash_signature.update(token.encode("utf-8"))

        for i in range(len(tokens) - 1):
            bigram = f"{tokens[i]} {tokens[i+1]}"
            minhash_signature.update(bigram.encode("utf-8"))

        return minhash_signature

    def _register_rule(
        self, rule_id: Optional[str], normalized_rule: str, minhash_signature: MinHash
    ) -> None:
        # Store rule metadata for future duplicate checks.
        rule_key = rule_id or normalized_rule
        self.lsh_index.insert(rule_key, minhash_signature)
        self.seen_normalized_rules.add(normalized_rule)
        self.rule_to_minhash[rule_key] = minhash_signature
        self.rule_to_normalized_text[rule_key] = normalized_rule

    def is_rule_a_duplicate(
        self, rule_text: str, rule_id: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        # Determine whether the supplied rule already exists.
        normalized_rule = self._normalize_text(rule_text)

        if normalized_rule in self.seen_normalized_rules:
            return True, None

        rule_minhash = self._create_minhash_signature(rule_text)
        candidate_ids = self.lsh_index.query(rule_minhash)

        if not candidate_ids:
            self._register_rule(rule_id, normalized_rule, rule_minhash)
            return False, None

        for candidate_id in candidate_ids:
            candidate_text = self.rule_to_normalized_text.get(
                candidate_id, candidate_id
            )

            similarity_score = fuzz.token_set_ratio(
                normalized_rule, candidate_text
            )

            if similarity_score >= self.fuzzy_similarity_threshold:
                logger.debug(
                    "Found duplicate: %s%% similar to %s",
                    similarity_score,
                    candidate_id,
                )
                return True, candidate_id

        self._register_rule(rule_id, normalized_rule, rule_minhash)
        return False, None

    def add_rule_to_index(self, rule_text: str, rule_id: Optional[str] = None) -> bool:
        # Insert a known unique rule without duplicate checks.
        normalized_rule = self._normalize_text(rule_text)

        if normalized_rule in self.seen_normalized_rules:
            return False

        minhash_signature = self._create_minhash_signature(rule_text)
        self._register_rule(rule_id, normalized_rule, minhash_signature)

        return True

    def get_deduplication_stats(self) -> dict:
        # Report a snapshot of internal counters.
        return {
            "total_rules": len(self.seen_normalized_rules),
            "lsh_buckets": len(self.lsh_index.hashtables[0].keys())
            if self.lsh_index.hashtables
            else 0,
            "minhash_threshold": self.minhash_similarity_threshold,
            "fuzzy_threshold": self.fuzzy_similarity_threshold,
        }


def deduplicate_rules_in_list(
    rules: List[dict], text_key: str = "rule_text"
) -> Tuple[List[dict], List[dict]]:
    # Deduplicate a list of rule dicts.
    deduplicator = RuleDeduplicator()
    unique_rules = []
    duplicate_rules = []

    for rule_dict in rules:
        rule_text = rule_dict.get(text_key, "")
        if not rule_text:
            continue

        is_duplicate, duplicate_of_rule_id = deduplicator.is_rule_a_duplicate(rule_text)

        if is_duplicate:
            rule_dict["duplicate_of"] = duplicate_of_rule_id
            duplicate_rules.append(rule_dict)
        else:
            unique_rules.append(rule_dict)

    logger.info("Deduplication complete:")
    logger.info(f"  Unique rules: {len(unique_rules)}")
    logger.info(f"  Duplicates: {len(duplicate_rules)}")

    total_rules = len(rules)
    duplicate_rate = (
        len(duplicate_rules) / total_rules * 100 if total_rules else 0.0
    )
    logger.info(f"  Deduplication rate: {duplicate_rate:.1f}%")

    return unique_rules, duplicate_rules


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    test_rules = [
        "Your tie should always be darker than your shirt.",
        "Always ensure your tie is darker than your shirt.",
        "A tie must be darker than the shirt you're wearing.",
        "Black shoes should be worn with dark suits.",
        "Wear black shoes with dark-colored suits.",
        "Brown shoes go well with casual outfits.",
        "Your belt should match your shoes.",
        "Match your belt to your shoe color.",
        "Never wear a black belt with brown shoes.",
    ]

    print("Testing RuleDeduplicator:")
    print("=" * 80)

    deduplicator = RuleDeduplicator()

    for i, rule in enumerate(test_rules, 1):
        is_duplicate, duplicate_of = deduplicator.is_rule_a_duplicate(
            rule, rule_id=f"rule_{i}"
        )
        status = "DUPLICATE" if is_duplicate else "UNIQUE"
        print(f'{i}. [{status}] {rule}')
        if is_duplicate:
            print(f"   -> Duplicate of: {duplicate_of}")

    print("\n" + "=" * 80)
    print("STATS:")
    stats = deduplicator.get_deduplication_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
