"""
Test basic error handling
"""

import pytest
from conftest import GQLTestClient
from platformics.database.connect import SyncDB
from platformics.test_infra.factories.base import SessionStorage
from test_infra.factories.school import SchoolFactory


@pytest.mark.asyncio
async def test_unauthorized_error(
    gql_client: GQLTestClient,
) -> None:
    """
    Validate that expected errors don't get masked by our error handler.
    """
    query = """
        mutation createOneSample {
            createSample(input: {
                name: "Test Sample"
                sampleType: "Type 1"
                waterControl: false
                collectionLocation: "San Francisco, CA"
                collectionDate: "2024-01-01"
                collectionId: 123
            }) {
                id,
                collectionLocation
            }
        }
    """
    output = await gql_client.query(query, member_projects=[456])

    # Make sure we haven't masked expected errors.
    assert output["data"] is None
    assert output["errors"][0]["message"].startswith("Unauthorized: Cannot create entity")


@pytest.mark.asyncio
async def test_python_error(
    gql_client: GQLTestClient,
) -> None:
    """
    Validate that unexpected errors do get masked by our error handler.
    """
    query = """
        query causeException {
            uncaughtExceptions {
                name
            }
        }
    """
    output = await gql_client.query(query, member_projects=[456])

    # Make sure we have masked unexpected errors.
    assert output["data"] is None
    assert "Unexpected error" in output["errors"][0]["message"]


@pytest.mark.asyncio
async def test_pagination_value_error(
    gql_client: GQLTestClient,
    sync_db: SyncDB,
) -> None:
    """
    Validate that we communicate about pagination limits for relay connections
    """
    auth_args = {"owner_user_id": 10, "collection_id": 10}
    with sync_db.session() as session:
        SessionStorage.set_session(session)
        SchoolFactory.create(**auth_args)
    query = """
      query MyQuery {
        schools {
          name
          students(first: 1000) {
            edges {
              node {
                name
              }
            }
          }
        }
      }
    """
    output = await gql_client.query(query, member_projects=[10])

    # Make sure we have masked unexpected errors.
    assert output["data"] is None
    assert "cannot be higher than 100" in output["errors"][0]["message"]
