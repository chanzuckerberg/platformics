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
* `settings.py` - config variables




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
* `cerbos` - generated access policies for user actions for each entity type
* `database/` - code related to establishing DB connections / sessions
  * `migrations/` - alembic migrations
  * `models/` - generated SQLAlchemy models 
* `schema/`
  * `schema.yaml` - LinkML schema used to codegen entity-related files
* `test_infra/`
  * `factories/` - FactoryBoy factories generated for each entity type
* `tests/` - your custom tests (not codegenned)
* `etc/` - some basic setup configuration
