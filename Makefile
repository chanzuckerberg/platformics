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
codegen: build-base ## Run codegen to convert the LinkML schema to a GQL API
	$(docker_compose_run) $(BUILD_CONTAINER) api generate --schemafile ./schema/schema.yaml --output-prefix .

.PHONY: rm-pycache
rm-pycache: ## remove all __pycache__ files (run if encountering issues with pycharm debugger (containers exiting prematurely))
	find . -name '__pycache__' | xargs rm -rf

### DOCKER LOCAL DEV #########################################
.PHONY: start
start: ## Start the local dev environment.
	$(MAKE_TEST_APP) start || true
	cd test_app; docker compose stop graphql-api
	$(docker_compose) start

.PHONY: stop
stop: ## Stop the local dev environment.
	$(docker_compose) stop
	$(MAKE_TEST_APP) stop

.PHONY: fix-poetry-lock
fix-poetry-lock: ## Fix poetry lockfile after merge conflict & repairing pyproject.toml
	git checkout --theirs poetry.lock
	$(docker_compose_run) $(CONTAINER) poetry lock --no-update

.PHONY: update-python-deps
update-python-deps: ## Update poetry.lock to reflect pyproject.toml file changes.
	$(docker_compose) exec $(CONTAINER) poetry update

.PHONY: check-lint
lint: ## Check for / fix bad linting
	pre-commit run --all-files

.PHONY: codegen-tests
codegen-tests: codegen  ## Run tests
	$(docker_compose) up -d
	$(docker_compose_run) -v platformics api generate --schemafile /app/schema/test_app.yaml --output-prefix /app
	$(docker_compose_run) $(CONTAINER) black .
	$(docker_compose_run) $(CONTAINER) ruff check --fix  .
	$(docker_compose_run) $(CONTAINER) pytest

### GitHub Actions ###################################################
.PHONY: gha-setup
gha-setup: ## Set up the environment in CI
	docker swarm init
	touch test_app/.moto_recording

.PHONY: build-base ## Build the base docker image
build-base:
	rm -rf dist/*.whl
	poetry build
	# Export poetry dependency list as a requirements.txt, which makes Docker builds
	# faster by not having to reinstall all dependencies every time we build a new wheel.
	poetry export --without-hashes --format=requirements.txt > requirements.txt
	$(docker_compose) build
	rm requirements.txt

.PHONY: build ## Build the base docker image and the test app docker image
build: build-base
	$(MAKE_TEST_APP) build

.PHONY: dev ## Launch a container suitable for developing the platformics library
dev:
	$(MAKE_TEST_APP) init
	cd test_app; docker compose stop graphql-api
	docker compose up -d

.PHONY: clean
clean: ## Remove all build artifacts
	rm -rf dist
	rm -rf test_app/.moto_recording
	$(docker_compose) down
	$(MAKE_TEST_APP) clean

.PHONY: %
%: ## Forward all other targets to the test app
	$(MAKE_TEST_APP) $@
