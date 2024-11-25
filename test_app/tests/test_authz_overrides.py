"""
Test that our principal-generation and authz client functionality can be overriden the way the docs say they acan.
"""

import datetime
import pytest
import sqlalchemy as sa
from platformics.database.connect import SyncDB
from platformics.security.authorization import AuthzClient
from platformics.graphql_api.core.deps import get_settings, get_authz_client
from fastapi import Depends
from conftest import GQLTestClient, SessionStorage
from test_infra.factories.sample import SampleFactory
from fastapi import FastAPI
from platformics.security.authorization import Principal
from platformics.settings import APISettings
from platformics.graphql_api.core.deps import (
    get_auth_principal,
)

date_now = datetime.datetime.now()


@pytest.mark.asyncio
async def test_principal_override(
    api_test_schema: FastAPI,
    sync_db: SyncDB,
    gql_client: GQLTestClient,
) -> None:
    """
    Test that we can override the way auth principals get generated. Our tests
    use this functionality under the hood so we know it works, but since this
    interface is now *explicitly* documented, it's a breaking change to alter the
    interface.
    """

    def custom_auth_principal():
        return Principal(
            "user123",
            roles=["user"],
            attr={
                "user_id": "user123",
                "owner_projects": [],
                "member_projects": [],
                "service_identity": [],
                # This value can be read from a secret or external db or anything you wish.
                # It's just hardcoded here for brevity.
                "viewer_projects": [444],
            },
        )

    api_test_schema.dependency_overrides[get_auth_principal] = custom_auth_principal

    user_id = 12345
    secondary_user_id = 67890
    project_id = 444

    # Create mock data
    with sync_db.session() as session:
        SessionStorage.set_session(session)
        SampleFactory.create_batch(
            2,
            collection_location="San Francisco, CA",
            collection_date=date_now,
            owner_user_id=user_id,
            collection_id=project_id,
        )
        SampleFactory.create_batch(
            6,
            collection_location="Mountain View, CA",
            collection_date=date_now,
            owner_user_id=user_id,
            collection_id=project_id,
        )
        SampleFactory.create_batch(
            4,
            collection_location="Phoenix, AZ",
            collection_date=date_now,
            owner_user_id=secondary_user_id,
            collection_id=9999,
        )

    # Fetch all samples
    query = """
        query MyQuery {
            samples {
                id,
                collectionLocation
            }
        }
    """
    output = await gql_client.query(query, user_id=user_id, member_projects=[project_id])
    locations = [sample["collectionLocation"] for sample in output["data"]["samples"]]
    assert "San Francisco, CA" in locations
    assert "Mountain View, CA" in locations
    assert "Phoenix, AZ" not in locations


class CustomAuthzClient(AuthzClient):
    def get_resource_query(self, principal, action, model_cls, relationship):
        query = sa.select(model_cls).where(model_cls.name.in_(["apple", "asparagus"]))
        return query


def custom_authz_client(settings: APISettings = Depends(get_settings)) -> AuthzClient:
    return AuthzClient(settings=settings)


@pytest.mark.asyncio
async def test_authz_client_override(
    api_test_schema: FastAPI,
    sync_db: SyncDB,
    gql_client: GQLTestClient,
) -> None:
    """
    Test that we can override the way auth principals get generated. Our tests
    use this functionality under the hood so we know it works, but since this
    interface is now *explicitly* documented, it's a breaking change to alter the
    interface.
    """

    api_test_schema.dependency_overrides[get_authz_client] = custom_authz_client

    user_id = 12345
    secondary_user_id = 67890
    project_id = 444

    # Create mock data
    with sync_db.session() as session:
        SessionStorage.set_session(session)
        SampleFactory.create(
            name="bananas",
            collection_date=date_now,
            owner_user_id=user_id,
            collection_id=project_id,
        )
        SampleFactory.create(
            name="apples",
            collection_date=date_now,
            owner_user_id=user_id,
            collection_id=project_id,
        )
        SampleFactory.create(
            name="asparagus",
            collection_date=date_now,
            owner_user_id=secondary_user_id,
            collection_id=project_id,
        )

    # Fetch all samples
    query = """
        query MyQuery {
            samples {
                id,
                name
            }
        }
    """
    output = await gql_client.query(query, user_id=user_id, member_projects=[project_id])
    names = [sample["name"] for sample in output["data"]["samples"]]
    assert "apples" in names
    assert "asparagus" in names
    assert "banana" not in names
