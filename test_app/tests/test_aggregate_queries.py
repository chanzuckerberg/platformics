"""
Test aggregate queries
"""

import pytest
from platformics.database.connect import SyncDB
from conftest import GQLTestClient, SessionStorage
from test_infra.factories.sample import SampleFactory
from test_infra.factories.sequencing_read import SequencingReadFactory
from test_infra.factories.contig import ContigFactory
from test_infra.factories.upstream_database import UpstreamDatabaseFactory


@pytest.mark.asyncio
async def test_basic_aggregate_query(
    sync_db: SyncDB,
    gql_client: GQLTestClient,
) -> None:
    """
    Test that we can perform an aggregate query on a model
    """
    user_id = 12345
    project_id = 123
    secondary_project_id = 234

    # Create mock data
    with sync_db.session() as session:
        SessionStorage.set_session(session)
        SampleFactory.create_batch(
            2, collection_location="San Francisco, CA", owner_user_id=user_id, collection_id=project_id
        )
        SampleFactory.create_batch(
            3, collection_location="Mountain View, CA", owner_user_id=user_id, collection_id=secondary_project_id
        )

    # Fetch all samples
    query = """
        query MyQuery {
            samplesAggregate {
                aggregate {
                    avg {
                        collectionId
                    }
                    count
                    max {
                        collectionLocation
                    }
                    min {
                        collectionLocation
                    }
                    stddev {
                        collectionId
                    }
                    sum {
                        ownerUserId
                    }
                    variance {
                        collectionId
                    }
                }
            }
        }
    """
    output = await gql_client.query(query, user_id=user_id, member_projects=[project_id, secondary_project_id])
    avg_collectionId = output["data"]["samplesAggregate"]["aggregate"][0]["avg"]["collectionId"]
    count = output["data"]["samplesAggregate"]["aggregate"][0]["count"]
    max_collectionLocation = output["data"]["samplesAggregate"]["aggregate"][0]["max"]["collectionLocation"]
    min_collectionLocation = output["data"]["samplesAggregate"]["aggregate"][0]["min"]["collectionLocation"]
    stddev_collectionId = output["data"]["samplesAggregate"]["aggregate"][0]["stddev"]["collectionId"]
    sum_ownerUserId = output["data"]["samplesAggregate"]["aggregate"][0]["sum"]["ownerUserId"]

    assert avg_collectionId == 189
    assert count == 5
    assert max_collectionLocation == "San Francisco, CA"
    assert min_collectionLocation == "Mountain View, CA"
    assert stddev_collectionId == 60
    assert sum_ownerUserId == 61725


@pytest.mark.asyncio
async def test_nested_aggregate_query(
    sync_db: SyncDB,
    gql_client: GQLTestClient,
) -> None:
    """
    Test that we can perform a nested aggregate query
    """
    with sync_db.session() as session:
        SessionStorage.set_session(session)
        sample_1 = SampleFactory(owner_user_id=111, collection_id=888)
        sample_2 = SampleFactory(owner_user_id=111, collection_id=888)
        SequencingReadFactory.create_batch(
            2, sample=sample_1, owner_user_id=sample_1.owner_user_id, collection_id=sample_1.collection_id
        )
        SequencingReadFactory.create_batch(
            3, sample=sample_2, owner_user_id=sample_2.owner_user_id, collection_id=sample_2.collection_id
        )

    query = """
        query MyQuery {
            samples {
                sequencingReadsAggregate {
                    aggregate {
                        count
                    }
                }
            }
        }
    """
    results = await gql_client.query(query, user_id=111, member_projects=[888])
    assert results["data"]["samples"][0]["sequencingReadsAggregate"]["aggregate"][0]["count"] == 2
    assert results["data"]["samples"][1]["sequencingReadsAggregate"]["aggregate"][0]["count"] == 3


@pytest.mark.asyncio
async def test_count_distinct_query(
    sync_db: SyncDB,
    gql_client: GQLTestClient,
) -> None:
    """
    Test that we can perform a count distinct query
    """
    with sync_db.session() as session:
        SessionStorage.set_session(session)
        # Make sure there is at least one sample with water_control=True and one with water_control=False
        SampleFactory(owner_user_id=111, collection_id=888, water_control=True)
        SampleFactory(owner_user_id=111, collection_id=888, water_control=False)
        SampleFactory.create_batch(2, owner_user_id=111, collection_id=888)

    query = """
        query MyQuery {
            samplesAggregate {
                aggregate {
                    count(columns: waterControl)
                }
            }
        }
    """
    results = await gql_client.query(query, user_id=111, member_projects=[888])
    assert results["data"]["samplesAggregate"]["aggregate"][0]["count"] == 4

    query = """
        query MyQuery {
            samplesAggregate {
                aggregate {
                    count(columns: waterControl, distinct: true)
                }
            }
        }
    """
    results = await gql_client.query(query, user_id=111, member_projects=[888])
    assert results["data"]["samplesAggregate"]["aggregate"][0]["count"] == 2


