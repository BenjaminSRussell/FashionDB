import argparse, json, os, sys, time, hashlib
from datetime import datetime, timezone
from typing import List, Literal, Optional, Dict

# libs
import ollama  # pip install -U ollama
from pydantic import BaseModel, Field, ValidationError, field_validator

class AppConfig:
    # Default runtime settings for the application.
    DEFAULT_MODEL: str = os.getenv("MODEL", "qwen2.5:1.5b-instruct")
    TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0.1"))
    TOP_K_COMMENTS: int = int(os.getenv("TOP_K_COMMENTS", "16"))
    MAX_POSTS: int = int(os.getenv("MAX_POSTS", "0"))  # 0 = no limit
    MAX_CHARS_PER_POST: int = int(os.getenv("MAX_CHARS_PER_POST", "9000"))
    RETRY_ATTEMPTS: int = int(os.getenv("RETRY_ATTEMPTS", "1"))

# -----------------------------
# Output schema (Pydantic v2)
# -----------------------------
RuleType = Literal["absolute", "guideline", "trend", "contrarian"]
Category = Literal[
    "fit", "color", "formality", "fabric", "footwear", "accessories",
    "season", "pattern", "proportion", "grooming", "occasion", "general"
]
Severity = Literal["low", "medium", "high"]

class Citation(BaseModel):
    # A short source snippet tied to a rule.
    source_post_id: str = Field(..., description="Reddit post ID (e.g., 't3_12345')")
    source_url: Optional[str] = Field(None, description="URL to the post or comment")
    source_comment_id: Optional[str] = Field(None, description="Reddit comment ID (e.g., 't1_abcde')")
    snippet: str = Field(..., description="A short, representative quote from the source text (max 240 chars)")
    upvotes: Optional[int] = Field(None, description="The score of the post or comment")

    @field_validator("snippet")
    def clean_and_trim_snippet(cls, snippet_text: str) -> str:
        # Remove extra whitespace and cap snippet length.
        return " ".join(snippet_text.split()).strip()[:240]

class Rule(BaseModel):
    # One actionable fashion rule.
    rule_id: str = Field(..., description="A unique, stable identifier for the rule (SHA1 hash)")
    text: str = Field(..., description="The clear and concise text of the rule")
    rule_type: RuleType = Field(..., description="The type of rule (e.g., absolute, guideline)")
    categories: List[Category] = Field(..., min_items=1, description="The fashion categories this rule belongs to")
    context_tags: List[str] = Field(..., description="Keywords for when the rule applies (e.g., 'office', 'summer')")
    examples: List[str] = Field(default_factory=list, description="Brief, generic examples of how to apply the rule")
    exceptions: List[str] = Field(default_factory=list, description="Situations where this rule might not apply")
    rationale: Optional[str] = Field(None, description="A one-sentence explanation of why the rule exists")
    confidence: float = Field(..., ge=0.0, le=1.0, description="The model's confidence in the extracted rule (0.0-1.0)")
    citations: List[Citation] = Field(..., min_items=1, description="A list of sources that support this rule")
    safety: Optional[Severity] = Field(None, description="How critical it is to follow this rule to avoid a faux pas")

class RuleDigest(BaseModel):
    # A bundle of rules pulled from one source post.
    source_platform: Literal["reddit", "web", "forum", "blog"] = Field("reddit", description="The platform the source material is from")
    extracted_at: str = Field(..., description="The UTC timestamp of when the extraction occurred (ISO 8601)")
    domain_topic: Literal["menswear", "general_style", "streetwear", "classic_menswear", "workwear", "formalwear", "athleisure", "other"] = Field("menswear", description="The broad fashion domain of the source material")
    source_post_id: str = Field(..., description="The unique identifier of the source post")
    source_title: str = Field(..., description="The title of the source post")
    source_url: Optional[str] = Field(None, description="The URL of the source post")
    rules: List[Rule] = Field(default_factory=list, description="A list of the rules extracted from the post")

