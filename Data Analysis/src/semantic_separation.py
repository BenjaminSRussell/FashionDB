from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path, PurePath
from typing import Iterable, List, Mapping, Optional, Sequence

# The following try/except blocks guard against missing optional dependencies.
try:
    from spellchecker import SpellChecker
except ImportError:  # pragma: no cover
    SpellChecker = None  # type: ignore
    "Type alias for optional dependency."

try:
    import language_tool_python
except ImportError:  # pragma: no cover
    language_tool_python = None  # type: ignore
    "Type alias for optional dependency."

try:
    from sentence_transformers import SentenceTransformer
except ImportError:  # pragma: no cover
    SentenceTransformer = None  # type: ignore
    "Type alias for optional dependency."

try:
    from sklearn.cluster import KMeans
    from numpy.typing import NDArray
    from sklearn.metrics import silhouette_score
except ImportError:  # pragma: no cover
    KMeans = None  # type: ignore
    silhouette_score = None  # type: ignore

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"


@dataclass
class PipelineConfig:
    input_path: PurePath = DATA_DIR / "reddit_fashion_data_unique.json"
    output_path: Path = DATA_DIR / "semantic_engine_evaluation.json"
    model_name: str = "sentence-transformers/all-mpnet-base-v2"
    batch_size: int = 64
    min_k: int = 6
    max_k: int = 18
    samples_per_cluster: int = 5
    use_spellcheck: bool = False  # Set to True to enable spell-checking (very slow!)
    use_language_tool: bool = False
    skip_spellcheck: Sequence[str] = field(
        default_factory=lambda: [
            "reddit",
            "malefashionadvice",
            "femalefashionadvice",
            "streetwear",
            "uniqlo",
            "ootd",
            "h&m",
            "fitpic",
            "selvedge",
            "workwear",
            "athleisure",
            "menswear",
            "lookbook",
        ]
    )


def ensure_module(name: str, module: Optional[object], install_hint: str) -> None:
    """Raise a RuntimeError if an optional dependency is not installed."""
    if module is None:
        raise RuntimeError(
            f"Missing optional dependency '{name}'. Install it with:\n    {install_hint}"
        )


def normalize_whitespace(text: str) -> str:
    """Collapse multiple whitespace characters into a single space."""
    return re.sub(r"\s+", " ", text).strip()


def preserve_case(original: str, correction: str) -> str:
    """Apply the casing of an original word to its corrected version."""
    if original.isupper():
        return correction.upper()
    if original[:1].isupper():
        return correction.capitalize()
    return correction


def build_spellchecker(skip_words: Sequence[str]) -> "SpellChecker":
    """Initialize the spellchecker with domain-specific words."""
    ensure_module("spellchecker", SpellChecker, "pip install pyspellchecker")
    checker: "SpellChecker" = SpellChecker(language="en")
    checker.word_frequency.load_words(word.lower() for word in skip_words)
    return checker


def correct_spelling(
    text: str, checker: "SpellChecker", skip_words: Sequence[str]
) -> str:
    """Correct spelling in a string while preserving case and skipping domain words."""
    skip_lookup = {w.lower() for w in skip_words}
    tokens = re.findall(r"[A-Za-z]+|[^A-Za-z]+", text)
    corrected: List[str] = []

    # Batch collect all alpha tokens to check at once for better performance
    alpha_tokens = [token for token in tokens if token.isalpha()]
    alpha_lower = [t.lower() for t in alpha_tokens]

    # Filter out tokens we want to skip (domain words, short words)
    tokens_to_check = [
        lower for lower in alpha_lower
        if lower not in skip_lookup and len(lower) > 2
    ]

    # Batch check all unknown words at once
    unknown_set = set(checker.unknown(tokens_to_check)) if tokens_to_check else set()

    for token in tokens:
        if not token.isalpha():
            corrected.append(token)
            continue

        lower = token.lower()
        if lower in skip_lookup or len(lower) <= 2:
            corrected.append(token)
            continue

        # Use pre-computed unknown set instead of checking each word individually
        if lower not in unknown_set:
            corrected.append(token)
            continue

        best = checker.correction(lower)
        if best and best != lower:
            corrected.append(preserve_case(token, best))
        else:
            corrected.append(token)

    return "".join(corrected)