@pytest.mark.asyncio
async def test_groupby_query(
    sync_db: SyncDB,
    gql_client: GQLTestClient,
) -> None:
    """
    Test that we can perform a groupby query
    """
    with sync_db.session() as session:
        SessionStorage.set_session(session)
        SampleFactory.create_batch(2, owner_user_id=111, collection_id=888, collection_location="San Francisco, CA")
        SampleFactory.create_batch(3, owner_user_id=111, collection_id=888, collection_location="Mountain View, CA")

    query = """
        query MyQuery {
            samplesAggregate {
                aggregate {
                    groupBy {
                        collectionLocation
                    }
                    count
                }
            }
        }
    """
    results = await gql_client.query(query, user_id=111, member_projects=[888])
    aggregate = results["data"]["samplesAggregate"]["aggregate"]
    for group in aggregate:
        if group["groupBy"]["collectionLocation"] == "San Francisco, CA":
            assert group["count"] == 2
        elif group["groupBy"]["collectionLocation"] == "Mountain View, CA":
            assert group["count"] == 3


@pytest.mark.asyncio
async def test_groupby_query_with_nested_fields(
    sync_db: SyncDB,
    gql_client: GQLTestClient,
) -> None:
    """
    Test that we can perform a groupby query with nested fields
    """
    with sync_db.session() as session:
        SessionStorage.set_session(session)
        sample_1 = SampleFactory(owner_user_id=111, collection_id=888, collection_location="San Francisco, CA")
        sample_2 = SampleFactory(owner_user_id=111, collection_id=888, collection_location="Mountain View, CA")
        SequencingReadFactory.create_batch(
            2, sample=sample_1, owner_user_id=sample_1.owner_user_id, collection_id=sample_1.collection_id
        )
        SequencingReadFactory.create_batch(
            3, sample=sample_2, owner_user_id=sample_2.owner_user_id, collection_id=sample_2.collection_id
        )

    query = """
        query MyQuery {
            sequencingReadsAggregate {
                aggregate {
                    groupBy {
                        sample {
                            collectionLocation
                        }
                    }
                    count
                }
            }
        }
    """
    results = await gql_client.query(query, user_id=111, member_projects=[888])
    aggregate = results["data"]["sequencingReadsAggregate"]["aggregate"]
    for group in aggregate:
        if group["groupBy"]["sample"]["collectionLocation"] == "San Francisco, CA":
            assert group["count"] == 2
        elif group["groupBy"]["sample"]["collectionLocation"] == "Mountain View, CA":
            assert group["count"] == 3


@pytest.mark.asyncio
async def test_groupby_query_with_multiple_fields(
    sync_db: SyncDB,
    gql_client: GQLTestClient,
) -> None:
    """
    Test that we can perform a groupby query with fields nested at multiple levels
    """
    with sync_db.session() as session:
        SessionStorage.set_session(session)
        sample_1 = SampleFactory(owner_user_id=111, collection_id=888, collection_location="San Francisco, CA")
        sample_2 = SampleFactory(owner_user_id=111, collection_id=888, collection_location="Mountain View, CA")
        SequencingReadFactory.create_batch(
            1,
            sample=sample_1,
            owner_user_id=sample_1.owner_user_id,
            collection_id=sample_1.collection_id,
            technology="Illumina",
        )
        SequencingReadFactory.create_batch(
            2,
            sample=sample_1,
            owner_user_id=sample_1.owner_user_id,
            collection_id=sample_1.collection_id,
            technology="Nanopore",
        )
        SequencingReadFactory.create_batch(
            3,
            sample=sample_2,
            owner_user_id=sample_2.owner_user_id,
            collection_id=sample_2.collection_id,
            technology="Illumina",
        )
        SequencingReadFactory.create_batch(
            4,
            sample=sample_2,
            owner_user_id=sample_2.owner_user_id,
            collection_id=sample_2.collection_id,
            technology="Nanopore",
        )

    query = """
        query MyQuery {
            sequencingReadsAggregate {
                aggregate {
                    groupBy {
                        sample {
                            collectionLocation
                        }
                        technology
                    }
                    count
                }
            }
        }
    """
    results = await gql_client.query(query, user_id=111, member_projects=[888])
    aggregate = results["data"]["sequencingReadsAggregate"]["aggregate"]
    for group in aggregate:
        if (
            group["groupBy"]["sample"]["collectionLocation"] == "San Francisco, CA"
            and group["groupBy"]["technology"] == "Illumina"
        ):
            assert group["count"] == 1
        elif (
            group["groupBy"]["sample"]["collectionLocation"] == "San Francisco, CA"
            and group["groupBy"]["technology"] == "Nanopore"
        ):
            assert group["count"] == 2
        elif (
            group["groupBy"]["sample"]["collectionLocation"] == "Mountain View, CA"
            and group["groupBy"]["technology"] == "Illumina"
        ):
            assert group["count"] == 3
        elif (
            group["groupBy"]["sample"]["collectionLocation"] == "Mountain View, CA"
            and group["groupBy"]["technology"] == "Nanopore"
        ):
            assert group["count"] == 4


