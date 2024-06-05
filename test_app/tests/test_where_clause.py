"""
Test "where" clause capabilities on GQL queries
"""

import pytest
from platformics.database.connect import SyncDB
from conftest import GQLTestClient, SessionStorage, FileFactory
from platformics.codegen.tests.output.test_infra.factories.sample import SampleFactory
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


@pytest.mark.asyncio
async def test_where_clause_regex_match(sync_db: SyncDB, gql_client: GQLTestClient) -> None:
    """
    Verify that the regex operators work as expected.
    """
    # Regex for any string with "MATCH" in it
    regex = ".*MATCH.*"
    with sync_db.session() as session:
        SessionStorage.set_session(session)
        # Sample names that match the regex (case-sensitive)
        case_sensitive_matches = ["A MATCH", "A MATCHING SAMPLE"]
        # Sample names that match the regex if case is ignored, but do not match if case is considered
        case_insensitive_matches = ["a match if ignore case", "a matching sample if ignore case"]
        # Sample names that don't match the regex at all
        no_matches = ["asdf1234", "HCTAM"]
        # Create the samples
        all_sample_names = case_sensitive_matches + case_insensitive_matches + no_matches
        for name in all_sample_names:
            SampleFactory.create(name=name, owner_user_id=user_id, collection_id=project_id)

    match_case_query = f"""
        query GetSamplesMatchingCase {{
            samples ( where: {{
                name: {{
                    _regex: "{regex}"
                }}
            }}) {{
                name
            }}
        }}
    """

    match_case_query_output = await gql_client.query(match_case_query, member_projects=[project_id])
    assert len(match_case_query_output["data"]["samples"]) == 2
    output_sample_names = [sample["name"] for sample in match_case_query_output["data"]["samples"]]
    assert sorted(output_sample_names) == sorted(case_sensitive_matches)

    ignore_case_query = f"""
        query GetSamplesMatchingIgnoreCase {{
            samples ( where: {{
                name: {{
                    _iregex: "{regex}"
                }}
            }}) {{
                name
            }}
        }}
    """

    ignore_case_query_output = await gql_client.query(ignore_case_query, member_projects=[project_id])
    assert len(ignore_case_query_output["data"]["samples"]) == 4
    output_sample_names = [sample["name"] for sample in ignore_case_query_output["data"]["samples"]]
    assert sorted(output_sample_names) == sorted(case_sensitive_matches + case_insensitive_matches)

    no_match_query = f"""
        query GetSamplesNoMatch {{
            samples ( where: {{
                name: {{
                    _nregex: "{regex}"
                }}
            }}) {{
                name
            }}
        }}
    """

    no_match_query_output = await gql_client.query(no_match_query, member_projects=[project_id])
    assert len(no_match_query_output["data"]["samples"]) == 4
    output_sample_names = [sample["name"] for sample in no_match_query_output["data"]["samples"]]
    assert sorted(output_sample_names) == sorted(no_matches + case_insensitive_matches)

    no_match_ignore_case_query = f"""
        query GetSamplesNoMatchIgnoreCase {{
            samples ( where: {{
                name: {{
                    _niregex: "{regex}"
                }}
            }}) {{
                name
            }}
        }}
    """

    no_match_ignore_case_query_output = await gql_client.query(no_match_ignore_case_query, member_projects=[project_id])
    assert len(no_match_ignore_case_query_output["data"]["samples"]) == 2
    output_sample_names = [sample["name"] for sample in no_match_ignore_case_query_output["data"]["samples"]]
    assert sorted(output_sample_names) == sorted(no_matches)


@pytest.mark.asyncio
async def test_soft_deleted_objects(sync_db: SyncDB, gql_client: GQLTestClient) -> None:
    """
    Verify that the where clause works as expected with soft-deleted objects.
    By default, soft-deleted objects should not be returned.
    """
    sequencing_reads = generate_sequencing_reads(sync_db)
    FileFactory.update_file_ids()
    # Soft delete the first 3 sequencing reads by updating the deleted_at field
    deleted_ids = [str(sequencing_reads[0].id), str(sequencing_reads[1].id), str(sequencing_reads[2].id)]
    soft_delete_mutation = f"""
        mutation SoftDeleteSequencingReads {{
            updateSequencingRead (
                where: {{
                    id: {{ _in: [ "{deleted_ids[0]}", "{deleted_ids[1]}", "{deleted_ids[2]}" ] }},
                }},
                input: {{
                    deletedAt: "2021-01-01T00:00:00Z",
                }}
            ) {{
                id
            }}
        }}
    """
    output = await gql_client.query(soft_delete_mutation, member_projects=[project_id])
    assert len(output["data"]["updateSequencingRead"]) == 3

    # Check that the soft-deleted sequencing reads are not returned
    regular_query = """
        query GetSequencingReads {
            sequencingReads {
                id
            }
        }
    """
    output = await gql_client.query(regular_query, member_projects=[project_id])
    assert len(output["data"]["sequencingReads"]) == 2
    for sequencing_read in output["data"]["sequencingReads"]:
        assert sequencing_read["id"] not in deleted_ids

    # Check that the soft-deleted sequencing reads are returned when explicitly requested
    soft_deleted_query = """
        query GetSequencingReads {
            sequencingReads ( where: { deletedAt: { _is_null: false } }) {
                id
            }
        }
    """
    output = await gql_client.query(soft_deleted_query, member_projects=[project_id])
    assert len(output["data"]["sequencingReads"]) == 3
    for sequencing_read in output["data"]["sequencingReads"]:
        assert sequencing_read["id"] in deleted_ids

    # Check that we can hard-delete the soft-deleted objects
    hard_delete_mutation = f"""
        mutation DeleteSequencingReads {{
            deleteSequencingRead (
                where: {{
                    id: {{ _in: [ "{deleted_ids[0]}", "{deleted_ids[1]}", "{deleted_ids[2]}" ] }},
                }}
            ) {{
                id
            }}
        }}
    """

    output = await gql_client.query(hard_delete_mutation, user_id=user_id, member_projects=[project_id])
    assert len(output["data"]["deleteSequencingRead"]) == 3

    # Check that the hard-deleted sequencing reads are not returned
    output = await gql_client.query(soft_deleted_query, member_projects=[project_id])
    assert len(output["data"]["sequencingReads"]) == 0
