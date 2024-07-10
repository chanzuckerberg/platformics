"""
Test basic queries and mutations
"""

import datetime
import pytest
from platformics.database.connect import SyncDB
from conftest import GQLTestClient, SessionStorage
from test_infra.factories.constraint_checked_type import ConstraintCheckedTypeFactory

date_now = datetime.datetime.now()


@pytest.mark.asyncio
async def test_field_with_spaces(
    sync_db: SyncDB,
    gql_client: GQLTestClient,
) -> None:
    """
    Test that we can only fetch samples from the database that we have access to
    """
    user_id = 12345
    project_id = 123

    # Create mock data
    with sync_db.session() as session:
        SessionStorage.set_session(session)
        cct = ConstraintCheckedTypeFactory.create(
            owner_user_id=user_id,
            collection_id=project_id,
        )

    # Fetch the row via gql
    query = """
        query MyQuery {
            constraintCheckedTypes {
                id,
                fieldWithSpaces
            }
        }
    """
    output = await gql_client.query(query, user_id=user_id, member_projects=[project_id])
    assert cct.field_with_spaces == output["data"]["constraintCheckedTypes"][0]["fieldWithSpaces"]
    assert output["data"]["constraintCheckedTypes"][0]["fieldWithSpaces"]
