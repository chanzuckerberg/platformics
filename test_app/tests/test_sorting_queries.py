"""
Test queries with an ORDER BY clause
"""

import pytest
from platformics.database.connect import SyncDB
from conftest import GQLTestClient, SessionStorage
from test_infra.factories.sample import SampleFactory
from test_infra.factories.sequencing_read import SequencingReadFactory
from test_infra.factories.contig import ContigFactory
from test_infra.factories.upstream_database import UpstreamDatabaseFactory


@pytest.mark.asyncio
async def test_basic_order_by_query(
    sync_db: SyncDB,
    gql_client: GQLTestClient,
) -> None:
    """
    Test that we can add an ORDER BY clause to a query
    """
    user_id = 12345
    project_id = 123

    # Create mock data
    with sync_db.session() as session:
        SessionStorage.set_session(session)
        SampleFactory.create_batch(
            2, collection_location="San Francisco, CA", owner_user_id=user_id, collection_id=project_id
        )
        SampleFactory.create_batch(
            1, collection_location="Mountain View, CA", owner_user_id=user_id, collection_id=project_id
        )
        SampleFactory.create_batch(
            2, collection_location="Los Angeles, CA", owner_user_id=user_id, collection_id=project_id
        )

    # Fetch all samples, in descending order of collection location
    query = """
        query MyQuery {
            samples(orderBy: {collectionLocation: desc}) {
                collectionLocation
            }
        }
    """
    output = await gql_client.query(query, user_id=user_id, member_projects=[project_id])
    locations = [sample["collectionLocation"] for sample in output["data"]["samples"]]
    assert locations == [
        "San Francisco, CA",
        "San Francisco, CA",
        "Mountain View, CA",
        "Los Angeles, CA",
        "Los Angeles, CA",
    ]


@pytest.mark.asyncio
async def test_order_multiple_fields_query(
    sync_db: SyncDB,
    gql_client: GQLTestClient,
) -> None:
    """
    Test that we can sort by multiple fields, and that the order of the fields are preserved
    """
    user_id = 12345
    project_id = 123
    secondary_project_id = 234

    # Create mock data
    with sync_db.session() as session:
        SessionStorage.set_session(session)
        SampleFactory(owner_user_id=user_id, collection_id=project_id, collection_location="San Francisco, CA")
        SampleFactory(
            owner_user_id=user_id, collection_id=secondary_project_id, collection_location="San Francisco, CA"
        )
        SampleFactory(owner_user_id=user_id, collection_id=project_id, collection_location="Mountain View, CA")
        SampleFactory(
            owner_user_id=user_id, collection_id=secondary_project_id, collection_location="Mountain View, CA"
        )

    # Fetch all samples, in descending order of collection id and then ascending order of collection location
    query = """
        query MyQuery {
            samples(orderBy: [{collectionId: desc}, {collectionLocation: asc}]) {
                collectionLocation,
                collectionId
            }
        }
    """
    output = await gql_client.query(query, user_id=user_id, member_projects=[project_id, secondary_project_id])
    locations = [sample["collectionLocation"] for sample in output["data"]["samples"]]
    collection_ids = [sample["collectionId"] for sample in output["data"]["samples"]]
    assert locations == ["Mountain View, CA", "San Francisco, CA", "Mountain View, CA", "San Francisco, CA"]
    assert collection_ids == [234, 234, 123, 123]

    # Fetch all samples, in ascending order of collection location and then descending order of collection id
    query = """
        query MyQuery {
            samples(orderBy: [{collectionLocation: asc}, {collectionId: desc}]) {
                collectionLocation,
                collectionId
            }
        }
    """
    output = await gql_client.query(query, user_id=user_id, member_projects=[project_id, secondary_project_id])
    locations = [sample["collectionLocation"] for sample in output["data"]["samples"]]
    collection_ids = [sample["collectionId"] for sample in output["data"]["samples"]]
    assert locations == ["Mountain View, CA", "Mountain View, CA", "San Francisco, CA", "San Francisco, CA"]
    assert collection_ids == [234, 123, 234, 123]


