# Makefile for doc-builder Development

# Phony targets
.PHONY: install test clean generate regenerate-checkpoint test-debug

# Install the package in editable mode
install:
	@echo "Installing the package in editable mode..."
	python -m pip install -e .

# Run tests and clean up afterwards
test:
	@echo "Running tests..."
	python -m pytest

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
regenerate-checkpoint:
	@echo "Regenerating test checkpoint..."
	@rm -rf tests/expected_output/*
	@SOURCE_DATE_EPOCH=0 python -m src.document_generator batch tests/data --template-dir templates --output-dir tests/expected_output
	@echo "Checkpoint updated."