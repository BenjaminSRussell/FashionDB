# Beans pipeline: discover/scrape → distill → clean → filter → validate
# Usage:
#   make -C Beans pipeline URLS=test_urls.txt
#   make -C Beans pipeline-offline   # fixture JSON only (no network)

.PHONY: pipeline pipeline-offline help

URLS ?= test_urls.txt

help:
	@echo "Targets:"
	@echo "  pipeline URLS=<file>   full scrape→distill→clean→filter→validate + manifest"
	@echo "  pipeline-offline       offline fixture through distill→validate + manifest"

pipeline:
	python run.py full $(URLS)

pipeline-offline:
	python run.py distill data/fixtures data/rules_raw.json
	python -c "from clean import RuleCleaner, RuleValidationConfig; RuleCleaner(RuleValidationConfig(min_word_count=5,max_word_count=50,min_quality_score=7)).clean_rules('data/rules_raw.json','data/rules_cleaned.json')"
	python run.py filter data/rules_cleaned.json data/rules.json
	python run.py validate data/rules.json
	python -c "from run import write_run_manifest; from datetime import datetime, timezone; write_run_manifest({'started_at':datetime.now(timezone.utc).isoformat(),'input':'fixtures','status':'ok','mode':'offline'})"
