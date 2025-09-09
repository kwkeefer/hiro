.PHONY: help dev install test test-unit test-integration test-cov lint format typecheck clean build run

PYTHON := python3.12
PACKAGE := code_mcp
SRC_DIR := src/$(PACKAGE)
TEST_DIR := tests

help: ## Show this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

dev: ## Set up development environment
	uv sync --all-extras
	uv run pre-commit install
	@echo "Development environment ready!"

install: ## Install the package in production mode
	uv sync

test: ## Run all tests
	uv run pytest $(TEST_DIR) -v

test-unit: ## Run unit tests only
	uv run pytest $(TEST_DIR) -v -m unit

test-integration: ## Run integration tests only
	uv run pytest $(TEST_DIR) -v -m integration

test-cov: ## Run tests with coverage report
	uv run pytest $(TEST_DIR) --cov=$(PACKAGE) --cov-report=term-missing --cov-report=html

lint: ## Run linting checks
	uv run ruff check $(SRC_DIR) $(TEST_DIR)

format: ## Format code with ruff
	uv run ruff format $(SRC_DIR) $(TEST_DIR)
	uv run ruff check --fix $(SRC_DIR) $(TEST_DIR)

typecheck: ## Run type checking with mypy
	uv run mypy --strict --ignore-missing-imports $(SRC_DIR)

pre-commit: ## Run all pre-commit hooks on all files
	uv run pre-commit run --all-files

pre-commit-install: ## Install pre-commit hooks
	uv run pre-commit install

sync-ai: ## Update .ai/ and .claude/ configuration from template
	uv run scripts/update_ai_config.py

clean: ## Clean up generated files
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build: clean ## Build distribution packages
	uv build

run: ## Run the CLI application
	uv run code_mcp

docker-build: ## Build Docker image
	docker build -t code_mcp:latest .

docker-run: ## Run Docker container
	docker run --rm -it code_mcp:latest

docker-compose-up: ## Start services with docker-compose
	docker-compose up -d

docker-compose-down: ## Stop services with docker-compose
	docker-compose down
