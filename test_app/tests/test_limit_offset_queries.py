"""
Test limit/offset on top-level queries
"""

import datetime
import pytest
from platformics.database.connect import SyncDB
from conftest import GQLTestClient, SessionStorage
from test_infra.factories.sample import SampleFactory

date_now = datetime.datetime.now()


@pytest.mark.asyncio
async def test_limit_query(
    sync_db: SyncDB,
    gql_client: GQLTestClient,
) -> None:
    """
    Test that we can limit the number of samples returned
    """
    user_id = 12345
    project_id = 123

    # Create mock data
    with sync_db.session() as session:
        SessionStorage.set_session(session)
        SampleFactory.create_batch(10, owner_user_id=user_id, collection_id=project_id)

    # Fetch all samples
    query = """
        query limitQuery {
            samples(limitOffset: {limit: 3}) {
                id,
                collectionLocation
            }
        }
    """
    output = await gql_client.query(query, user_id=user_id, member_projects=[project_id])
    assert len(output["data"]["samples"]) == 3


@pytest.mark.asyncio
async def test_offset_query(
    sync_db: SyncDB,
    gql_client: GQLTestClient,
) -> None:
    """
    Test that we can offset the number of samples returned
    """
    user_id = 12345
    project_id = 123

    # Create mock data
    with sync_db.session() as session:
        SessionStorage.set_session(session)
        for i in range(10):
            SampleFactory.create(name=f"Sample {i}", owner_user_id=user_id, collection_id=project_id)

    # Fetch all samples
    all_samples_query = """
        query allSamples {
            samples(orderBy: {name: asc}) {
                name
            }
        }
    """

    output = await gql_client.query(all_samples_query, user_id=user_id, member_projects=[project_id])
    all_sample_names = [sample["name"] for sample in output["data"]["samples"]]

    # Fetch samples with limit: 3, offset: 3
    query = """
        query offsetQuery {
            samples(limitOffset: {limit: 3, offset: 3}, orderBy: {name: asc}) {
                name
            }
        }
    """

    output = await gql_client.query(query, user_id=user_id, member_projects=[project_id])
    offset_sample_names = [sample["name"] for sample in output["data"]["samples"]]
    assert offset_sample_names == all_sample_names[3:6]

    # If we offset by 10, we should get an empty list
    query = """
        query offsetQuery {
            samples(limitOffset: {limit: 1, offset: 10}, orderBy: {name: asc}) {
                name
            }
        }
    """

    output = await gql_client.query(query, user_id=user_id, member_projects=[project_id])
    assert len(output["data"]["samples"]) == 0

    # If a user includes an offset without a limit, we should get an error
    query = """
        query offsetQuery {
            samples(limitOffset: {offset: 1}, orderBy: {name: asc}) {
                name
            }
        }
    """

    output = await gql_client.query(query, user_id=user_id, member_projects=[project_id])
    assert output["data"] is None
    assert "Cannot use offset without limit" in output["errors"][0]["message"]
