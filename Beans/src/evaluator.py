import json
import logging
from pathlib import Path
from typing import Dict, List, Set, Tuple
logger = logging.getLogger(__name__)


class RuleExtractorEvaluator:
    # Evaluates rule extraction logic against a labeled gold set.

    def __init__(self, gold_set_filepath: str = "data/processed/gold_set.jsonl"):
        # Load the gold set immediately so evaluation can run.
        self.gold_set_filepath = Path(gold_set_filepath)
        self.gold_set_data: List[Dict] = []
        self.labeled_sentence_count = 0
        self.unlabeled_sentence_count = 0

        self._load_gold_set_data()

    def _load_gold_set_data(self):
        # Load JSONL gold set while skipping blanks or bad lines.
        if not self.gold_set_filepath.exists():
            raise FileNotFoundError(f"Gold set not found: {self.gold_set_filepath}")

        with self.gold_set_filepath.open("r", encoding="utf-8") as gold_file:
            for line in gold_file:
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                    self.gold_set_data.append(entry)

                    if entry.get("label") is not None and entry.get("label") != "":
                        self.labeled_sentence_count += 1
                    else:
                        self.unlabeled_sentence_count += 1
                except json.JSONDecodeError:
                    continue

        logger.info(
            f"Loaded gold set: {len(self.gold_set_data)} total sentences"
        )
        logger.info(f"  Labeled: {self.labeled_sentence_count}")
        logger.info(f"  Unlabeled: {self.unlabeled_sentence_count}")

    def evaluate_rule_extractor(
        self, extractor_function, min_confidence_threshold: float = 0.0
    ) -> Dict:
        # Run the extractor on labeled sentences and report precision/recall stats.
        if self.labeled_sentence_count == 0:
            logger.warning("No labeled sentences in gold set! Cannot evaluate.")
            return {
                "error": "No labeled sentences",
                "labeled_count": 0,
                "total_count": len(self.gold_set_data),
            }

        true_positives = 0
        false_positives = 0
        true_negatives = 0
        false_negatives = 0

        predictions = []

        for item in self.gold_set_data:
            label = item.get("label")
            if label is None or label == "":
                continue

            sentence = item.get("sentence", "")
            sentence_id = item.get("id", "unknown")

            is_rule_ground_truth = self._normalize_label_to_boolean(label)

            try:
                is_rule_predicted = extractor_function(sentence)
            except Exception as error:
                logger.error(
                    f"Error evaluating sentence {sentence_id}: {error}"
                )
                continue

            if is_rule_ground_truth and is_rule_predicted:
                true_positives += 1
                predictions.append(
                    {
                        "id": sentence_id,
                        "sentence": sentence,
                        "label": "TP",
                        "ground_truth": True,
                        "predicted": True,
                    }
                )
            elif is_rule_ground_truth and not is_rule_predicted:
                false_negatives += 1
                predictions.append(
                    {
                        "id": sentence_id,
                        "sentence": sentence,
                        "label": "FN",
                        "ground_truth": True,
                        "predicted": False,
                    }
                )
            elif not is_rule_ground_truth and is_rule_predicted:
                false_positives += 1
                predictions.append(
                    {
                        "id": sentence_id,
                        "sentence": sentence,
                        "label": "FP",
                        "ground_truth": False,
                        "predicted": True,
                    }
                )
            else:  # not is_rule_ground_truth and not is_rule_predicted
                true_negatives += 1
                predictions.append(
                    {
                        "id": sentence_id,
                        "sentence": sentence,
                        "label": "TN",
                        "ground_truth": False,
                        "predicted": False,
                    }
                )

        precision = (
            true_positives / (true_positives + false_positives)
            if (true_positives + false_positives) > 0
            else 0.0
        )
        recall = (
            true_positives / (true_positives + false_negatives)
            if (true_positives + false_negatives) > 0
            else 0.0
        )
        f1_score = (
            2 * (precision * recall) / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        )
        accuracy = (true_positives + true_negatives) / (
            true_positives + true_negatives + false_positives + false_negatives
        )

        return {
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "f1": round(f1_score, 3),
            "accuracy": round(accuracy, 3),
            "confusion_matrix": {
                "true_positives": true_positives,
                "false_positives": false_positives,
                "true_negatives": true_negatives,
                "false_negatives": false_negatives,
            },
            "total_evaluated": len(predictions),
            "predictions": predictions,
        }

    def _normalize_label_to_boolean(self, label) -> bool:
        # Map varied label formats to a boolean.
        if isinstance(label, bool):
            return label
        if isinstance(label, int):
            return label == 1

        if isinstance(label, str):
            label_lower = label.lower().strip()
            return label_lower in {"rule", "yes", "y", "1", "true", "positive", "r"}

        return False

    def print_evaluation_report(self, evaluation_results: Dict):
        # Pretty-print core metrics and helpful hints.
        print("\n" + "=" * 80)
        print("EVALUATION REPORT")
        print("=" * 80)

        if "error" in evaluation_results:
            print(f"ERROR: {evaluation_results['error']}")
            print(
                f"  Labeled sentences: {evaluation_results.get('labeled_count', 0)}"
            )
            print(f"  Total sentences: {evaluation_results.get('total_count', 0)}")
            print("\nPlease label your gold set before evaluation!")
            print("Edit data/processed/gold_set.jsonl and set 'label' field to:")
            print("  - 'rule' or 'yes' or '1' for positive examples")
            print("  - 'not_rule' or 'no' or '0' for negative examples")
            return

        print(f"Total Evaluated: {evaluation_results['total_evaluated']}")
        print()
        print("METRICS:")
        print(f"  Precision: {evaluation_results['precision']:.1%}")
        print(f"  Recall:    {evaluation_results['recall']:.1%}")
        print(f"  F1 Score:  {evaluation_results['f1']:.1%}")
        print(f"  Accuracy:  {evaluation_results['accuracy']:.1%}")
        print()
        print("CONFUSION MATRIX:")
        confusion_matrix = evaluation_results["confusion_matrix"]
        print(f"  True Positives:  {confusion_matrix['true_positives']}")
        print(f"  False Positives: {confusion_matrix['false_positives']}")
        print(f"  True Negatives:  {confusion_matrix['true_negatives']}")
        print(f"  False Negatives: {confusion_matrix['false_negatives']}")

    def show_prediction_errors(
        self, evaluation_results: Dict, error_type: str = "all", max_errors_to_show: int = 10
    ):
        # Display misclassified sentences for manual review.
        predictions = evaluation_results.get("predictions", [])

        if error_type == "all":
            errors = [p for p in predictions if p["label"] in {"FP", "FN"}]
        else:
            errors = [p for p in predictions if p["label"] == error_type.upper()]

        if not errors:
            print(f"\nNo {error_type} errors found!")
            return

        print(
            f"\n{error_type.upper()} ERRORS (showing {min(max_errors_to_show, len(errors))} of {len(errors)}):"
        )
        print("=" * 80)

        for i, error in enumerate(errors[:max_errors_to_show], 1):
            print(f"\n{i}. [{error['id']}] {error['label']}")
            print(f"   Sentence: {error['sentence'][:200]}...")
            print(
                f"   Ground Truth: {error['ground_truth']} | Predicted: {error['predicted']}"
            )


