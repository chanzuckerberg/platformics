"""
Test deletion of bulkDownloads > 7 days old
"""

import pytest
import datetime
from platformics.database.connect import SyncDB
from conftest import SessionStorage, GQLTestClient, FileFactory
from platformics.codegen.tests.output.test_infra.factories.bulk_download import BulkDownloadFactory


@pytest.mark.asyncio
async def test_delete_old_bulk_downloads(
    sync_db: SyncDB,
    gql_client: GQLTestClient,
) -> None:
    """
    Test that we can delete bulk downloads older than 7 days
    """
    user_id = 12345
    project_id = 123

    # Create mock data: 3 current bulk downloads, 2 bulk downloads from 1 week ago, and 5 bulk downloads from 1 month ago
    with sync_db.session() as session:
        SessionStorage.set_session(session)
        current_time = datetime.datetime.now()
        one_week_ago = current_time - datetime.timedelta(days=7)
        one_month_ago = current_time - datetime.timedelta(days=30)

        current_bulk_downloads = BulkDownloadFactory.create_batch(3, owner_user_id=user_id, collection_id=None)
        one_week_old_bulk_downloads = BulkDownloadFactory.create_batch(
            2, owner_user_id=user_id, collection_id=None, created_at=one_week_ago
        )
        one_month_old_bulk_downloads = BulkDownloadFactory.create_batch(
            5, owner_user_id=user_id, collection_id=None, created_at=one_month_ago
        )
        all_old_bulk_downloads = one_week_old_bulk_downloads + one_month_old_bulk_downloads
        FileFactory.update_file_ids()

    # Delete old bulk downloads
    query = """
        mutation MyMutation {
            deleteOldBulkDownloads {
                id
            }
        }
    """

    # Verify that the mutation can't be called by a non-system user
    result = await gql_client.query(query, user_id=user_id, member_projects=[project_id])
    assert result["data"] is None
    assert "Unauthorized"

    # Verify that the mutation deletes all bulk downloads older than 7 days
    result = await gql_client.query(query, user_id=user_id, member_projects=[project_id], service_identity="rails")
    assert len(result["data"]["deleteOldBulkDownloads"]) == 7
    assert [bd["id"] for bd in result["data"]["deleteOldBulkDownloads"]] == [
        str(bd.id) for bd in all_old_bulk_downloads
    ]

    # Check that current bulk downloads are still there
    query = """
        query MyQuery {
            bulkDownloads {
                id
            }
        }
    """

    result = await gql_client.query(query, user_id=user_id, member_projects=[project_id])
    assert len(result["data"]["bulkDownloads"]) == 3
    assert [bd["id"] for bd in result["data"]["bulkDownloads"]] == [str(bd.id) for bd in current_bulk_downloads]
