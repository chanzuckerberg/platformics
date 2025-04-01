"""
Fixtures for API tests
"""

import json
import os
import typing
from typing import Optional
from platformics.graphql_api.core.error_handler import HandleErrors

import pytest
import pytest_asyncio
from fastapi import FastAPI
from graphql_api.mutations import Mutation
from graphql_api.queries import Query
from httpx import AsyncClient
from platformics.graphql_api.core.deps import (
    get_auth_principal,
    get_db_session,
    get_engine,
    require_auth_principal,
)
from platformics.security.authorization import Principal
from platformics.graphql_api.setup import get_app
from platformics.database.connect import AsyncDB, SyncDB, init_async_db, init_sync_db
from platformics.database.models.base import Base
from platformics.test_infra.factories.base import SessionStorage
from pytest_postgresql import factories
from pytest_postgresql.executor_noop import NoopExecutor
from pytest_postgresql.janitor import DatabaseJanitor
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request
from platformics.settings import APISettings
from platformics.graphql_api.setup import get_strawberry_config
import strawberry

__all__ = [
    "gql_client",
    "GQLTestClient",
    "SessionStorage",
]  # needed by tests


test_db: NoopExecutor = factories.postgresql_noproc(
    host=os.getenv("PLATFORMICS_DATABASE_HOST"),
    password=os.getenv("PLATFORMICS_DATABASE_PASSWORD"),
)  # type: ignore


def get_db_uri(
    db_user: typing.Optional[str],
    db_pass: typing.Optional[str],
    db_host: typing.Optional[str],
    db_port: typing.Optional[int],
    db_name: typing.Optional[str],
) -> str:
    """
    Utility function to generate database URI
    """
    db_uri = f"{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
    return db_uri


@pytest.fixture()
def test_db_uri(test_db: NoopExecutor) -> str:
    return get_db_uri(
        db_host=test_db.host,
        db_port=test_db.port,
        db_user=test_db.user,
        db_pass=test_db.password,
        db_name=test_db.dbname,
    )


@pytest.fixture()
def sync_db(test_db: NoopExecutor, test_db_uri: str) -> typing.Generator[SyncDB, None, None]:
    """
    Fixture to create a synchronous database connection
    """

    with DatabaseJanitor(test_db.user, test_db.host, test_db.port, test_db.dbname, test_db.version, test_db.password):
        db: SyncDB = init_sync_db(f"postgresql+psycopg://{test_db_uri}")
        Base.metadata.create_all(db.engine)
        yield db


@pytest_asyncio.fixture()
async def async_db(sync_db: SyncDB, test_db: NoopExecutor, test_db_uri: str) -> typing.AsyncGenerator[AsyncDB, None]:
    """
    Fixture to create an asynchronous database connection
    """
    db = init_async_db(f"postgresql+asyncpg://{test_db_uri}")
    yield db


# When importing `gql_client`, it will use the `http_client` below, which uses the test schema
@pytest_asyncio.fixture()
async def http_client(api_test_schema: FastAPI) -> AsyncClient:
    return AsyncClient(app=api_test_schema, base_url="http://test-codegen")


class GQLTestClient:
    def __init__(self, http_client: AsyncClient):
        self.http_client = http_client

    async def query(
        self,
        query: str,
        user_id: Optional[int] = None,
        member_projects: Optional[list[int]] = None,
        owner_projects: Optional[list[int]] = None,
        viewer_projects: Optional[list[int]] = None,
        service_identity: Optional[str] = None,
    ) -> dict[str, typing.Any]:
        """
        Utility function for making GQL HTTP queries with authorization info.
        """
        if not user_id:
            user_id = 111
        if not owner_projects:
            owner_projects = []
        if not member_projects:
            member_projects = []
        if not viewer_projects:
            viewer_projects = []
        gql_headers = {
            "content-type": "application/json",
            "accept": "application/json",
            "user_id": str(user_id),
            "member_projects": json.dumps(member_projects),
            "owner_projects": json.dumps(owner_projects),
            "viewer_projects": json.dumps(viewer_projects),
            "service_identity": service_identity or "",
        }
        result = await self.http_client.post("/graphql", json={"query": query}, headers=gql_headers)
        return result.json()


@pytest_asyncio.fixture()
async def gql_client(http_client: AsyncClient) -> GQLTestClient:
    """
    Create a GQL client.
    """
    client = GQLTestClient(http_client)
    return client


async def patched_authprincipal(request: Request) -> Principal:
    """
    Create a Principal object from request headers.
    """
    user_id = request.headers.get("user_id")
    if not user_id:
        raise Exception("user_id not found in request headers")
    principal = Principal(
        user_id,
        roles=["user"],
        attr={
            "user_id": int(user_id),
            "member_projects": json.loads(request.headers.get("member_projects", "[]")),
            "owner_projects": json.loads(request.headers.get("owner_projects", "[]")),
            "viewer_projects": json.loads(request.headers.get("viewer_projects", "[]")),
            "service_identity": request.headers.get("service_identity"),
        },
    )
    return principal


def overwrite_api(api: FastAPI, async_db: AsyncDB) -> None:
    """
    Utility function for overwriting API dependencies with test versions.
    """

    async def patched_session() -> typing.AsyncGenerator[AsyncSession, None]:
        session = async_db.session()
        try:
            yield session
        finally:
            await session.close()

    api.dependency_overrides[get_engine] = lambda: async_db
    api.dependency_overrides[get_db_session] = patched_session
    api.dependency_overrides[require_auth_principal] = patched_authprincipal
    api.dependency_overrides[get_auth_principal] = patched_authprincipal


@pytest_asyncio.fixture()
async def api_test_schema(async_db: AsyncDB) -> FastAPI:
    """
    Create an API instance using the real schema.
    """
    settings = APISettings.model_validate({})  # Workaround for https://github.com/pydantic/pydantic/issues/3753
    strawberry_config = get_strawberry_config()
    schema = strawberry.Schema(query=Query, mutation=Mutation, config=strawberry_config, extensions=[HandleErrors()])
    api = get_app(settings, schema)
    overwrite_api(api, async_db)
    return api
