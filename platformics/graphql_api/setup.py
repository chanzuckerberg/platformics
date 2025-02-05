"""
Launch the GraphQL server.
"""

import typing

import strawberry
from fastapi import Depends, FastAPI
from strawberry.fastapi import GraphQLRouter
from strawberry.schema.config import StrawberryConfig
from strawberry.schema.name_converter import HasGraphQLName, NameConverter

from platformics.database.connect import AsyncDB
from platformics.graphql_api.core.deps import (
    get_auth_principal,
    get_authz_client,
    get_db_module,
    get_engine,
    get_s3_client,
)
from platformics.graphql_api.core.gql_loaders import EntityLoader
from platformics.security.authorization import AuthzClient, Principal
from platformics.settings import APISettings

# ------------------------------------------------------------------------------
# Utilities for setting up the app
# ------------------------------------------------------------------------------


def get_context(
    engine: AsyncDB = Depends(get_engine),
    authz_client: AuthzClient = Depends(get_authz_client),
    principal: Principal = Depends(get_auth_principal),
    db_module: AsyncDB = Depends(get_db_module),
) -> dict[str, typing.Any]:
    """
    Defines sqlalchemy_loader, used by dataloaders
    """
    return {
        "sqlalchemy_loader": EntityLoader(engine=engine, authz_client=authz_client, principal=principal),
        # This is entirely to support automatically resolving Relay Nodes in the EntityInterface
        "db_module": db_module,
    }


class CustomNameConverter(NameConverter):
    """
    Arg/Field names that start with _ are not camel-cased
    """

    def get_graphql_name(self, obj: HasGraphQLName) -> str:
        if obj.python_name.startswith("_"):
            return obj.python_name
        return super().get_graphql_name(obj)


def get_app(
    settings: APISettings,
    schema: strawberry.Schema,
    db_module: typing.Any,
    dependencies: typing.Optional[typing.Sequence[Depends]] = [],
) -> FastAPI:
    """
    Make sure tests can get their own instances of the app.
    """

    title = settings.SERVICE_NAME
    graphql_app: GraphQLRouter = GraphQLRouter(schema, context_getter=get_context)
    _app = FastAPI(title=title, debug=settings.DEBUG, dependencies=dependencies)
    _app.include_router(graphql_app, prefix="/graphql")
    # Add a global settings object to the app that we can use as a dependency
    _app.state.settings = settings
    _app.state.db_module = db_module

    return _app


def get_strawberry_config():
    return StrawberryConfig(auto_camel_case=True, name_converter=CustomNameConverter())
