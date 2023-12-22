"""
Authorization spot-checks
"""

import pytest
from platformics.database.connect import SyncDB
from platformics.codegen.conftest import GQLTestClient, SessionStorage
from platformics.codegen.tests.output.test_infra.factories.sample import SampleFactory


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "project_ids,num_results,cities",
    [([], 0, ()), ([333], 2, {"City1"}), ([333, 555], 4, {"City1", "City3"})],
)
async def test_collection_authorization(
    project_ids: list[int],
    num_results: int,
    cities: tuple[str],
    sync_db: SyncDB,
    gql_client: GQLTestClient,
) -> None:
    """
    Make sure users can only see samples in collections they have access to.
    """
    owner_user_id = 333
    user_id = 12345

    # Create mock data
    with sync_db.session() as session:
        SessionStorage.set_session(session)
        SampleFactory.create_batch(2, collection_location="City1", owner_user_id=owner_user_id, collection_id=333)
        SampleFactory.create_batch(2, collection_location="City2", owner_user_id=owner_user_id, collection_id=444)
        SampleFactory.create_batch(2, collection_location="City3", owner_user_id=owner_user_id, collection_id=555)

    # Fetch all samples
    query = """
        query MyQuery {
            samples {
                id
                collectionLocation
            }
        }
    """
    output = await gql_client.query(query, user_id=user_id, member_projects=project_ids)
    assert len(output["data"]["samples"]) == num_results
    assert {sample["collectionLocation"] for sample in output["data"]["samples"]} == set(cities)
