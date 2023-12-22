import pytest_asyncio
from platformics.database.connect import AsyncDB
from fastapi import FastAPI
from httpx import AsyncClient
from api.main import get_app
from api.conftest import overwrite_api, gql_client, moto_client, GQLTestClient
from test_infra.factories.main import SessionStorage, FileFactory

__all__ = ["gql_client", "moto_client", "GQLTestClient", "SessionStorage", "FileFactory"]  # needed by tests


@pytest_asyncio.fixture()
async def api_test_schema(async_db: AsyncDB) -> FastAPI:
    api = get_app(use_test_schema=True)
    overwrite_api(api, async_db)
    return api


# When importing `gql_client`, it will use the `http_client` below, which uses the test schema
@pytest_asyncio.fixture()
async def http_client(api_test_schema: FastAPI) -> AsyncClient:
    return AsyncClient(app=api_test_schema, base_url="http://test-codegen")