# Model-facing schemas: omit fields we overwrite in code so small models don't invent them.
class ModelCitation(BaseModel):
    source_post_id: Optional[str] = None
    source_url: Optional[str] = None
    source_comment_id: Optional[str] = None
    snippet: str = Field(..., description="A short, representative quote from the source text (max 240 chars)")
    upvotes: Optional[int] = None

    @field_validator("snippet")
    def clean_and_trim_snippet(cls, snippet_text: str) -> str:
        return " ".join(snippet_text.split()).strip()[:240]

class ModelRule(BaseModel):
    text: str
    rule_type: RuleType
    categories: List[Category] = Field(..., min_items=1)
    context_tags: List[str] = Field(default_factory=list)
    examples: List[str] = Field(default_factory=list)
    exceptions: List[str] = Field(default_factory=list)
    rationale: Optional[str] = None
    confidence: float = Field(..., ge=0.0, le=1.0)
    citations: List[ModelCitation] = Field(default_factory=list)
    safety: Optional[Severity] = None

class ModelRuleDigest(BaseModel):
    domain_topic: Literal["menswear", "general_style", "streetwear", "classic_menswear", "workwear", "formalwear", "athleisure", "other"] = "menswear"
    rules: List[ModelRule] = Field(default_factory=list)  # empty allowed — posts may have no rules

# -----------------------------
# Helpers
# -----------------------------
def current_iso_timestamp() -> str:
    # Current UTC time in ISO 8601.
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def hash_sha1(text: str) -> str:
    # SHA1 helper for IDs.
    return hashlib.sha1(text.encode("utf-8")).hexdigest()

def clean_text_block(text: str, max_chars: int) -> str:
    # Collapse whitespace and trim to the max length.
    collapsed = " ".join(text.split()).strip()
    return collapsed[:max_chars] if len(collapsed) > max_chars else collapsed

def select_top_comments(comments: List[Dict], max_count: int) -> List[Dict]:
    # Pick the best comments by score.
    clean_comments = [
        comment for comment in comments
        if isinstance(comment, dict) and comment.get("body") and comment.get("score") is not None
    ]
    clean_comments.sort(key=lambda comment: int(comment.get("score", 0)), reverse=True)
    return clean_comments[:max_count]

def compose_prompt(post_record: Dict) -> str:
    """Build a budgeted prompt that keeps newlines and always retains the citation instruction."""
    max_chars = AppConfig.MAX_CHARS_PER_POST
    citation_instruction = (
        "For each rule, include at least one citation snippet (<=240 chars) "
        "with the comment_id or post_id from the lists above. "
        "If the post contains no actionable style rule, return an empty rules list."
    )
    header = (
        "You are an expert menswear editor. Extract concrete, atomic style rules "
        "from this discussion.\n"
        "Focus on durable rules (fit, proportion, color, formality), not product shilling.\n"
    )
    title = clean_text_block(post_record.get("title", ""), 300)
    post_id = post_record.get("post_id", "")
    selftext = clean_text_block(post_record.get("selftext", ""), 1200)
    post_block = f"Post:\n- id: {post_id}\n- title: {title}\n- selftext: {selftext}\n"

    top_comments = select_top_comments(post_record.get("comments", []), AppConfig.TOP_K_COMMENTS)
    comment_lines = []
    for comment in top_comments:
        body = clean_text_block(comment.get("body", ""), 600)
        if not body or body.lower() == "[deleted]":
            continue
        comment_lines.append(f"- ({comment.get('score')}↑) [{comment.get('comment_id', '')}] {body}")

    reserved = len(header) + len(post_block) + len(citation_instruction) + 40
    budget = max(500, max_chars - reserved)
    kept = []
    used = 0
    for line in comment_lines:
        extra = len(line) + 1
        if used + extra > budget:
            break
        kept.append(line)
        used += extra
    comment_section = "Top comments:\n" + ("\n".join(kept) if kept else "(none)")
    prompt = f"{header}\n{post_block}\n{comment_section}\n\n{citation_instruction}\n"
    if len(prompt) > max_chars:
        # Last resort: shrink selftext further rather than cutting the instruction.
        overflow = len(prompt) - max_chars
        selftext = selftext[: max(0, len(selftext) - overflow - 20)]
        post_block = f"Post:\n- id: {post_id}\n- title: {title}\n- selftext: {selftext}\n"
        prompt = f"{header}\n{post_block}\n{comment_section}\n\n{citation_instruction}\n"
    return prompt


