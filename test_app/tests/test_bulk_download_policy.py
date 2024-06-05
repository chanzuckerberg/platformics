"""
Test collection_id policy for entities and bulk downloads
1. Test that users cannot create normal entities without a collection_id, or update them to have a null collection_id.
2. Test that users cannot create bulk downloads WITH a collection_id.
3. Test that only owners can view their own bulk downloads
"""

import pytest
from platformics.database.connect import SyncDB
from conftest import SessionStorage, GQLTestClient
from platformics.codegen.tests.output.test_infra.factories.bulk_download import BulkDownloadFactory
from platformics.codegen.tests.output.test_infra.factories.sample import SampleFactory


@pytest.mark.asyncio
async def test_null_collection_id_for_regular_entities(
    sync_db: SyncDB,
    gql_client: GQLTestClient,
) -> None:
    """
    Test that users cannot create normal entities without a collection_id, or update them to have a null collection_id.
    """
    owner_user_id = 333
    collection_id = 444

    # Attempt to create a sample without a collection_id
    query = f"""
        mutation MyMutation {{
          createSample(
            input: {{
                name: "No collection id",
                sampleType: "Type 1",
                waterControl: false,
                collectionLocation: "San Francisco, CA",
                collectionDate: "2024-01-01",
            }}
          ) {{ id }}
        }}
    """

    output = await gql_client.query(query, user_id=owner_user_id, member_projects=[collection_id])
    assert "Unauthorized: Cannot create entity in this collection" in output["errors"][0]["message"]

    # Create mock data
    with sync_db.session() as session:
        SessionStorage.set_session(session)
        sample = SampleFactory.create(name="Test Sample", owner_user_id=owner_user_id, collection_id=collection_id)

    # Attempt to update the sample to have a null collection_id
    query = f"""
        mutation MyMutation {{
          updateSample(
            where: {{id: {{_eq: "{sample.id}"}} }},
            input: {{
              collectionId: null
            }}
          ) {{ id }}
        }}
    """

    output = await gql_client.query(query, user_id=owner_user_id, member_projects=[collection_id])
    assert (
        "Field 'collectionId' is not defined by type 'SampleUpdateInput'. Did you mean 'collectionDate'?"
        in output["errors"][0]["message"]
    )


@pytest.mark.asyncio
async def test_null_collection_id_for_bulk_downloads(
    sync_db: SyncDB,
    gql_client: GQLTestClient,
) -> None:
    """
    Test that users cannot create bulk downloads WITH a collection_id.
    """
    owner_user_id = 333
    collection_id = 444

    # Attempt to create a bulk download with a collection_id
    query = f"""
        mutation MyMutation {{
            createBulkDownload(
                input: {{
                    collectionId: {collection_id},
                    downloadDisplayName: "Test Bulk Download",
                }}
            ) {{ id }}
        }}
    """

    output = await gql_client.query(query, user_id=owner_user_id, member_projects=[collection_id])
    assert "Unauthorized: Cannot create entity in this collection" in output["errors"][0]["message"]


@pytest.mark.asyncio
async def test_view_bulk_downloads(
    sync_db: SyncDB,
    gql_client: GQLTestClient,
) -> None:
    """
    Test that only owners can view their own bulk downloads
    """
    user_id = 111
    other_user_id = 222
    project_id = 123

    # Create mock data
    with sync_db.session() as session:
        SessionStorage.set_session(session)
        # Create 4 bulk downloads owned by user_id, and 3 for another user
        BulkDownloadFactory.create_batch(4, owner_user_id=user_id, collection_id=None)
        BulkDownloadFactory.create_batch(3, owner_user_id=other_user_id, collection_id=None)

    # Fetch all bulk downloads
    query = """
        query MyQuery {
            bulkDownloads {
                id
            }
        }
    """
    output = await gql_client.query(query, user_id=user_id, member_projects=[project_id])
    assert len(output["data"]["bulkDownloads"]) == 4