@pytest.mark.asyncio
async def test_deeply_nested_groupby_query(
    sync_db: SyncDB,
    gql_client: GQLTestClient,
) -> None:
    """
    Test that we can perform a deeply nested groupby query
    """

    user_id = 12345
    project_id = 123

    with sync_db.session() as session:
        SessionStorage.set_session(session)
        SessionStorage.set_session(session)

        upstream_db_1 = UpstreamDatabaseFactory(owner_user_id=user_id, collection_id=project_id, name="NCBI")
        upstream_db_2 = UpstreamDatabaseFactory(owner_user_id=user_id, collection_id=project_id, name="GTDB")
        contig_1 = ContigFactory(owner_user_id=user_id, collection_id=project_id, upstream_database=upstream_db_1)
        contig_2 = ContigFactory(owner_user_id=user_id, collection_id=project_id, upstream_database=upstream_db_2)
        SequencingReadFactory(owner_user_id=user_id, collection_id=project_id, contigs=contig_1)
        SequencingReadFactory(owner_user_id=user_id, collection_id=project_id, contigs=contig_1)
        SequencingReadFactory(owner_user_id=user_id, collection_id=project_id, contigs=contig_2)
        SequencingReadFactory(owner_user_id=user_id, collection_id=project_id, contigs=contig_2)

    query = """
        query MyQuery {
            sequencingReadsAggregate {
                aggregate {
                    count
                    groupBy {
                        contigs {
                            upstreamDatabase {
                                name
                            }
                        }
                    }
                }
            }
        }
    """
    results = await gql_client.query(query, user_id=user_id, member_projects=[project_id])
    aggregate = results["data"]["sequencingReadsAggregate"]["aggregate"]
    for group in aggregate:
        if group["groupBy"]["contigs"]["upstreamDatabase"]["name"] == "NCBI":
            assert group["count"] == 2
        elif group["groupBy"]["contigs"]["upstreamDatabase"]["name"] == "GTDB":
            assert group["count"] == 2


@pytest.mark.asyncio
async def test_soft_deleted_data_not_in_aggregate_query(
    sync_db: SyncDB,
    gql_client: GQLTestClient,
) -> None:
    """
    Test that soft-deleted data is not included in aggregate queries
    """
    user_id = 12345
    project_id = 123

    # Create mock data
    with sync_db.session() as session:
        SessionStorage.set_session(session)
        SampleFactory.create_batch(
            4, collection_location="San Francisco, CA", owner_user_id=user_id, collection_id=project_id
        )
        sample_to_delete = SampleFactory(
            collection_location="Mountain View, CA", owner_user_id=user_id, collection_id=project_id
        )

    # Verify that there are 5 samples in the database
    aggregate_query = """
        query MyQuery {
            samplesAggregate {
                aggregate {
                    count
                }
            }
        }
    """
    output = await gql_client.query(aggregate_query, user_id=user_id, member_projects=[project_id])
    assert output["data"]["samplesAggregate"]["aggregate"][0]["count"] == 5

    # Soft-delete a sample by updating its deleted_at field
    soft_delete_query = f"""
        mutation MyMutation {{
            updateSample (where: {{ id: {{ _eq: "{sample_to_delete.id}" }} }}, input: {{ deletedAt: "2021-01-01T00:00:00Z" }}) {{
                id
            }}
        }}
    """
    output = await gql_client.query(soft_delete_query, user_id=user_id, member_projects=[project_id])
    assert output["data"]["updateSample"][0]["id"] == str(sample_to_delete.id)

    # The soft-deleted sample should not be included in the aggregate query anymore
    output = await gql_client.query(aggregate_query, user_id=user_id, member_projects=[project_id])
    assert output["data"]["samplesAggregate"]["aggregate"][0]["count"] == 4

    # The soft-deleted sample should be included in the aggregate query if we specifically ask for it
    aggregate_soft_deleted_query = """
        query MyQuery {
            samplesAggregate(where: { deletedAt: { _is_null: false } }) {
                aggregate {
                    count
                }
            }
        }
    """
    output = await gql_client.query(aggregate_soft_deleted_query, user_id=user_id, member_projects=[project_id])
    assert output["data"]["samplesAggregate"]["aggregate"][0]["count"] == 1