def collect_prompt_ids(post_record: Dict) -> set:
    """IDs that citations are allowed to reference."""
    ids = set()
    if pid := post_record.get("post_id"):
        ids.add(str(pid))
    for comment in post_record.get("comments", []) or []:
        if isinstance(comment, dict) and comment.get("comment_id"):
            ids.add(str(comment["comment_id"]))
    return ids


def filter_citations(rule: Rule, allowed_ids: set, post_id: str) -> Rule:
    """Drop hallucinated citation IDs; keep snippets that cite known IDs."""
    kept = []
    for cite in rule.citations:
        ok_post = not cite.source_post_id or cite.source_post_id in allowed_ids or cite.source_post_id == post_id
        ok_comment = not cite.source_comment_id or cite.source_comment_id in allowed_ids
        if ok_post and ok_comment and cite.snippet:
            kept.append(cite)
    rule.citations = kept
    return rule

SYSTEM_MSG = {
    "role": "system",
    "content": (
        "You convert discussions into structured menswear rules. "
        "Output MUST strictly follow the provided JSON schema. "
        "Do not add fields. Do not include prose outside JSON."
    ),
}

def call_ollama(model: str, prompt: str) -> str:
    # Call Ollama and return the raw response.
    response = ollama.chat(
        model=model,
        messages=[SYSTEM_MSG, {"role": "user", "content": prompt}],
        format=ModelRuleDigest.model_json_schema(),
        options={"temperature": AppConfig.TEMPERATURE},
    )
    return response.message.content

def validate_with_retries(model: str, prompt: str) -> Optional[ModelRuleDigest]:
    # Keep asking until the response validates or retries run out.
    for attempt_index in range(1 + AppConfig.RETRY_ATTEMPTS):
        try:
            raw_response = call_ollama(model, prompt)
            return ModelRuleDigest.model_validate_json(raw_response)
        except ValidationError as error:
            print(f"Validation attempt {attempt_index + 1} failed: {error}", file=sys.stderr)
            prompt += "\n\nSTRICT: Your previous output did not validate. Reply with VALID JSON ONLY matching the schema. No explanations."
            time.sleep(0.2)
    return None

def build_rule_id(canonical_text: str, post_id: str) -> str:
    # Stable ID based on rule text and post id.
    return hash_sha1(f"{(canonical_text or '').strip().lower()}::{post_id}")

def assign_rule_ids(digest: RuleDigest) -> RuleDigest:
    # Always use the stable text+post hash — never trust model-invented IDs.
    for rule in digest.rules:
        rule.rule_id = build_rule_id(rule.text, digest.source_post_id)
    return digest


def model_digest_to_stored(model_digest: ModelRuleDigest, post_record: Dict, post_id: str) -> RuleDigest:
    """Promote model output into the stored RuleDigest with server-owned fields."""
    allowed = collect_prompt_ids(post_record)
    rules: List[Rule] = []
    for mr in model_digest.rules:
        citations = [
            Citation(
                source_post_id=c.source_post_id or post_id,
                source_url=c.source_url or post_record.get("url"),
                source_comment_id=c.source_comment_id,
                snippet=c.snippet,
                upvotes=c.upvotes,
            )
            for c in mr.citations
        ]
        rule = Rule(
            rule_id=build_rule_id(mr.text, post_id),
            text=mr.text,
            rule_type=mr.rule_type,
            categories=mr.categories,
            context_tags=mr.context_tags,
            examples=mr.examples,
            exceptions=mr.exceptions,
            rationale=mr.rationale,
            confidence=mr.confidence,
            citations=citations or [
                Citation(source_post_id=post_id, source_url=post_record.get("url"), snippet=mr.text[:240])
            ],
            safety=mr.safety,
        )
        rule = filter_citations(rule, allowed, post_id)
        if not rule.citations:
            continue
        rules.append(rule)
    return RuleDigest(
        extracted_at=current_iso_timestamp(),
        domain_topic=model_digest.domain_topic,
        source_post_id=post_id,
        source_title=post_record.get("title", ""),
        source_url=post_record.get("url"),
        rules=rules,
    )

