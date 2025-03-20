"""
Test cascade deletion
"""

import pytest
from platformics.database.connect import SyncDB
from conftest import SessionStorage, GQLTestClient
from test_infra.factories.sequencing_read import SequencingReadFactory


@pytest.mark.asyncio
async def test_cascade_delete(
    sync_db: SyncDB,
    gql_client: GQLTestClient,
) -> None:
    """
    Test that we can make cascade deletions
    """
    user_id = 12345
    project_id = 123

    # Create mock data: 2 SequencingReads, each with a different Sample, and each with R1/R2
    with sync_db.session() as session:
        SessionStorage.set_session(session)
        sequencing_reads = SequencingReadFactory.create_batch(
            2, technology="Illumina", owner_user_id=user_id, collection_id=project_id
        )
        for sr in sequencing_reads:
            sr.r1_file.collection_id = project_id
            sr.r1_file.owner_user_id = user_id
            sr.r2_file.collection_id = project_id
            sr.r2_file.owner_user_id = user_id
            sr.sample.collection_id = project_id
            sr.sample.owner_user_id = user_id
        session.commit()

    # Delete the first Sample
    query = f"""
      mutation MyMutation {{
        deleteSample (where: {{ id: {{ _eq: "{sequencing_reads[0].sample_id}" }}  }}) {{
          id
        }}
      }}
    """
    result = await gql_client.query(query, user_id=user_id, member_projects=[project_id], service_identity="workflows")
    assert result["data"]["deleteSample"][0]["id"] == str(sequencing_reads[0].sample_id)

    # The first SequencingRead should be deleted
    query = f"""
      query MyQuery {{
        sequencingReadsAggregate(where: {{ id: {{ _eq: "{sequencing_reads[0].entity_id}"}} }}) {{
            aggregate {{ count }}
        }}
      }}
    """
    result = await gql_client.query(query, member_projects=[project_id])
    assert result["data"]["sequencingReadsAggregate"]["aggregate"][0]["count"] == 0

    # The second SequencingRead should still exist
    query = f"""
      query MyQuery {{
        sequencingReadsAggregate(where: {{ id: {{ _eq: "{sequencing_reads[1].entity_id}"}} }}) {{
            aggregate {{ count }}
        }}
      }}
    """
    result = await gql_client.query(query, member_projects=[project_id])
    assert result["data"]["sequencingReadsAggregate"]["aggregate"][0]["count"] == 1

    # Files from the first SequencingRead should be deleted
    query = f"""
      query MyQuery {{
        files(where: {{ id: {{ _in: ["{sequencing_reads[0].r1_file.id}", "{sequencing_reads[0].r2_file.id}", "{sequencing_reads[0].primer_file.id}"] }} }}) {{
            id
        }}
      }}
    """
    result = await gql_client.query(query, member_projects=[project_id])
    assert len(result["data"]["files"]) == 0

    # Files from the second SequencingRead should NOT be deleted
    query = f"""
      query MyQuery {{
        files(where: {{ id: {{ _in: ["{sequencing_reads[1].r1_file.id}", "{sequencing_reads[1].r2_file.id}", "{sequencing_reads[1].primer_file.id}"] }} }}) {{
            id
        }}
      }}
    """
    result = await gql_client.query(query, member_projects=[project_id])
    assert len(result["data"]["files"]) == 2
