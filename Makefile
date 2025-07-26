# Makefile for doc-builder Development

# Phony targets
.PHONY: install test clean generate regenerate-checkpoint test-debug lint

# Install the package in editable mode with test dependencies
install:
	@echo "Installing the package in editable mode with test dependencies..."
	python -m pip install -e .[test]

# Run tests and clean up afterwards
test:
	@echo "Running tests..."
	python -m pytest $(PYTEST_ARGS)

# Run tests for CI, excluding local-only tests
test-ci:
	@echo "Running CI tests..."
	python -m pytest -m "not local"

# Run linter
lint:
	@echo "Running linter..."
	python -m ruff check .

# Run tests and keep the output for inspection
test-debug:
	@echo "Running tests and keeping output in tests/tmp/..."
	@KEEP_TEST_OUTPUT=1 python -m pytest

# Clean generated files
clean:
	@echo "Cleaning generated files..."
	rm -rf generated_studies tests/tmp

# Generate a single report for development purposes
generate:
	@echo "Generating report for Study1..."
	doc-builder generate tests/data/Study1

# Regenerate the test checkpoint
regenerate-checkpoint: clean
	@echo "Regenerating test checkpoint..."
	@mkdir -p tests/tmp/checkpoint_generation
	@SOURCE_DATE_EPOCH=0 python -m src.document_generator batch tests/data --template-dir templates --output-dir tests/tmp/checkpoint_generation
	@rm -rf tests/expected_output/*
	@cp -R tests/tmp/checkpoint_generation/* tests/expected_output/
	@rm -rf tests/tmp
	@echo "Checkpoint updated."