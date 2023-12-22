"""
Test file queries
"""

import pytest
from platformics.database.connect import SyncDB
from platformics.codegen.conftest import SessionStorage, FileFactory, GQLTestClient
from platformics.codegen.tests.output.test_infra.factories.sequencing_read import SequencingReadFactory


@pytest.mark.asyncio
async def test_file_query(
    sync_db: SyncDB,
    gql_client: GQLTestClient,
) -> None:
    """
    Test that we can only fetch files that we have access to
    """
    user1_id = 12345
    user2_id = 67890
    user3_id = 87654
    project1_id = 123
    project2_id = 456

    # Create mock data
    with sync_db.session() as session:
        SessionStorage.set_session(session)
        SequencingReadFactory.create_batch(2, owner_user_id=user1_id, collection_id=project1_id)
        SequencingReadFactory.create_batch(6, owner_user_id=user2_id, collection_id=project1_id)
        SequencingReadFactory.create_batch(4, owner_user_id=user3_id, collection_id=project2_id)
        FileFactory.update_file_ids()

    # Fetch all samples
    query = """
      query MyQuery {
        files {
          entity {
            collectionId
            ownerUserId
            id
            type
          }
          path
          entityFieldName
        }
      }
    """
    output = await gql_client.query(query, member_projects=[project1_id])
    # Each SequencingRead results in 5 files:
    # r1_file, r2_file
    # primer_file -> GenomicRange file
    # GenomicRange produces ReferenceGenome -> file and file_index
    # so we expect 8 * 5 = 40 files.
    assert len(output["data"]["files"]) == 40
    for file in output["data"]["files"]:
        assert file["path"] is not None
        assert file["entity"]["collectionId"] == project1_id
        assert file["entity"]["ownerUserId"] in (user1_id, user2_id)


@pytest.mark.asyncio
async def test_nested_files(
    sync_db: SyncDB,
    gql_client: GQLTestClient,
) -> None:
    """
    Test that we can fetch related file info.
    """
    user1_id = 12345
    user2_id = 67890
    user3_id = 87654
    project1_id = 123
    project2_id = 456

    # Create mock data
    with sync_db.session() as session:
        SessionStorage.set_session(session)
        SequencingReadFactory.create_batch(2, owner_user_id=user1_id, collection_id=project1_id)
        SequencingReadFactory.create_batch(6, owner_user_id=user2_id, collection_id=project1_id)
        SequencingReadFactory.create_batch(4, owner_user_id=user3_id, collection_id=project2_id)
        FileFactory.update_file_ids()

    # Fetch all samples
    query = """
        query MyQuery {
          sequencingReads {
            r1File {
              entityId
              fileFormat
              path
              size
            }
            nucleicAcid
            id
            ownerUserId
          }
        }
    """
    output = await gql_client.query(query, member_projects=[project1_id])
    assert len(output["data"]["sequencingReads"]) == 8

    for read in output["data"]["sequencingReads"]:
        assert read["r1File"] is not None
        assert read["r1File"]["entityId"] == read["id"]
        assert read["r1File"]["path"]
