SHELL := /bin/bash

FOLDER = /app
CONTAINER=dev-app
TEST_CONTAINER=test-app
BUILD_CONTAINER=platformics

### DATABASE VARIABLES #################################################
LOCAL_DB_NAME=platformics
LOCAL_DB_SERVER=localhost:5432
LOCAL_DB_USERNAME=postgres
LOCAL_DB_PASSWORD=password_postgres
LOCAL_DB_CONN_STRING = postgresql://$(LOCAL_DB_USERNAME):$(LOCAL_DB_PASSWORD)@$(LOCAL_DB_SERVER)/$(LOCAL_DB_NAME)

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

.PHONY: rm-pycache
rm-pycache: ## remove all __pycache__ files (run if encountering issues with pycharm debugger (containers exiting prematurely))
	find . -name '__pycache__' | xargs rm -rf

### DOCKER LOCAL DEV #########################################
.PHONY: debugger
debugger: ## Attach to the backend service (useful for pdb)
	docker attach $$($(docker_compose) ps | grep $(CONTAINER) | cut -d ' ' -f 1 | head -n 1) --detach-keys="ctrl-p"

.PHONY: stop
local-stop: ## Stop the local dev environment.
	$(docker_compose) --profile '*' stop

.PHONY: local-seed
local-seed: ## Seed the dev db with a reasonable set of starting data.
	$(docker_compose) exec $(CONTAINER) python3 scripts/seed.py

.PHONY: pgconsole
pgconsole: ## Connect to the local postgres database.
	$(docker_compose) exec platformics-db psql "$(LOCAL_DB_CONN_STRING)"

.PHONY: logs
local-logs: ## Tail the logs of the dev env containers. ex: make local-logs CONTAINER=backend
	$(docker_compose) logs -f $(CONTAINER)

.PHONY: fix-poetry-lock
fix-poetry-lock: ## Fix poetry lockfile after merge conflict & repairing pyproject.toml
	git checkout --theirs poetry.lock
	$(docker_compose_run) $(CONTAINER) poetry lock --no-update

.PHONY: local-update-deps
local-update-deps: ## Update poetry.lock to reflect pyproject.toml file changes.
	$(docker_compose) exec $(CONTAINER) poetry update

.PHONY: local-token
local-token: ## Copy an auth token for this local dev env to the system clipboard
	TOKEN=$$($(docker_compose_run) -w /platformics $(CONTAINER) python3 platformics/cli/main.py auth generate-token 111 --project 444:admin --expiration 99999); echo '{"Authorization":"Bearer '$$TOKEN'"}' | tee >(pbcopy)

.PHONY: check-lint
check-lint: ## Check for bad linting
	$(docker_compose_run) $(CONTAINER) black --check .
	$(docker_compose_run) $(CONTAINER) ruff check .
	$(docker_compose_run) $(CONTAINER) mypy .

.PHONY: update-cli
update-cli:  ## Update the GQL types used by the CLI
	$(docker_compose) exec $(CONTAINER) python3 -m sgqlc.introspection --exclude-deprecated --exclude-description http://localhost:8042/graphql api/schema.json
	$(docker_compose) exec $(CONTAINER) sgqlc-codegen schema api/schema.json cli/gql_schema.py

.PHONY: codegen-tests
codegen-tests: codegen  ## Run tests
	$(docker_compose) up -d
	$(docker_compose) run -v platformics api generate --schemafile /platformics/test_app/schema/test_app.yaml --output-prefix /platformics/test_app/
	$(docker_compose_run) $(CONTAINER) black .
	$(docker_compose_run) $(CONTAINER) ruff check --fix  .
	$(docker_compose_run) $(CONTAINER) pytest

### GitHub Actions ###################################################
.PHONY: gha-setup
gha-setup:
	docker swarm init

### ALEMBIC #############################################
alembic-upgrade-head: ## Run alembic migrations locally
	$(docker_compose) run $(CONTAINER) alembic upgrade head 

alembic-undo-migration: ## Downgrade the latest alembic migration
	$(docker_compose) run $(CONTAINER) alembic downgrade -1

alembic-autogenerate: ## Create new alembic migrations files based on SA schema changes.
	$(docker_compose) run $(CONTAINER) alembic revision --autogenerate -m "autogenerated" --rev-id $$(date +%Y%m%d_%H%M%S)

.PHONY: build
build:
	rm -rf dist/*.whl
	poetry build
	docker compose build

.PHONY: init
init:
	#rm -rf dist/*.whl
	#poetry build
	#docker compose --profile dev build

	docker compose --profile dev up -d
	$(docker_compose_run) $(CONTAINER) python3 platformics/cli/main.py api generate --schemafile /app/schema/test_app.yaml --output-prefix /app/
	$(MAKE) alembic-autogenerate
	$(MAKE) alembic-upgrade-head
	$(docker_compose_run) $(CONTAINER) black .
	# $(docker_compose_run) $(CONTAINER) ruff check --fix .
	$(docker_compose_run) $(CONTAINER) sh -c 'strawberry export-schema main:schema > /app/api/schema.graphql'
	sleep 5 # wait for the app to reload after having files updated.
	docker compose --profile dev up -d
	docker compose exec $(CONTAINER) python3 -m sgqlc.introspection --exclude-deprecated --exclude-description http://localhost:9009/graphql api/schema.json

.PHONY: clean
clean:
	rm -rf dist
	rm -rf test_app/api
	rm -rf test_app/cerbos
	rm -rf test_app/support
	rm -rf test_app/database
	docker compose --profile '*' down

.PHONY: test
test: build
	docker compose --profile test build
	docker compose --profile test up -d
	docker compose exec $(TEST_CONTAINER) pytest -vvv

.PHONY: dev
dev: build
	docker compose --profile dev build
	docker compose --profile dev up -d
	docker compose exec $(CONTAINER) pytest -vvv
