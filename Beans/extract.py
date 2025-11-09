import re
from typing import List, Dict

class Extractor:
    """Extracts fashion rules from web page text."""

    def __init__(self):
        self.advice_indicators = [
            r'\b(should|must|always|never|avoid|best|recommended?|essential|important)\b',
            r'\b(don\'t|do not|make sure|ensure|consider)\b',
            r'\b(wear|pair|match|combine|choose|select)\b'
        ]

        self.fashion_keywords = [
            'suit', 'jacket', 'blazer', 'pants', 'trousers', 'shirt', 'tie',
            'shoes', 'belt', 'color', 'fit', 'style', 'pattern', 'fabric',
            'dress', 'casual', 'formal', 'outfit', 'wardrobe', 'wear', 'clothing'
        ]

        self.skip_patterns = [
            r'\$\d+', r'shop\s+', r'buy\s+now', r'click\s+here',
            r'subscribe', r'newsletter', r'discount', r'sale'
        ]

    def extract(self, text: str) -> List[Dict]:
        if not text or len(text.strip()) < 50:
            return []

        sentences = self._split_sentences(text)

        rules = []
        for sentence in sentences:
            if self._is_fashion_rule(sentence):
                rule = self._create_rule(sentence)
                if rule:
                    rules.append(rule)

        rules.sort(key=lambda r: r['quality_score'], reverse=True)
        return rules[:50]

    def _split_sentences(self, text: str) -> List[str]:
        sentences = re.split(r'[.!?]\s+', text)
        return [s.strip() for s in sentences if len(s.strip()) > 20]

    def _is_fashion_rule(self, sentence: str) -> bool:
        lower_sent = sentence.lower()

        if any(re.search(pattern, sentence, re.I) for pattern in self.skip_patterns):
            return False

        has_advice = any(re.search(pattern, lower_sent, re.I) for pattern in self.advice_indicators)
        if not has_advice:
            return False

        has_fashion = any(keyword in lower_sent for keyword in self.fashion_keywords)
        if not has_fashion:
            return False

        word_count = len(sentence.split())
        if word_count < 5 or word_count > 45:
            return False

        return True

    def _create_rule(self, sentence: str) -> Dict:
        cleaned = sentence.strip()
        if not cleaned:
            return None

        if not cleaned[0].isupper():
            cleaned = cleaned[0].upper() + cleaned[1:]

        if not cleaned[-1] in '.!?':
            cleaned += '.'

        quality = self._calculate_quality(cleaned)
        rule_type = self._classify_rule(cleaned)

        return {
            'rule_text': cleaned,
            'rule_type': rule_type,
            'word_count': len(cleaned.split()),
            'quality_score': quality
        }

    def _calculate_quality(self, text: str) -> float:
        score = 0.5
        lower_text = text.lower()

        strong_advice = ['always', 'never', 'must', 'essential', 'best']
        if any(word in lower_text for word in strong_advice):
            score += 0.2

        fashion_count = sum(1 for kw in self.fashion_keywords if kw in lower_text)
        score += min(fashion_count * 0.05, 0.2)

        word_count = len(text.split())
        if word_count < 8:
            score -= 0.1
        elif word_count > 35:
            score -= 0.1
        elif 10 <= word_count <= 25:
            score += 0.1

        return max(0.0, min(1.0, score))

    def _classify_rule(self, text: str) -> str:
        lower_text = text.lower()

        if any(word in lower_text for word in ['color', 'colour', 'match', 'contrast']):
            return 'color_matching'

        if any(word in lower_text for word in ['fit', 'size', 'tailored', 'slim', 'tight', 'loose']):
            return 'fit_guidelines'

        if any(word in lower_text for word in ['formal', 'casual', 'business', 'occasion', 'event']):
            return 'occasion_specific'

        if any(word in lower_text for word in ['pair', 'combine', 'together', 'with']):
            return 'combination_advice'

        return 'general_styling'
