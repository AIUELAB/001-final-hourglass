# Makefile for Claude Code Template MCP
# 2025年版 - 最適化された開発コマンド

.PHONY: help
help: ## Show this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

.PHONY: install
install: ## Install all dependencies
	python -m pip install --upgrade pip
	pip install -r requirements.txt
	pre-commit install

.PHONY: format
format: ## Format code with Ruff
	ruff format src tests

.PHONY: lint
lint: ## Lint code with Ruff
	ruff check src tests --fix

.PHONY: type
type: ## Type check with mypy
	mypy src

.PHONY: test
test: ## Run tests
	pytest tests -v

.PHONY: coverage
coverage: ## Run tests with coverage
	pytest tests --cov=src --cov-report=html --cov-report=term

.PHONY: security
security: ## Run security checks
	bandit -r src/
	pip-audit
	safety check

.PHONY: pre-commit
pre-commit: ## Run all pre-commit hooks
	pre-commit run --all-files

.PHONY: clean
clean: ## Clean build artifacts
	rm -rf build dist *.egg-info
	rm -rf .pytest_cache .mypy_cache .ruff_cache
	rm -rf htmlcov .coverage
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

.PHONY: docs
docs: ## Serve documentation locally
	mkdocs serve

.PHONY: docs-build
docs-build: ## Build documentation
	mkdocs build

.PHONY: ollama
ollama: ## Setup Ollama integration
	./scripts/setup-ollama.sh

.PHONY: ollama-test
ollama-test: ## Test Ollama integration
	python src/ollama_integration.py

.PHONY: all
all: format lint type test ## Run all checks

.PHONY: ci
ci: lint type test security ## Run CI checks

.PHONY: ci-full
ci-full: ## Run full CI pipeline (same as GitHub Actions)
	@echo "🔍 Running full CI pipeline..."
	@echo ""
	@echo "📋 Step 1: Pre-commit hooks"
	pre-commit run --all-files
	@echo ""
	@echo "📋 Step 2: Ruff format check"
	ruff format --check . --exclude "*/_archived/*" --exclude "archive/*"
	@echo ""
	@echo "📋 Step 3: Ruff lint"
	ruff check . --exclude "*/_archived/*" --exclude "archive/*"
	@echo ""
	@echo "📋 Step 4: Type check"
	mypy src/ --ignore-missing-imports
	@echo ""
	@echo "📋 Step 5: Tests"
	pytest tests/ -v
	@echo ""
	@echo "📋 Step 6: Security - Bandit"
	bandit -r src/ -f json -o bandit-report.json
	@echo ""
	@echo "📋 Step 7: Security - pip-audit"
	pip-audit -r requirements.txt --desc
	@echo ""
	@echo "📋 Step 8: Security - Safety"
	safety check -r requirements.txt --json
	@echo ""
	@echo "✅ All CI checks passed!"

.PHONY: ci-quick
ci-quick: ## Run quick CI checks (no security)
	@echo "🔍 Running quick CI..."
	pre-commit run --all-files
	ruff format --check . --exclude "*/_archived/*" --exclude "archive/*"
	ruff check . --exclude "*/_archived/*" --exclude "archive/*"
	pytest tests/ -v
	@echo "✅ Quick CI passed!"
