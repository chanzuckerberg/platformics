"""
Launch the GraphQL server.
"""

import typing

import strawberry
from cerbos.sdk.client import CerbosClient
from cerbos.sdk.model import Principal
from fastapi import Depends, FastAPI
from strawberry.fastapi import GraphQLRouter
from strawberry.schema.config import StrawberryConfig
from strawberry.schema.name_converter import HasGraphQLName, NameConverter

from platformics.graphql_api.core.deps import get_auth_principal, get_cerbos_client, get_db_module, get_engine, get_s3_client
from platformics.graphql_api.core.gql_loaders import EntityLoader
from platformics.database.connect import AsyncDB
from platformics.database.models.file import File
from platformics.settings import APISettings

# ------------------------------------------------------------------------------
# Utilities for setting up the app
# ------------------------------------------------------------------------------


def get_context(
    engine: AsyncDB = Depends(get_engine),
    db_module: AsyncDB = Depends(get_db_module),
    cerbos_client: CerbosClient = Depends(get_cerbos_client),
    principal: Principal = Depends(get_auth_principal),
) -> dict[str, typing.Any]:
    """
    Defines sqlalchemy_loader, used by dataloaders
    """
    return {
        "sqlalchemy_loader": EntityLoader(engine=engine, cerbos_client=cerbos_client, principal=principal),
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


def get_app(settings: APISettings, schema: strawberry.Schema, db_module: typing.Any) -> FastAPI:
    """
    Make sure tests can get their own instances of the app.
    """
    File.set_settings(settings)
    File.set_s3_client(get_s3_client(settings))
    settings = APISettings.model_validate({})  # Workaround for https://github.com/pydantic/pydantic/issues/3753

    title = settings.SERVICE_NAME
    graphql_app: GraphQLRouter = GraphQLRouter(schema, context_getter=get_context)
    _app = FastAPI(title=title, debug=settings.DEBUG)
    _app.include_router(graphql_app, prefix="/graphql")
    # Add a global settings object to the app that we can use as a dependency
    _app.state.settings = settings
    _app.state.db_module = db_module

    return _app


def get_strawberry_config():
    return StrawberryConfig(auto_camel_case=True, name_converter=CustomNameConverter())