@pytest.mark.asyncio
async def test_sort_nested_objects_query(
    sync_db: SyncDB,
    gql_client: GQLTestClient,
) -> None:
    """
    Test that we can sort nested objects
    """
    user_id = 12345
    project_id = 123

    with sync_db.session() as session:
        SessionStorage.set_session(session)
        sample_1 = SampleFactory(
            owner_user_id=user_id, collection_id=project_id, collection_location="San Francisco, CA"
        )
        sample_2 = SampleFactory(
            owner_user_id=user_id, collection_id=project_id, collection_location="Mountain View, CA"
        )
        SequencingReadFactory(owner_user_id=user_id, collection_id=project_id, sample=sample_1, nucleic_acid="DNA")
        SequencingReadFactory(owner_user_id=user_id, collection_id=project_id, sample=sample_1, nucleic_acid="RNA")
        SequencingReadFactory(owner_user_id=user_id, collection_id=project_id, sample=sample_2, nucleic_acid="DNA")
        SequencingReadFactory(owner_user_id=user_id, collection_id=project_id, sample=sample_2, nucleic_acid="RNA")

    # Fetch all samples, in descending order of collection location, and then in ascending order of
    # the related sequencing read's nucleic acid
    query = """
        query MyQuery {
            samples(orderBy: {collectionLocation: desc}) {
                collectionLocation
                sequencingReads(orderBy: {nucleicAcid: asc}) {
                    edges {
                        node {
                            nucleicAcid
                        }
                    }
                }
            }
        }
    """
    output = await gql_client.query(query, user_id=user_id, member_projects=[project_id])
    locations = [sample["collectionLocation"] for sample in output["data"]["samples"]]
    assert locations == ["San Francisco, CA", "Mountain View, CA"]
    nucleic_acids = []
    for sample in output["data"]["samples"]:
        for sr in sample["sequencingReads"]["edges"]:
            nucleic_acids.append(sr["node"]["nucleicAcid"])
    assert nucleic_acids == ["DNA", "RNA", "DNA", "RNA"]


@pytest.mark.asyncio
async def test_order_by_related_field_query(
    sync_db: SyncDB,
    gql_client: GQLTestClient,
) -> None:
    """
    Test that we can sort by fields of a related object
    """
    user_id = 12345
    project_id = 123

    # Create mock data
    with sync_db.session() as session:
        SessionStorage.set_session(session)
        sample_1 = SampleFactory(
            owner_user_id=user_id, collection_id=project_id, collection_location="Mountain View, CA"
        )
        sample_2 = SampleFactory(
            owner_user_id=user_id, collection_id=project_id, collection_location="San Francisco, CA"
        )
        SequencingReadFactory(owner_user_id=user_id, collection_id=project_id, sample=sample_1, nucleic_acid="DNA")
        SequencingReadFactory(owner_user_id=user_id, collection_id=project_id, sample=sample_1, nucleic_acid="RNA")
        SequencingReadFactory(owner_user_id=user_id, collection_id=project_id, sample=sample_2, nucleic_acid="DNA")
        SequencingReadFactory(owner_user_id=user_id, collection_id=project_id, sample=sample_2, nucleic_acid="RNA")

    # Fetch all sequencing reads, in descending order of the related sample's collection location
    query = """
        query MyQuery {
            sequencingReads(orderBy: {sample: {collectionLocation: desc}}) {
                nucleicAcid
                sample {
                    collectionLocation
                }
            }
        }
    """
    output = await gql_client.query(query, user_id=user_id, member_projects=[project_id])
    nucleic_acids = [sr["nucleicAcid"] for sr in output["data"]["sequencingReads"]]
    collection_locations = [sr["sample"]["collectionLocation"] for sr in output["data"]["sequencingReads"]]
    assert nucleic_acids == ["DNA", "RNA", "DNA", "RNA"]
    assert collection_locations == ["San Francisco, CA", "San Francisco, CA", "Mountain View, CA", "Mountain View, CA"]


@pytest.mark.asyncio
async def test_deeply_nested_query(
    sync_db: SyncDB,
    gql_client: GQLTestClient,
) -> None:
    """
    Test that we can sort by fields of a very deeply nested object
    """
    user_id = 12345
    project_id = 123

    # Create mock data
    with sync_db.session() as session:
        SessionStorage.set_session(session)
        upstream_db_1 = UpstreamDatabaseFactory(owner_user_id=user_id, collection_id=project_id, name="NCBI")
        upstream_db_2 = UpstreamDatabaseFactory(owner_user_id=user_id, collection_id=project_id, name="GTDB")
        contig_1 = ContigFactory(owner_user_id=user_id, collection_id=project_id, upstream_database=upstream_db_1)
        contig_2 = ContigFactory(owner_user_id=user_id, collection_id=project_id, upstream_database=upstream_db_2)
        SequencingReadFactory(owner_user_id=user_id, collection_id=project_id, contig=contig_1)
        SequencingReadFactory(owner_user_id=user_id, collection_id=project_id, contig=contig_1)
        SequencingReadFactory(owner_user_id=user_id, collection_id=project_id, contig=contig_2)
        SequencingReadFactory(owner_user_id=user_id, collection_id=project_id, contig=contig_2)

    # Fetch all contigs, in descending order of the related sequencing read's taxon's upstream database's name
    query = """
        query MyQuery {
            sequencingReads(orderBy: {contig: {upstreamDatabase: {name: desc}}}) {
                id
                contig {
                    upstreamDatabase {
                        name
                    }
                }
            }
        }
    """

    output = await gql_client.query(query, user_id=user_id, member_projects=[project_id])
    upstream_database_names = [d["contig"]["upstreamDatabase"]["name"] for d in output["data"]["sequencingReads"]]
    assert upstream_database_names == ["NCBI", "NCBI", "GTDB", "GTDB"]