def sentence_case(text: str) -> str:
    """Convert text to sentence case, ensuring each sentence starts with a capital."""
    if not text:
        return text

    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    formatted: List[str] = []

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        if sentence[-1] not in ".!?":
            sentence += "."

        for idx, char in enumerate(sentence):
            if char.isalpha():
                sentence = sentence[:idx] + char.upper() + sentence[idx + 1 :]
                break

        formatted.append(sentence)

    return " ".join(formatted)


def apply_language_tool(text: str, tool: "language_tool_python.LanguageTool") -> str:
    """Correct grammar and style issues using LanguageTool."""
    return tool.correct(text)


def load_posts(path: Path) -> List[tuple[str, Mapping[str, object]]]:
    """Load posts from a JSON file into a list of (category, post_data) tuples."""
    with path.open("r", encoding="utf-8") as file_handle:
        data = json.load(file_handle)

    posts: List[tuple[str, Mapping[str, object]]] = []
    for category, items in data.items():  # Assumes JSON structure is {category: [posts]}
        if isinstance(items, list):
            posts.extend((category, post) for post in items if isinstance(post, dict))
    return posts


def extract_top_comment(post: Mapping[str, object]) -> str:
    """Extract the body of the highest-scoring comment from a post."""
    comments = post.get("comments")
    if not isinstance(comments, list) or not comments:
        return ""

    top = max(
        comments,
        key=lambda comment: comment.get("score", 0) if isinstance(comment, dict) else 0,
    )
    if isinstance(top, dict):
        return str(top.get("body", "")).strip()
    return ""


def prepare_corpus(
    posts: Iterable[tuple[str, Mapping[str, object]]],
    checker: Optional[SpellChecker],
    skip_words: Sequence[str],
    grammar_tool: Optional["language_tool_python.LanguageTool"],
) -> List[Mapping[str, str]]:
    """Clean and prepare text from posts for embedding."""
    corpus: List[Mapping[str, str]] = []
    posts_list = list(posts)
    total = len(posts_list)

    for idx, (category, post) in enumerate(posts_list, 1):
        if idx % 500 == 0 or idx == 1:
            print(f"  Processing post {idx}/{total} ({idx/total*100:.1f}%)...")

        title = str(post.get("title", "")).strip()
        selftext = str(post.get("selftext", "")).strip()
        top_comment = extract_top_comment(post)

        combined = normalize_whitespace(
            " ".join(filter(None, [title, selftext, top_comment]))
        )
        if not combined:
            continue

        cleaned = combined
        if checker:
            cleaned = correct_spelling(cleaned, checker, skip_words)
        cleaned = sentence_case(cleaned)
        if grammar_tool:
            cleaned = apply_language_tool(cleaned, grammar_tool)

        corpus.append(
            {
                "post_id": str(post.get("post_id", "")),
                "title": title,
                "category": category,
                "clean_text": cleaned,
            }
        )

    return corpus


def embed_texts(texts: Sequence[str], config: PipelineConfig) -> NDArray:
    """Encodes a sequence of texts into sentence embeddings."""
    ensure_module(
        "sentence-transformers",
        SentenceTransformer,
        "pip install sentence-transformers",
    )
    model = SentenceTransformer(config.model_name)
    return model.encode(
        texts,
        batch_size=config.batch_size,
        show_progress_bar=True,
        normalize_embeddings=True,
    )


def evaluate_clusters(embeddings: NDArray, config: PipelineConfig):
    """Perform K-Means clustering and evaluate results using silhouette scores."""
    ensure_module("scikit-learn", KMeans, "pip install scikit-learn")
    ensure_module("scikit-learn", silhouette_score, "pip install scikit-learn")

    scores = []
    for k in range(config.min_k, config.max_k + 1):
        model = KMeans(
            n_clusters=k,
            random_state=42,
            n_init="auto",
        )
        labels = model.fit_predict(embeddings)
        score = float(silhouette_score(embeddings, labels))
        scores.append(
            {
                "k": k,
                "silhouette": score,
                "model_state": model,
                "labels": labels,
            }
        )

    scores.sort(key=lambda item: item["silhouette"], reverse=True)
    return scores


