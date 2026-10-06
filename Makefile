PROJECT ?= devops-template
COMPOSE := docker compose -p $(PROJECT)
PYTHON  ?= python3

.DEFAULT_GOAL := help
.PHONY: help env up down logs ps test lint fmt backup backups restore clean

help: ## Show available targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  %-10s %s\n", $$1, $$2}'

env: ## Create .env from .env.example (if missing)
	@test -f .env || (cp .env.example .env && echo "Created .env - change the passwords!")

up: env ## Build and start the whole stack
	$(COMPOSE) up -d --build
	$(COMPOSE) ps

down: ## Stop the stack (data volumes are kept)
	$(COMPOSE) down

logs: ## Follow logs (make logs s=app for one service)
	$(COMPOSE) logs -f --tail=100 $(s)

ps: ## Show service status
	$(COMPOSE) ps

test: ## Run unit/API tests (SQLite, no Docker needed)
	$(PYTHON) -m pytest

lint: ## Run ruff linter and formatter check
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .

fmt: ## Auto-fix lint issues and format code
	$(PYTHON) -m ruff check --fix .
	$(PYTHON) -m ruff format .

backup: ## Make a database dump right now
	$(COMPOSE) exec backup /bin/sh /usr/local/bin/backup.sh once

backups: ## List available dumps
	$(COMPOSE) exec backup ls -lh /backups

restore: ## Restore a dump: make restore [f=app_YYYYmmddTHHMMSSZ.dump] (default: latest)
	COMPOSE="$(COMPOSE)" ./scripts/restore.sh $(f)

clean: ## Stop the stack and DELETE all volumes (database, metrics, backups)
	$(COMPOSE) down -v
