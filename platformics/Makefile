SHELL := /bin/bash

FOLDER=
CONTAINER=

### DATABASE VARIABLES #################################################
LOCAL_DB_NAME= 
LOCAL_DB_SERVER= 
LOCAL_DB_USERNAME= 
LOCAL_DB_PASSWORD= 
LOCAL_DB_CONN_STRING= 

### DOCKER ENVIRONMENTAL VARS #################################################
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
	docker attach $$($(docker_compose) ps | grep $(FOLDER) | cut -d ' ' -f 1 | head -n 1) --detach-keys="ctrl-p"

.PHONY: local-status
local-status: ## Show the status of the containers in the dev environment.
	docker ps -a | grep --color=no -e '$(CONTAINER)\|$(FOLDER)'

.PHONY: local-shell
local-shell: ## Open a command shell in one of the dev containers. ex: make local-shell CONTAINER=frontend
	$(docker_compose) exec $(CONTAINER) bash

.PHONY: local-build
local-build: ## Build images
	$(docker_compose) build

.PHONY: local-rebuild
local-rebuild: local-build ## Rebuild local dev without re-importing data
	$(docker_compose) up -d

.PHONY: local-sync
local-sync: local-rebuild local-init ## Re-sync the local-environment state after modifying library deps or docker configs

.PHONY: local-stop
local-stop: ## Stop the local dev environment.
	$(docker_compose) --profile '*' stop

.PHONY: local-clean
local-clean: local-stop ## Remove everything related to the local dev environment (including db data!)
	$(docker_compose) down

.PHONY: local-seed
local-seed: ## Seed the dev db with a reasonable set of starting data.
	$(docker_compose) exec $(FOLDER) python3 scripts/seed.py

.PHONY: local-logs
local-logs: ## Tail the logs of the dev env containers. ex: make local-logs CONTAINER=backend
	$(docker_compose) logs -f $(CONTAINER)

.PHONY: fix-poetry-lock
fix-poetry-lock: ## Fix poetry lockfile after merge conflict & repairing pyproject.toml
	git checkout --theirs poetry.lock
	$(docker_compose_run) $(FOLDER) poetry lock --no-update

.PHONY: local-update-deps
local-update-deps: ## Update poetry.lock to reflect pyproject.toml file changes.
	$(docker_compose) exec $(FOLDER) poetry update

.PHONY: local-update-backend-deps
local-update-backend-deps: ## Update poetry.lock to reflect pyproject.toml file changes.
	$(docker_compose) exec backend poetry update

.PHONY: local-tests
local-tests: ## Run tests
	$(docker_compose_run) $(FOLDER) bash -c "poetry run pytest"

.PHONY: local-token
local-token: ## Copy an auth token for this local dev env to the system clipboard
	TOKEN=$$($(docker_compose_run) $(FOLDER) ../platformics/cli/generate_token.py auth generate-token 111 --project 444:admin --expiration 99999); echo '{"Authorization":"Bearer '$$TOKEN'"}' | tee >(pbcopy)

.PHONY: fix-lint
fix-lint: ## Apply linting rules to the code in this directory.
	$(docker_compose_run) $(FOLDER) black .
	$(docker_compose_run) $(FOLDER) ruff check --fix .

.PHONY: check-lint
check-lint: ## Check for bad linting
	$(docker_compose_run) $(FOLDER) black --check .
	$(docker_compose_run) $(FOLDER) ruff check .
	$(docker_compose_run) $(FOLDER) mypy .

.PHONY: local-mypy
local-mypy: ## Run type checking
	$(docker_compose) exec $(FOLDER) mypy .

.PHONY: update-cli
update-cli:  ## Update the GQL types used by the CLI
	$(docker_compose) exec $(FOLDER) python3 -m sgqlc.introspection --exclude-deprecated --exclude-description http://localhost:8042/graphql api/schema.json
	$(docker_compose) exec $(FOLDER) sgqlc-codegen schema api/schema.json cli/gql_schema.py

### GitHub Actions ###################################################
.PHONY: gha-setup
gha-setup:
	docker swarm init

### ALEMBIC #############################################
alembic-upgrade-head: ## Run alembic migrations locally
	$(docker_compose) exec $(FOLDER) alembic upgrade head 

alembic-undo-migration: ## Downgrade the latest alembic migration
	$(docker_compose) exec $(FOLDER) alembic downgrade -1

alembic-autogenerate: ## Create new alembic migrations files based on SA schema changes.
	$(docker_compose) exec $(FOLDER) alembic revision --autogenerate -m "$(MESSAGE)" --rev-id $$(date +%Y%m%d_%H%M%S)
