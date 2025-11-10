"""Extract fashion rules from text using MLX-LM."""

import re
import json
from typing import List, Optional

try:
    from mlx_lm import load, generate
except ImportError:
    load = None
    generate = None


SYSTEM_PROMPT = """You are a fashion expert analyzing text for specific fashion rules and advice.

Extract specific fashion rules, guidelines, or advice mentioned in the text.

Return your response as a JSON object with this EXACT structure:
{
  "has_fashion_rule": true,
  "rules": [
    {"rule_text": "Clear statement of the fashion rule", "rule_type": "fit", "quality_score": 7, "word_count": 8}
  ]
}

Rule types: fit, color, style, formality, accessories, general
Quality score: 1-10 (10 = highly specific and actionable)

Examples:
Input: "Never button the bottom button of a suit jacket"
Output: {"has_fashion_rule": true, "rules": [{"rule_text": "Never button the bottom button of a suit jacket", "rule_type": "formality", "quality_score": 9, "word_count": 9}]}

Input: "Black shoes don't go with brown belts"
Output: {"has_fashion_rule": true, "rules": [{"rule_text": "Black shoes don't go with brown belts", "rule_type": "color", "quality_score": 8, "word_count": 7}]}

Input: "Where can I buy cheap jeans?"
Output: {"has_fashion_rule": false, "rules": []}

Return ONLY valid JSON, no other text."""


class Extractor:
    def __init__(self, model_name: str = "mlx-community/Mistral-7B-Instruct-v0.2-4bit"):
        self.model_name = model_name
        self.model = None
        self.tokenizer = None
        self._load_model()

    def _load_model(self):
        """Load the MLX model for extraction."""
        if load is None or generate is None:
            raise RuntimeError("Missing mlx_lm package. Install: pip install mlx-lm")

        print(f"Loading model: {self.model_name}...")
        self.model, self.tokenizer = load(self.model_name)
        print("Model loaded!")

    def extract(self, text: str) -> List[dict]:
        """Extract fashion rules from text."""
        if not text or len(text.strip()) < 20:
            return []

        # Truncate long text
        if len(text) > 2000:
            text = text[:2000] + "..."

        prompt = self._create_prompt(text)

        try:
            response_text = generate(
                self.model,
                self.tokenizer,
                prompt=prompt,
                max_tokens=512,
                verbose=False,
            )

            result = self._extract_json(response_text)

            if result and result.get("has_fashion_rule"):
                rules = result.get("rules", [])
                # Add word_count if missing
                for rule in rules:
                    if "word_count" not in rule:
                        rule["word_count"] = len(rule.get("rule_text", "").split())
                return rules

            return []

        except Exception as e:
            print(f"Extraction error: {e}")
            return []

    def _create_prompt(self, text: str) -> str:
        """Create extraction prompt in Mistral format."""
        return f"""<s>[INST] {SYSTEM_PROMPT}

Analyze this text and extract any fashion rules or advice:

{text}

Return only valid JSON. [/INST]"""

    def _extract_json(self, text: str) -> Optional[dict]:
        """Extract JSON from model response."""
        text = text.strip()
        text = re.sub(r',\s*([}\]])', r'\1', text)

        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
        if json_match:
            cleaned = json_match.group()
            cleaned = re.sub(r',\s*([}\]])', r'\1', cleaned)
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                pass

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        return None
