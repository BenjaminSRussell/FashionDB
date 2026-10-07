"""Extract fashion rules from text using MLX-LM with sentence-transformers fallback."""

import re
import json
import logging
import platform
from pathlib import Path
from typing import List, Optional

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global flag for MLX availability
USE_MLX = False

# Try MLX-LM first (macOS)
if platform.system() == "Darwin":
    try:
        from mlx_lm import load, generate
        USE_MLX = True
        logger.info("Using MLX-LM backend")
    except ImportError:
        logger.warning("MLX-LM not available, falling back to sentence-transformers")

# Fallback to sentence-transformers
if not USE_MLX:
    try:
        from sentence_transformers import SentenceTransformer
        from sklearn.metrics.pairwise import cosine_similarity
        import numpy as np
        logger.info("Using sentence-transformers backend")
    except ImportError:
        raise RuntimeError("Neither MLX-LM nor sentence-transformers available. Install required dependencies.")


SYSTEM_PROMPT = """You are a fashion expert who analyzes fashion articles and extracts specific rules. 

IMPORTANT INSTRUCTIONS:
1. Look for sentences containing SPECIFIC fashion advice about:
   - How clothes should fit
   - What colors match with what
   - When to wear certain items
   - What combinations to avoid
   - Specific measurements or proportions
   - Clear do's and don'ts

2. Focus on sentences that:
   - Start with action words: "Always", "Never", "Make sure", "Avoid", "Choose", "Match", "Pair"
   - Give specific measurements: "should fall to", "about half an inch", "no more than"
   - State clear rules: "blue suits match with brown shoes", "belt should match your shoes"
   
3. COMPLETELY IGNORE:
   - Promotional text about the website/article
   - Navigation or menu items
   - Generic statements without specific advice
   - Marketing messages or ads
   - Links or references
   - Anything about buying or shopping

EXAMPLES OF GOOD RULES:
✓ "A suit jacket's sleeves should show about 1/4 inch of shirt cuff"
✓ "Never wear a black belt with brown shoes"
✓ "Your tie width should match your lapel width"
✓ "The bottom button of a suit jacket should always remain unbuttoned"

EXAMPLES OF BAD RULES (DO NOT EXTRACT):
✗ "Check out our style guide for more tips"
✗ "We have the best fashion advice"
✗ "Learn more about men's fashion"
✗ "Buy our style course for expert tips"

Rules must be:
- Specific and actionable
- Related to fashion, style, or clothing
- Independent of any website or platform
- Clear and direct statements

Return your response as a JSON object with this EXACT structure:
{
  "has_fashion_rule": true,
  "rules": [
    {"rule_text": "Clear statement of the fashion rule", "rule_type": "fit", "quality_score": 7, "word_count": 8}
  ]
}

Rule types: fit, color, style, formality, accessories, general
Quality score: 1-10 (10 = highly specific and actionable)

Examples of GOOD rules:
✓ "Never wear a black belt with brown shoes"
✓ "A suit jacket's sleeves should end at your wrist bone"
✓ "Match your socks to your pants, not your shoes"

Examples of BAD rules (do not extract):
✗ "Check out our style guide"
✗ "Learn more fashion tips"
✗ "Subscribe to our newsletter"
✗ "Visit our website for more"

Input: "Never button the bottom button of a suit jacket"
Output: {"has_fashion_rule": true, "rules": [{"rule_text": "Never button the bottom button of a suit jacket", "rule_type": "formality", "quality_score": 9, "word_count": 9}]}

Input: "Check out our top 10 fashion tips!"
Output: {"has_fashion_rule": false, "rules": []}

Return ONLY valid JSON, no other text."""


class Extractor:
    def __init__(self, model_name: str = "mlx-community/Mistral-7B-Instruct-v0.2-4bit"):
        self.model_name = model_name
        self.model = None
        self.tokenizer = None
        self.transformer = None
        self.use_mlx = USE_MLX  # Store the global flag locally
        self._load_model()
        
    def _load_model(self):
        """Load the appropriate model for extraction."""
        if self.use_mlx:
            try:
                logger.info(f"Loading MLX model: {self.model_name}...")
                self.model, self.tokenizer = load(self.model_name)
                logger.info("MLX model loaded successfully!")
            except Exception as e:
                logger.error(f"Failed to load MLX model: {e}")
                self.use_mlx = False
                
        if not USE_MLX:
            try:
                logger.info("Loading sentence-transformer model...")
                self.transformer = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info("Sentence transformer model loaded successfully!")
            except Exception as e:
                raise RuntimeError(f"Failed to load sentence-transformer model: {e}")

    def extract(self, text: str) -> List[dict]:
        """Extract fashion rules from text using either MLX-LM or sentence-transformers."""
        if not text or len(text.strip()) < 20:
            return []

        # Truncate long text
        if len(text) > 2000:
            text = text[:2000] + "..."

        try:
            if self.use_mlx and self.model and self.tokenizer:
                return self._extract_mlx(text)
            elif self.transformer:
                return self._extract_transformer(text)
            else:
                raise RuntimeError("No model available for extraction")
        except Exception as e:
            logger.error(f"Extraction error: {e}")
            return []

    def _extract_mlx(self, text: str) -> List[dict]:
        """Extract rules using MLX-LM."""
        prompt = self._create_prompt(text)
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
            for rule in rules:
                if "word_count" not in rule:
                    rule["word_count"] = len(rule.get("rule_text", "").split())
            return rules
        return []

    def _extract_transformer(self, text: str) -> List[dict]:
        """Extract rules using sentence-transformers."""
        # Split text into sentences
        sentences = [s.strip() for s in re.split(r'[.!?]+', text) if len(s.strip()) > 20]
        
        if not sentences:
            return []
            
        # Fashion-related keywords for filtering
        fashion_keywords = [
            "wear", "dress", "outfit", "style", "fashion", "clothes",
            "shoes", "accessories", "fit", "color", "pattern", "formal",
            "casual", "match", "coordinate", "combination"
        ]
        
        # Encode sentences
        embeddings = self.transformer.encode(sentences)
        
        # Create rule embeddings
        rule_templates = [
            "This is a clear fashion rule or guideline",
            "This describes how to wear clothing properly",
            "This explains fashion dos and don'ts",
        ]
        rule_embeddings = self.transformer.encode(rule_templates)
        
        rules = []
        for i, sentence in enumerate(sentences):
            # Check if sentence contains fashion keywords
            if not any(keyword in sentence.lower() for keyword in fashion_keywords):
                continue
                
            # Calculate similarity with rule templates
            similarity = cosine_similarity(
                embeddings[i].reshape(1, -1),
                rule_embeddings
            ).max()
            
            if similarity > 0.5:  # Threshold for rule detection
                rule_type = self._determine_rule_type(sentence)
                rules.append({
                    "rule_text": sentence,
                    "rule_type": rule_type,
                    "quality_score": int(similarity * 10),
                    "word_count": len(sentence.split())
                })
        
        return rules

    def _determine_rule_type(self, text: str) -> str:
        """Determine the type of fashion rule based on keywords."""
        text = text.lower()
        if any(word in text for word in ["fit", "size", "tight", "loose"]):
            return "fit"
        elif any(word in text for word in ["color", "colour", "pattern", "print"]):
            return "color"
        elif any(word in text for word in ["formal", "casual", "business", "dress code"]):
            return "formality"
        elif any(word in text for word in ["accessory", "accessories", "jewelry", "watch"]):
            return "accessories"
        elif any(word in text for word in ["style", "trend", "fashion"]):
            return "style"
        return "general"

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
