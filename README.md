# Platformics

Platformics is a GraphQL API framework that relies on code generation to implement a full featured GraphQL API on top of a PostgreSQL database, with support for authorization policy enforcement and file persistence via S3. It's built on top of the best available Python tools and frameworks!

The libraries and tools that make Platformics work:

![image](docs/images/platformics_libs.svg)
 
### Links to these tools/libraries
 - [LinkML](https://linkml.io/) - Schema modeling language
 - [FastAPI](https://fastapi.tiangolo.com/) - Async HTTP router
 - [Strawberry](https://strawberry.rocks/) - GraphQL Framework
 - [Pydantic](https://docs.pydantic.dev/latest/) - Data validation
 - [Cerbos](https://www.cerbos.dev/) - Authorization
 - [SQLAlchemy](https://www.sqlalchemy.org/) - Database Access / ORM
 - [factory_boy](https://factoryboy.readthedocs.io/en/stable/) - Test fixtures
 - [Alembic](https://alembic.sqlalchemy.org/en/latest/) - Database migrations

## Current Features
- [x] Express your schema in a straightforward YAML format
- [x] GraphQL Dataloader pattern (no n+1 queries!)
- [x] Authorization policy enforcement
- [x] Flexible Filtering
- [x] Data aggregation
- [x] Top-level pagination
- [x] Relationship traversal
- [x] DB migrations
- [x] Generated Test fixtures
- [x] pytest wiring
- [x] VSCode debugger integration
- [x] Authorized S3 file up/downloads
- [x] Add custom REST endpoints to generated API
- [x] Add custom GQL queries/mutations to generated API

## Roadmap
- [ ] Plugin hooks to add business logic to generated GQL resolvers
- [ ] Support arbitrary class inheritance hierarchies

## How to set up your own platformics API
1. Copy the test_app boilerplate code to your own repository.
2. Edit `schema/schema.yml` to reflect your application's data model.
3. Run `make build` and then `make init` to build and run your own GraphQL API service.
4. Browse to http://localhost:9009/graphql to interact with your api!
5. Run `make token` to generate an authorization token that you can use to interact with the API. The `make` target copies the necessary headers to the system clipboard. Paste the token into the `headers` section at the bottom of the GraphQL explorer API

## Iterating on your schema
1. Make changes to `schema/schema.yml`
2. Run `make codegen` to re-run code gen and restart the API service
3. If your changes require DB schema changes, run `make alembic-autogenerate` and `make alembic-upgrade-head` to generate DB migrations and run them.

## Debugging
1. Install the `Dev Containers` extension for vscode
2. Open a new VSCode window in your api directory. It will read the `.devcontainer/devcontainer.json` configuration and prompt you to reopen the directory in a container (lower right side of the screen). Click "Reopen in container"
3. Click the "Run and Debug" icon in the icon bar on the right side of the VSCode window (or ctrl+shift+d). Then click the "start debugging" icon at the top of the run and debug panel (or press F5). This will launch a secondary instance of the API service that listens on port 9008.
4. Set all the breakpoints you want. Browse to the api at http://localhost:9008 to trigger them. Remember that the application restarts when files change, so you'll have to start and stop the debugger to pick up any changes you make!

## Debugging and developing platformics itself
1. Run `make dev` in the root of this directory. This launches a compose service called `dev-app` that has the `platformics` directory in this repo mounted inside the `test_app` application as a sub-module, so it can be edited directly and be debugged via the VSCode debugger.
2. Open a new VSCode window in the root of this reopo. It will read the `.devcontainer/devcontainer.json` configuration and prompt you to reopen the directory in a container (lower right side of the screen). Click "Reopen in container"
3. Click the "Run and Debug" icon in the icon bar on the right side of the VSCode window (or ctrl+shift+d). Then click the "start debugging" icon at the top of the run and debug panel (or press F5). This will launch a secondary instance of the API service that listens on port 9008.
4. Set all the breakpoints you want. Browse to the api at http://localhost:9008 to trigger them. Remember that the application restarts when files change, so you'll have to start and stop the debugger to pick up any changes you make!

## HOWTO
- [Extend the generated API](docs/HOWTO-extend-generated-api.md)
- [Customize Codegen templates](docs/HOWTO-customize-templates.md)

## Contributing
This project adheres to the Contributor Covenant code of conduct. By participating, you are expected to uphold this code. Please report unacceptable behavior to opensource@chanzuckerberg.com.

## Reporting Security Issues
Please disclose security issues responsibly by contacting security@chanzuckerberg.com.