def summarize_clusters(
    corpus: Sequence[Mapping[str, str]],
    labels: NDArray,
    samples_per_cluster: int,
) -> List[Mapping[str, object]]:
    """Generate a summary for each cluster with top categories and text examples."""
    clusters_data: Mapping[int, Mapping[str, object]] = defaultdict(
        lambda: {"category_counts": Counter(), "examples": []}
    )

    for record, label in zip(corpus, labels):
        cluster_payload = clusters_data[label]
        category = record.get("category", "")
        if category:
            cluster_payload["category_counts"][category] += 1  # type: ignore[index]

        examples: List[Mapping[str, str]] = cluster_payload["examples"]  # type: ignore[assignment]
        if len(examples) < samples_per_cluster:
            examples.append(
                {
                    "post_id": record.get("post_id", ""),
                    "excerpt": record.get("clean_text", "")[:320],
                }
            )

    summary = []
    for label, payload in clusters_data.items():
        counts = payload["category_counts"].most_common(5)  # type: ignore[index]
        summary.append(
            {
                "cluster": int(label),
                "top_categories": [
                    {"category": category, "count": count}
                    for category, count in counts
                ],
                "examples": payload["examples"],  # type: ignore[index]
            }
        )

    summary.sort(key=lambda item: item["cluster"])
    return summary


def serialize_scores(scores, summary, config: PipelineConfig) -> Mapping[str, object]:
    """Format evaluation results and cluster summaries for JSON serialization."""
    return {
        "model_name": config.model_name,
        "cluster_scores": [
            {"k": entry["k"], "silhouette": entry["silhouette"]}
            for entry in scores
        ],
        "best_k": scores[0]["k"],
        "best_silhouette": scores[0]["silhouette"],
        "cluster_summaries": summary,
    }


def write_results(payload: Mapping[str, object], config: PipelineConfig) -> None:
    """Write the final evaluation payload to a JSON file."""
    config.output_path.parent.mkdir(parents=True, exist_ok=True)
    with config.output_path.open("w", encoding="utf-8") as file_handle:
        json.dump(payload, file_handle, indent=2)


def run_pipeline(config: PipelineConfig) -> None:
    """Execute the full semantic analysis pipeline."""
    print(f"Loading posts from {config.input_path}...")
    posts = load_posts(config.input_path)
    print(f"Loaded {len(posts)} posts")

    checker = None
    if config.use_spellcheck:
        print("Building spellchecker (note: this makes processing MUCH slower)...")
        checker = build_spellchecker(config.skip_spellcheck)
    else:
        print("Spell-checking disabled for faster processing")

    tool = None
    if config.use_language_tool:
        ensure_module(
            "language-tool-python",
            language_tool_python,
            "pip install language-tool-python",
        )
        tool = language_tool_python.LanguageTool("en-US")

    print("Cleaning and normalizing text...")
    corpus = prepare_corpus(posts, checker, config.skip_spellcheck, tool)
    texts = [record["clean_text"] for record in corpus]
    print(f"Prepared {len(texts)} cleaned texts")

    print(f"Embedding texts with {config.model_name}...")
    embeddings = embed_texts(texts, config)

    print("Evaluating semantic cohesion across cluster counts...")
    scores = evaluate_clusters(embeddings, config)
    best = scores[0]
    print(f"Best silhouette score: {best['silhouette']:.4f} at k={best['k']}")

    print("Summarizing top clusters for manual inspection...")
    summary = summarize_clusters(corpus, best["labels"], config.samples_per_cluster)
    payload = serialize_scores(scores, summary, config)

    print(f"Writing evaluation bundle to {config.output_path}...")
    write_results(payload, config)
    print("Done.")


if __name__ == "__main__":
    run_pipeline(PipelineConfig())