def evaluate_current_rule_extraction_system():
    # Convenience helper to run the default extractor against the gold set.
    from rules_extractor import RulesExtractor

    extractor = RulesExtractor()

    def is_sentence_a_rule(sentence: str) -> bool:
        # Lightweight wrapper so the evaluator can call the extractor.
        text_lower = sentence.lower()

        has_rule_keyword = any(kw in text_lower for kw in extractor.RULE_KEYWORDS)
        if not has_rule_keyword:
            return False

        has_fashion_keyword = any(
            kw in text_lower for kw in extractor.FASHION_KEYWORDS
        )
        if not has_fashion_keyword:
            return False

        has_noise_indicator = any(
            indicator in text_lower for indicator in extractor.NOISE_INDICATORS
        )
        if has_noise_indicator:
            return False

        if len(sentence) < 30 or len(sentence) > 500:
            return False

        return True

    evaluator = RuleExtractorEvaluator()
    results = evaluator.evaluate_rule_extractor(is_sentence_a_rule)

    evaluator.print_evaluation_report(results)

    if "predictions" in results:
        print("\n" + "=" * 80)
        print("SAMPLE ERRORS")
        print("=" * 80)
        evaluator.show_prediction_errors(results, error_type="FP", max_errors_to_show=5)
        evaluator.show_prediction_errors(results, error_type="FN", max_errors_to_show=5)

    return results


def main():
    # Minimal CLI for running evaluations.
    import argparse

    parser = argparse.ArgumentParser(description="Evaluate rule extractor performance")
    parser.add_argument(
        "--gold-set",
        default="data/processed/gold_set.jsonl",
        help="Path to gold set JSONL",
    )
    parser.add_argument(
        "--show-errors", action="store_true", help="Show detailed error analysis"
    )
    parser.add_argument(
        "--error-limit", type=int, default=10, help="Maximum errors to show"
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    results = evaluate_current_rule_extraction_system()

    if args.show_errors and "predictions" in results:
        evaluator = RuleExtractorEvaluator(args.gold_set)
        print("\n" + "=" * 80)
        print("DETAILED ERROR ANALYSIS")
        print("=" * 80)
        evaluator.show_prediction_errors(
            results, error_type="all", max_errors_to_show=args.error_limit
        )


if __name__ == "__main__":
    main()
