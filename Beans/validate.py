import json
import re
from pathlib import Path

class Validator:
    def __init__(self):
        self.min_w, self.max_w = 5, 30
        self.advice = {'always', 'never', 'should', 'must', 'avoid', 'best', 'recommend', 'ensure', 'make sure'}
        self.fashion = {'suit', 'jacket', 'pants', 'shirt', 'shoes', 'tie', 'belt', 'fit', 'style', 'wear', 'dress', 'color', 'collar', 'sleeve'}
        self.skip = [
            r'\$\d+', r'shop\s+', r'buy\s+', r'click', r'subscribe',
            r'question #\d+:', r'how to', r"i've", r"i'm", r'in this article',
            r'article title', r'\?$', r'what should you', r'which style'
        ]

    def validate(self, db_path: str) -> dict:
        data = json.loads(Path(db_path).read_text())
        rules = data.get('rules', [])

        valid, invalid = 0, 0
        issues = []

        for r in rules:
            ok, err = self._check(r)
            if ok:
                valid += 1
            else:
                invalid += 1
                if len(issues) < 10:
                    issues.append({'text': r.get('rule_text', '')[:60], 'error': err})

        return {
            'total': len(rules),
            'valid': valid,
            'invalid': invalid,
            'pass_rate': f"{valid/len(rules)*100:.1f}%" if rules else "0%",
            'sample_issues': issues
        }

    def _check(self, rule: dict) -> tuple:
        text = rule.get('rule_text', '')

        if not text or not text[0].isupper():
            return False, 'No capital start'

        if not text[-1] in '.!':
            return False, 'No punctuation'

        if '?' in text:
            return False, 'Contains question'

        wc = rule.get('word_count', len(text.split()))
        if wc < self.min_w:
            return False, f'Too short ({wc} words)'
        if wc > self.max_w:
            return False, f'Too long ({wc} words)'

        if any(re.search(p, text, re.I) for p in self.skip):
            return False, 'Prohibited content'

        low = text.lower()
        if not any(a in low for a in self.advice):
            return False, 'No advice indicator'
        if not any(f in low for f in self.fashion):
            return False, 'No fashion terms'

        capital_words = sum(1 for word in text.split() if word and word[0].isupper())
        if capital_words > wc * 0.4:
            return False, 'Too many capitals (article title)'

        return True, None

    def filter_invalid(self, db_path: str, output: str) -> dict:
        data = json.loads(Path(db_path).read_text())
        rules = data.get('rules', [])

        valid_rules = [r for r in rules if self._check(r)[0]]

        data['rules'] = valid_rules
        if 'statistics' in data:
            data['statistics']['total_rules'] = len(valid_rules)
            data['statistics']['filtered'] = len(rules) - len(valid_rules)

        Path(output).write_text(json.dumps(data, indent=2))
        return data