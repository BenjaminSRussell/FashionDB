"""
Rule Cleaning and Validation Tool for Fashion Rules.
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Any
import logging
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class RuleValidationConfig:
    min_word_count: int = 5
    max_word_count: int = 50
    min_quality_score: int = 7
    promotional_phrases: List[str] = None
    navigational_phrases: List[str] = None
    required_keywords: List[str] = None
    
    def __post_init__(self):
        # Promotional content patterns
        self.promotional_phrases = [
            r"check out",
            r"discover",
            r"learn more",
            r"sign up",
            r"subscribe",
            r"podcast",
            r"newsletter",
            r"article",
            r"click here",
            r"visit",
            r"website",
            r"blog",
            r"download",
            r"free",
            r"trial",
            r"today",
            r"shop now",
            r"buy",
            r"purchase",
            r"\™",  # Trademark symbol
            r"\®",  # Registered trademark
        ]
        
        # Navigation-related patterns
        self.navigational_phrases = [
            r"menu",
            r"navigation",
            r"search",
            r"home",
            r"about",
            r"contact",
            r"page",
            r"section",
        ]
        
        # Fashion rule keywords (at least one should be present)
        self.required_keywords = [
            "wear", "dress", "match", "pair", "combine", "avoid",
            "choose", "fit", "style", "coordinate", "color",
            "pattern", "fabric", "material", "accessory", "accessories",
            "suit", "shirt", "pants", "shoes", "outfit",
            "formal", "casual", "business", "occasion"
        ]

class RuleCleaner:
    def __init__(self, config: RuleValidationConfig = None):
        self.config = config or RuleValidationConfig()
    
    def clean_rules(self, input_file: str, output_file: str = None) -> Dict[str, Any]:
        """Clean and validate fashion rules from input file."""
        if not Path(input_file).exists():
            raise FileNotFoundError(f"Input file not found: {input_file}")
        
        # Load rules
        with open(input_file, 'r') as f:
            data = json.load(f)
        
        original_count = len(data.get('rules', []))
        logger.info(f"Processing {original_count} rules...")
        
        # Clean rules
        valid_rules = []
        rejected_rules = []
        
        for rule in data.get('rules', []):
            result = self.validate_rule(rule)
            if result['valid']:
                valid_rules.append(rule)
            else:
                rejected_rules.append({
                    'rule': rule,
                    'reasons': result['reasons']
                })
        
        # Update statistics
        stats = data.get('statistics', {})
        stats.update({
            'original_count': original_count,
            'valid_count': len(valid_rules),
            'rejected_count': len(rejected_rules),
            'validation_rate': round(len(valid_rules) / original_count * 100, 2) if original_count else 0
        })
        
        # Prepare output
        output_data = {
            'rules': valid_rules,
            'statistics': stats,
            'rejected_rules': rejected_rules
        }
        
        # Save if output file specified
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(output_data, f, indent=2)
            logger.info(f"Saved cleaned rules to: {output_file}")
        
        # Print summary
        self._print_summary(output_data)
        return output_data
    
    def validate_rule(self, rule: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a single rule and return validation result."""
        text = rule.get('rule_text', '').lower()
        reasons = []
        
        # Check word count
        word_count = len(text.split())
        if word_count < self.config.min_word_count:
            reasons.append(f"Too short: {word_count} words")
        if word_count > self.config.max_word_count:
            reasons.append(f"Too long: {word_count} words")
        
        # Check quality score
        quality_score = rule.get('quality_score', 0)
        if quality_score < self.config.min_quality_score:
            reasons.append(f"Low quality score: {quality_score}")
        
        # Check for promotional content
        if any(re.search(pattern, text, re.IGNORECASE) for pattern in self.config.promotional_phrases):
            reasons.append("Contains promotional content")
        
        # Check for navigational content
        if any(re.search(pattern, text, re.IGNORECASE) for pattern in self.config.navigational_phrases):
            reasons.append("Contains navigational content")
        
        # Check for required keywords
        if not any(keyword in text for keyword in self.config.required_keywords):
            reasons.append("No fashion-related keywords found")
        
        # Additional checks for actual advice content
        if not any(word in text for word in ["should", "must", "avoid", "always", "never", "try", "consider", "recommended"]):
            reasons.append("No advice indicators found")
        
        return {
            'valid': len(reasons) == 0,
            'reasons': reasons
        }
    
    def _print_summary(self, data: Dict[str, Any]):
        """Print summary of cleaning results."""
        stats = data['statistics']
        logger.info("\n=== Rule Cleaning Summary ===")
        logger.info(f"Original rules: {stats['original_count']}")
        logger.info(f"Valid rules: {stats['valid_count']}")
        logger.info(f"Rejected rules: {stats['rejected_count']}")
        logger.info(f"Validation rate: {stats['validation_rate']}%")
        
        if data['rejected_rules']:
            logger.info("\nSample rejected rules and reasons:")
            for rejected in data['rejected_rules'][:3]:
                logger.info(f"\nRule: {rejected['rule']['rule_text']}")
                logger.info(f"Reasons: {', '.join(rejected['reasons'])}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Clean and validate fashion rules")
    parser.add_argument("input_file", help="Input JSON file containing rules")
    parser.add_argument("--output", "-o", help="Output file for cleaned rules")
    parser.add_argument("--min-words", type=int, default=5, help="Minimum word count")
    parser.add_argument("--max-words", type=int, default=50, help="Maximum word count")
    parser.add_argument("--min-quality", type=int, default=7, help="Minimum quality score")
    
    args = parser.parse_args()
    
    config = RuleValidationConfig(
        min_word_count=args.min_words,
        max_word_count=args.max_words,
        min_quality_score=args.min_quality
    )
    
    cleaner = RuleCleaner(config)
    cleaner.clean_rules(args.input_file, args.output)

if __name__ == "__main__":
    main()