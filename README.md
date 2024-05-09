# Platformics
---
Platformics is a GraphQL API framework that relies on code generation to implement a full featured GraphQL API on top of a PostgreSQL database, with support for authorization policy enforcement and file persistence via S3.

## How to set up your own platformics API
1. Copy the test_app boilerplate code to your own repository.
2. Edit `schema/schema.yml` to reflect your data model.
3. Run `make build` and then `make init` to build and run your own GraphQL API service.
4. Browse to http://localhost:9009 to interact with your api!
5. Run `make token` to generate an authorization token that you can use to interact with the API. The `make` target copies the necessary headers to the system clipboard. Paste the token into the `headers` section at the bottom of the GraphQL explorer API

## Iterating on your schema
1. Make changes to `schema/schema.yml`
2. Run `make codegen` to re-run code gen and restart the API service
3. If your changes require DB schema changes, run `make alembic-autogenerate` and `make alembic-upgrade-head` to generate DB migrations and run them.

## Debugging
1. Install the `Dev Containers` extension for vscode
2. Open a new VSCode window in your api directory. It will read the `.devcontainer/devcontainer.json` configuration and prompt you to reopen the directory in a container (lower right side of the screen). Click "Reopen in container"
3. Click the "Debuger" icon in the icon bar on the right side of the VSCode window. This will launch a secondary instance of the API service that listens on port 9008.
4. Set all the breakpoints you want. Browse to the api at http://localhost:9008 to trigger them

## Debugging and developing platformics itself
1. Run `make dev` in the root of this directory
2. TODO
