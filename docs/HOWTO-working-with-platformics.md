# How To: Working with Platformics

## Structure

### Platformics
Notable files and subdirectories:
* `api/` - base code and utilities for setting up API
  * `core/`
    * `deps.py` - dependencies injected to FastAPI endpoints
    * `query_builder.py` - functions for querying DB given GraphQL queries
    * `gql_loaders.py` - dataloaders for relationships to avoid GQL N+1 queries
    * `strawberry_extensions.py` - extensions to apply dependencies to resolvers
  * `types/`
    * `entities.py` - base entity code
  * `files.py` - GQL types, mutations, queries for files
* `codegen/`
  * `lib/linkml_wrappers.py` - convenience functions for converting LinkML to generated code
  * `templates/` - all Jinja templates for codegen. Entity-related templates can be overridden with [custom templates](https://github.com/chanzuckerberg/platformics/tree/main/platformics/docs/HOWTO-customize-templates.md). 
  * `generator.py` - script handling all logic of applying Jinja templates to LinkML schema to generate code
* `database/`
  * `models/`
    * `base.py` - SQLAlchemy model for base entity
    * `file.py` - SQLAlchemy model and methods for file
  * `connect.py` - functions for connecting to database
* `support/` - miscellaneous support enums, functions for files
* `test_infra/` - contains base entity and file factories
* `settings.py` - config variables using [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)


### Test app
Notable files and subdirectories:
* `api/` - entrypoint for GQL API service
  * `helpers/` - generated GQL types and helper functions for GROUPBY queries
  * `types/` - generated GQL types 
  * `validators/` - generated Pydantic validators for create and update inputs
  * `mutations.py` - generated mutations (create, update, delete) for each entity type
  * `queries.py` - generated queries (list and aggregate) for each entity type
  * `schema.graphql` - GQL format schema
  * `schema.json` - JSON format schema
* `cerbos/` - generated access policies for user actions for each entity type
* `database/` - code related to establishing DB connections / sessions
  * `migrations/` - alembic migrations
  * `models/` - generated SQLAlchemy models 
* `schema/`
  * `schema.yaml` - LinkML schema used to codegen entity-related files
* `test_infra/`
  * `factories/` - FactoryBoy factories generated for each entity type
* `tests/` - your custom tests (not codegenned)
* `etc/` - some basic setup configuration

## Containers
There are two main ways of running the test app depending on what kind of development you're doing: making changes in the test app only, and making changes to the core platformics library.

To develop in the test app, `make init` will build the `platformics` image from the latest base image and start up the test app listening on port 9009. Changes within the `platformics` repo will not be picked up unless the image is rebuilt.

Containers (`test_app/docker-compose.yml`)
* `motoserver`: mock of S3 services to run test app entirely locally for development
* `cerbos`: resource authorization
* `platformics-db`: Postgres database
* `graphql-api`: API

When developing on `platformics` itself, running `make dev` will start all of the above containers, then stop the `graphql-api` container and start a new `dev-app` compose service. 
The compose service called `dev-app` has the `platformics` directory in this repo mounted inside the `test_app` application as a sub-module, so it can be edited directly and be debugged via the VSCode debugger.
`graphql-api` and `dev-app` share a port, so the `graphql-api` container is stopped before starting the `dev-app` container.


For either of these two flows, the main app will be listening on port 9009 and debugging sessions will listen on port 9008.


## Debugging

### Using VSCode debugger
1. Install the `Dev Containers` extension for vscode
2. Open a new VSCode window in your api directory. It will read the `.devcontainer/devcontainer.json` configuration and prompt you to reopen the directory in a container (lower right side of the screen). Click "Reopen in container"
3. Click the "Run and Debug" icon in the icon bar on the right side of the VSCode window (or ctrl+shift+d). Then click the "start debugging" icon at the top of the run and debug panel (or press F5). This will launch a secondary instance of the API service that listens on port 9008.
4. Set all the breakpoints you want. Browse to the api at http://localhost:9008/graphql to trigger them. Remember that the application restarts when files change, so you'll have to start and stop the debugger to pick up any changes you make!


### Queries
To view SQL logs for queries, set `DB_ECHO=true` in `docker-compose.yml`. Run `make start` or `docker compose up -d` to apply the change.