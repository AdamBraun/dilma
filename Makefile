# Dilma – simple automation
.PHONY: test lint schema

# Re-formatting / style check
lint:
	black --check .
	ruff check .

# Validate JSONL dilemmas & tag usage
schema:
	python scripts/check_dilemmas.py

# Aggregate target the docs refer to
test: lint schema 