def append_jsonl_record(path: str, obj: dict):
    # Append an object as one JSONL line.
    with open(path, "a", encoding="utf-8") as jsonl_file:
        jsonl_file.write(json.dumps(obj, ensure_ascii=False) + "\n")

def load_existing_rule_ids(path: str) -> set:
    # Gather rule IDs from an existing JSONL file to avoid duplicates.
    existing_ids = set()
    if not os.path.exists(path):
        return existing_ids
    with open(path, "r", encoding="utf-8") as jsonl_file:
        for line in jsonl_file:
            try:
                record = json.loads(line)
                for rule in record.get("rules", []):
                    if rule_id := rule.get("rule_id"):
                        existing_ids.add(rule_id)
            except json.JSONDecodeError:
                continue
    return existing_ids

# -----------------------------
# CLI / main
# -----------------------------
def process_post_file(input_path: str, out_path: str, model: str):
    # Read posts, extract rules, and write results to JSONL.
    try:
        with open(input_path, "r", encoding="utf-8") as input_file:
            posts_to_process = json.load(input_file)
        if not isinstance(posts_to_process, list):
            print("Input must be a list of posts.", file=sys.stderr)
            sys.exit(1)
    except (FileNotFoundError, json.JSONDecodeError) as error:
        print(f"Error reading input file: {error}", file=sys.stderr)
        sys.exit(1)

    existing_rule_ids = load_existing_rule_ids(out_path)
    processed_post_total = 0
    new_rule_total = 0

    for post_index, post_record in enumerate(posts_to_process):
        if AppConfig.MAX_POSTS and processed_post_total >= AppConfig.MAX_POSTS:
            break

        post_id = str(post_record.get("post_id", f"post_{post_index}"))
        prompt = compose_prompt(post_record)

        model_digest = validate_with_retries(model, prompt)
        if not model_digest:
            print(f"[skip] {post_id}: Failed to get a valid response from the model.", file=sys.stderr)
            processed_post_total += 1
            continue

        rule_digest = model_digest_to_stored(model_digest, post_record, post_id)
        rule_digest = assign_rule_ids(rule_digest)

        novel_rules = [rule for rule in rule_digest.rules if rule.rule_id not in existing_rule_ids]
        if not novel_rules:
            print(f"[dupe] {post_id}: No new rules found.")
            processed_post_total += 1
            continue

        jsonl_record = rule_digest.model_dump()
        jsonl_record["rules"] = [rule.model_dump() for rule in novel_rules]
        for rule_entry in novel_rules:
            existing_rule_ids.add(rule_entry.rule_id)
        append_jsonl_record(out_path, jsonl_record)

        new_rule_total += len(novel_rules)
        processed_post_total += 1
        print(f"[ok] {post_id}: Added {len(novel_rules)} new rules. Total saved: {len(existing_rule_ids)}")

    print(f"\nProcessing complete. Processed {processed_post_total} posts and saved {new_rule_total} new rules to {out_path}.")

def main():
    # CLI entry point.
    parser = argparse.ArgumentParser(description="Extract structured menswear rules from Reddit JSON using Ollama.")
    parser.add_argument("--input", required=True, help="Path to the input Reddit JSON file.")
    parser.add_argument("--out", default="rules.jsonl", help="Path to the output JSONL file.")
    parser.add_argument("--model", default=AppConfig.DEFAULT_MODEL, help=f"The Ollama model to use (default: {AppConfig.DEFAULT_MODEL}).")
    cli_args = parser.parse_args()

    try:
        ollama.chat(model=cli_args.model, messages=[{"role": "user", "content": "ping"}])
    except Exception:
        print(f"Could not connect to Ollama with model '{cli_args.model}'. Ensure Ollama is running and the model is pulled.", file=sys.stderr)
        sys.exit(1)

    process_post_file(cli_args.input, cli_args.out, cli_args.model)

if __name__ == "__main__":
    main()
