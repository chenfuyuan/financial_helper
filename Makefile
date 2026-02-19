.PHONY: help dev test lint format type-check ci migrate docker-up docker-down new-module architecture-check

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

dev: ## Run development server
	uvicorn app.interfaces.main:app --host 0.0.0.0 --port 8000 --reload

test: ## Run tests
	python -m pytest tests/ -v

lint: ## Run linter
	ruff check src/ tests/

format: ## Format code
	ruff format src/ tests/
	ruff check --fix src/ tests/

type-check: ## Run type checker
	mypy src/

architecture-check: ## Run architecture guards (import-linter + pytest arch tests)
	lint-imports
	python -m pytest tests/architecture/ -v

ci: ## Run same checks as CI (run before push)
	ruff check src/ tests/
	ruff format --check src/ tests/
	mypy src/
	$(MAKE) architecture-check
	python -m pytest tests/ -v

migrate: ## Run database migrations
	alembic upgrade head

migrate-create: ## Create a new migration (usage: make migrate-create msg="description")
	alembic revision --autogenerate -m "$(msg)"

docker-up: ## Start Docker services
	docker compose up -d --build

docker-down: ## Stop Docker services
	docker compose down

docker-logs: ## Tail Docker logs
	docker compose logs -f

new-module: ## Scaffold new DDD module from example (usage: make new-module name=product)
	python scripts/new_module.py "$(name)"
