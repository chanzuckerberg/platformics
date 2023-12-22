"""
Test "where" clause capabilities on GQL queries
"""

import pytest
from platformics.database.connect import SyncDB
from platformics.codegen.conftest import GQLTestClient, SessionStorage
from platformics.codegen.tests.output.test_infra.factories.sequencing_read import SequencingReadFactory
from support.enums import SequencingTechnology

user_id = 12345
project_id = 123


def generate_sequencing_reads(sync_db: SyncDB) -> list:
    """
    Generate 5 sequencing reads, each with 1 different associated sample
    """
    with sync_db.session() as session:
        SessionStorage.set_session(session)
        sequencing_reads = SequencingReadFactory.create_batch(
            5, technology=SequencingTechnology.Illumina, owner_user_id=user_id, collection_id=project_id
        )
        return sequencing_reads


@pytest.mark.asyncio
async def test_where_clause_basic(sync_db: SyncDB, gql_client: GQLTestClient) -> None:
    """
    Fetch subset of sequencing reads with a where clause on id
    """
    sequencing_reads = generate_sequencing_reads(sync_db)
    query = f"""
        query GetSequencingReadWhere {{
            sequencingReads ( where: {{
                id: {{ _in: [ "{sequencing_reads[0].id}", "{sequencing_reads[1].id}", "{sequencing_reads[2].id}" ] }},
            }}) {{
                id
                sample {{
                    id
                    name
                }}
            }}
        }}
    """
    output = await gql_client.query(query, member_projects=[project_id])
    assert len(output["data"]["sequencingReads"]) == 3


@pytest.mark.asyncio
async def test_where_clause_nested(sync_db: SyncDB, gql_client: GQLTestClient) -> None:
    """
    Fetch subset of sequencing reads with a where clause on id and on sample name
    """

    sequencing_reads = generate_sequencing_reads(sync_db)
    query = f"""
        query GetSequencingReadWhere {{
            sequencingReads ( where: {{
                id: {{
                    _in: [ "{sequencing_reads[0].id}", "{sequencing_reads[1].id}", "{sequencing_reads[2].id}" ]
                }},
                sample: {{
                    name: {{
                        _in: ["{ sequencing_reads[0].sample.name }", "{ sequencing_reads[1].sample.name }"]
                    }}
                }}
            }}) {{
                id
                sample {{
                    id
                    name
                }}
            }}
        }}
    """
    output = await gql_client.query(query, member_projects=[project_id])
    # Since sample where clause at top level, expect to return 2 samples
    assert len(output["data"]["sequencingReads"]) == 2
    assert output["data"]["sequencingReads"][0]["sample"]["name"] == sequencing_reads[0].sample.name
    assert output["data"]["sequencingReads"][1]["sample"]["name"] == sequencing_reads[1].sample.name


@pytest.mark.asyncio
async def test_where_clause_lower(sync_db: SyncDB, gql_client: GQLTestClient) -> None:
    """
    Move the sample "where" clause down a level
    """
    sequencing_reads = generate_sequencing_reads(sync_db)
    query = f"""
        query GetSequencingReadWhere {{
            sequencingReads ( where: {{
                id: {{ _in: [ "{sequencing_reads[0].id}", "{sequencing_reads[1].id}", "{sequencing_reads[2].id}" ] }}
            }}) {{
                id
                sample ( where: {{
                    name: {{
                        _in: ["{ sequencing_reads[0].sample.name }", "{ sequencing_reads[1].sample.name }"]
                    }}
                }} ) {{
                    id
                    name
                }}
            }}
        }}
    """
    output = await gql_client.query(query, member_projects=[project_id])
    # Now that the "where" clause is at the sample level, expect 3 samples, but the third is null since it doesn't match
    assert len(output["data"]["sequencingReads"]) == 3
    assert output["data"]["sequencingReads"][0]["sample"]["name"] == sequencing_reads[0].sample.name
    assert output["data"]["sequencingReads"][1]["sample"]["name"] == sequencing_reads[1].sample.name
    assert output["data"]["sequencingReads"][2]["sample"] is None


@pytest.mark.asyncio
async def test_where_clause_mutations(sync_db: SyncDB, gql_client: GQLTestClient) -> None:
    """
    Make sure that the where clause restricts which objects are mutated
    """
    sequencing_reads = generate_sequencing_reads(sync_db)
    prev_technology = SequencingTechnology.Illumina.value
    new_technology = SequencingTechnology.Nanopore.value
    updated_ids = [str(sequencing_reads[0].id), str(sequencing_reads[1].id), str(sequencing_reads[2].id)]
    query = f"""
        mutation UpdateSequencingReadsWhere {{
            updateSequencingRead (
                where: {{
                    id: {{ _in: [ "{updated_ids[0]}", "{updated_ids[1]}", "{updated_ids[2]}" ] }},
                }},
                input: {{
                    # Note that technology is an enum so don't need to quote the value
                    technology: {new_technology},
                }}
            ) {{
                id
            }}
        }}
    """
    output = await gql_client.query(query, member_projects=[project_id])
    assert len(output["data"]["updateSequencingRead"]) == 3

    # Check that the technology was updated only for the specified samples
    query = """
        query GetSequencingReads {
            sequencingReads {
                id
                technology
            }
        }
    """
    output = await gql_client.query(query, member_projects=[project_id])
    assert len(output["data"]["sequencingReads"]) == len(sequencing_reads)
    for sequencing_read in output["data"]["sequencingReads"]:
        if sequencing_read["id"] in updated_ids:
            assert sequencing_read["technology"] == new_technology
        else:
            assert sequencing_read["technology"] == prev_technology
