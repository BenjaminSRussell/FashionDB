import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from standardization.validate_rules import load_schema, validate_rule  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"


def test_valid_golden_passes():
    rule = json.loads((FIXTURES / "rule_valid.json").read_text())
    errs = validate_rule(rule, load_schema())
    assert errs == [], errs


def test_invalid_additional_property_fails():
    rule = json.loads((FIXTURES / "rule_invalid_extra.json").read_text())
    errs = validate_rule(rule, load_schema())
    assert any("additional property" in e for e in errs), errs


def test_missing_required_fails():
    rule = json.loads((FIXTURES / "rule_valid.json").read_text())
    del rule["claim"]
    errs = validate_rule(rule)
    assert any("missing required property 'claim'" in e for e in errs), errs
