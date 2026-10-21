PYTHON  ?= python3.13
VENV    ?= .venv
BIN     := $(VENV)/bin
COMPOSE ?= docker-compose

.DEFAULT_GOAL := help
.PHONY: help install css watch-css dev seed test clean \
        docker-build docker-up docker-down docker-logs docker-seed docker-shell

help: ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

# --- Local development ---

$(BIN)/flask: requirements.txt
	$(PYTHON) -m venv $(VENV)
	$(BIN)/pip install -r requirements.txt pytest
	@touch $@

node_modules: package.json package-lock.json
	npm ci
	@touch $@

install: $(BIN)/flask node_modules ## Create venv, install Python and Node dependencies

css: node_modules ## Build Tailwind CSS
	npm run build:css

watch-css: node_modules ## Rebuild Tailwind CSS on change
	npm run watch:css

dev: install css ## Run Flask dev server on :5000
	$(BIN)/flask --app app run --debug

seed: install ## Add sample entries to configured storage
	$(BIN)/flask --app app seed

test: install ## Run the test suite
	$(BIN)/python -m pytest

clean: ## Remove caches and build artifacts
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf .pytest_cache

# --- Docker ---

docker-build: ## Build the Docker image
	$(COMPOSE) build

docker-up: ## Build and start the app on :8000
	$(COMPOSE) up -d --build

docker-down: ## Stop and remove containers
	$(COMPOSE) down

docker-logs: ## Follow container logs
	$(COMPOSE) logs -f web

docker-seed: ## Add sample entries inside the running container
	$(COMPOSE) exec web flask --app app seed

docker-shell: ## Open a shell in the running container
	$(COMPOSE) exec web sh
