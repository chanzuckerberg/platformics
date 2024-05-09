SHELL := /bin/bash

FOLDER = /app
CONTAINER=dev-app
TEST_CONTAINER=test-app
BUILD_CONTAINER=platformics

MAKE_TEST_APP=$(MAKE) -C test_app

### DOCKER ENV VARS #################################################
export DOCKER_BUILDKIT:=1
export COMPOSE_DOCKER_CLI_BUILD:=1
export docker_compose:=docker compose
export docker_compose_run:=docker compose run --rm

### HELPFUL #################################################
.PHONY: help
help: ## display help for this makefile
	@echo "### SHARED FUNCTIONS ###"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
	@echo "### SHARED FUNCTIONS END ###"

.PHONY: codegen
codegen:
	$(MAKE_TEST_APP) codegen

.PHONY: rm-pycache
rm-pycache: ## remove all __pycache__ files (run if encountering issues with pycharm debugger (containers exiting prematurely))
	find . -name '__pycache__' | xargs rm -rf

### DOCKER LOCAL DEV #########################################
.PHONY: start
start: ## Start the local dev environment.
	$(docker_compose) start
	$(MAKE_TEST_APP) start

.PHONY: stop
stop: ## Stop the local dev environment.
	$(docker_compose) --profile '*' stop
	$(MAKE_TEST_APP) stop

.PHONY: fix-poetry-lock
fix-poetry-lock: ## Fix poetry lockfile after merge conflict & repairing pyproject.toml
	git checkout --theirs poetry.lock
	$(docker_compose_run) $(CONTAINER) poetry lock --no-update

.PHONY: update-python-deps
update-python-deps: ## Update poetry.lock to reflect pyproject.toml file changes.
	$(docker_compose) exec $(CONTAINER) poetry update

.PHONY: check-lint
check-lint: ## Check for bad linting
	$(docker_compose_run) $(CONTAINER) black --check .
	$(docker_compose_run) $(CONTAINER) ruff check .
	$(docker_compose_run) $(CONTAINER) mypy .

.PHONY: codegen-tests
codegen-tests: codegen  ## Run tests
	$(docker_compose) up -d
	$(docker_compose) run -v platformics api generate --schemafile /app/schema/test_app.yaml --output-prefix /app
	$(docker_compose_run) $(CONTAINER) black .
	$(docker_compose_run) $(CONTAINER) ruff check --fix  .
	$(docker_compose_run) $(CONTAINER) pytest

### GitHub Actions ###################################################
.PHONY: gha-setup
gha-setup:
	docker swarm init


.PHONY: build
build:
	rm -rf dist/*.whl
	poetry build
	$(docker_compose) build
	$(MAKE) -C test_app build

.PHONY: init
init:
	docker compose up -d
	$(MAKE_TEST_APP) init

.PHONY: clean
clean:
	rm -rf dist
	$(docker_compose) --profile '*' down
	$(MAKE_TEST_APP) clean

.PHONY: dev
dev: build
	$(docker_compose) --profile '*' build
	$(docker_compose) --profile dev up -d
	$(docker_compose) exec $(CONTAINER) pytest -vvv

.PHONY: %
%: ## Forward all other targets to the test app
	$(MAKE_TEST_APP) -c test_app $@
