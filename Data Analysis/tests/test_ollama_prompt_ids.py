import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "standardization"))
from ollama import compose_prompt, build_rule_id, assign_rule_ids, RuleDigest, Rule, Citation, ModelRuleDigest, model_digest_to_stored

def test_compose_prompt_keeps_citation_instruction():
    post = {
        "post_id": "t3_abc",
        "title": "Fit question",
        "selftext": "x" * 2000,
        "comments": [
            {"comment_id": f"t1_{i}", "score": 10, "body": ("y" * 500)}
            for i in range(20)
        ],
    }
    prompt = compose_prompt(post)
    assert "citation snippet" in prompt
    assert "\\n" in prompt or "\n" in prompt
    assert len(prompt) <= 9000 + 50  # soft bound

def test_build_rule_id_stable_and_overrides_model_id():
    a = build_rule_id("Break in leather shoes", "t3_1")
    b = build_rule_id("Break in leather shoes", "t3_1")
    assert a == b
    digest = RuleDigest(
        extracted_at="2026-01-01T00:00:00+00:00",
        source_post_id="t3_1",
        source_title="t",
        rules=[
            Rule(
                rule_id="rule_1",
                text="Break in leather shoes",
                rule_type="guideline",
                categories=["footwear"],
                context_tags=[],
                confidence=0.9,
                citations=[Citation(source_post_id="t3_1", snippet="break in")],
            )
        ],
    )
    assign_rule_ids(digest)
    assert digest.rules[0].rule_id == a
    assert digest.rules[0].rule_id != "rule_1"
