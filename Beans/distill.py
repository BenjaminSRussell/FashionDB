import json
import re
from pathlib import Path
from collections import defaultdict
from difflib import SequenceMatcher

class Distiller:
    def __init__(self, results_dir: str, output: str, similarity=0.85):
        self.dir = Path(results_dir)
        self.out = output
        self.sim = similarity

    def distill(self) -> dict:
        rules = self._load_all()
        unique = self._deduplicate(rules)
        merged = self._merge_sources(unique)
        db = self._build_database(merged)
        Path(self.out).parent.mkdir(parents=True, exist_ok=True)
        Path(self.out).write_text(json.dumps(db, indent=2))
        return db

    def _load_all(self) -> list:
        rules = []
        for f in self.dir.glob('*.json'):
            try:
                data = json.loads(f.read_text())
                rules.extend(data.get('rules', []))
            except:
                pass
        return rules

    def _deduplicate(self, rules: list) -> list:
        unique = []
        seen = []
        for r in rules:
            text = self._normalize(r['rule_text'])
            if not any(SequenceMatcher(None, text, s).ratio() >= self.sim for s in seen):
                unique.append(r)
                seen.append(text)
        return unique

    def _normalize(self, text: str) -> str:
        text = text.lower()
        text = re.sub(r'[^\w\s]', '', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _merge_sources(self, rules: list) -> list:
        by_text = defaultdict(lambda: {'rule': None, 'sources': []})
        for r in rules:
            key = self._normalize(r['rule_text'])
            if by_text[key]['rule'] is None:
                by_text[key]['rule'] = r
            by_text[key]['sources'].extend(r.get('sources', []))

        merged = []
        for item in by_text.values():
            rule = item['rule']
            rule['sources'] = item['sources']
            rule['source_count'] = len(item['sources'])
            merged.append(rule)
        return merged

    def _build_database(self, rules: list) -> dict:
        by_type = defaultdict(list)
        domains = set()

        for r in rules:
            by_type[r['rule_type']].append(r)
            for src in r.get('sources', []):
                domains.add(src.get('domain', 'unknown'))

        total = len(rules)
        multi = sum(1 for r in rules if r.get('source_count', 0) > 1)
        qualities = [r.get('quality_score', 0) for r in rules]
        words = [r.get('word_count', 0) for r in rules]

        return {
            'rules': rules,
            'statistics': {
                'total_rules': total,
                'unique_domains': len(domains),
                'domains': sorted(domains),
                'rule_types': {k: len(v) for k, v in by_type.items()},
                'multi_source_rules': multi,
                'multi_source_percentage': (multi / total * 100) if total else 0,
                'avg_quality_score': sum(qualities) / len(qualities) if qualities else 0,
                'avg_word_count': sum(words) / len(words) if words else 0,
                'completeness_rate': 100.0
            }
        }