"""Regression: full-pipeline clean thresholds must accept real fashion rules."""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from clean import RuleCleaner, RuleValidationConfig  # noqa: E402


FIXTURE_TEXT = (
    "Always pair a navy blazer with charcoal grey trousers for formal interviews"
)


def test_twelve_word_rule_survives_cli_aligned_defaults():
    """A 12-word fixture must pass the word-count gate used by run.full_pipeline."""
    words = FIXTURE_TEXT.split()
    assert len(words) == 12, len(words)

    cfg = RuleValidationConfig(
        min_word_count=5,
        max_word_count=50,
        min_quality_score=7,
    )
    cleaner = RuleCleaner(cfg)
    rule = {
        "rule_text": FIXTURE_TEXT,
        "quality_score": 8,
        "source": "fixture",
        "category": "color",
    }
    result = cleaner.validate_rule(rule)
    # Word-count reasons must not appear (the bug was max_word_count=7)
    reasons = result.get("reasons") or []
    assert not any("Too long" in r or "Too short" in r for r in reasons), reasons
    assert cfg.min_word_count <= len(words) <= cfg.max_word_count


def test_old_max_7_would_reject_fixture():
    """Prove the old hardcoded max=7 would reject this same fixture."""
    cfg = RuleValidationConfig(min_word_count=5, max_word_count=7, min_quality_score=7)
    cleaner = RuleCleaner(cfg)
    result = cleaner.validate_rule({
        "rule_text": FIXTURE_TEXT,
        "quality_score": 8,
    })
    assert any("Too long" in r for r in result["reasons"]), result


def test_full_pipeline_config_is_not_max_7():
    """Guard: run.full_pipeline must not hardcode max_word_count=7 as a kwarg."""
    src = (HERE / "run.py").read_text()
    assert "max_word_count=7," not in src and "max_word_count=7)" not in src
    assert "max_word_count=50" in src


if __name__ == "__main__":
    test_twelve_word_rule_survives_cli_aligned_defaults()
    test_old_max_7_would_reject_fixture()
    test_full_pipeline_config_is_not_max_7()
    print("ok")
