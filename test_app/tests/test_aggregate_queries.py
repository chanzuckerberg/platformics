"""
Test aggregate queries
"""

import pytest
from platformics.database.connect import SyncDB
from platformics.codegen.conftest import GQLTestClient, SessionStorage
from platformics.codegen.tests.output.test_infra.factories.sample import SampleFactory
from platformics.codegen.tests.output.test_infra.factories.sequencing_read import SequencingReadFactory


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
    avg_collectionId = output["data"]["samplesAggregate"]["aggregate"]["avg"]["collectionId"]
    count = output["data"]["samplesAggregate"]["aggregate"]["count"]
    max_collectionLocation = output["data"]["samplesAggregate"]["aggregate"]["max"]["collectionLocation"]
    min_collectionLocation = output["data"]["samplesAggregate"]["aggregate"]["min"]["collectionLocation"]
    stddev_collectionId = output["data"]["samplesAggregate"]["aggregate"]["stddev"]["collectionId"]
    sum_ownerUserId = output["data"]["samplesAggregate"]["aggregate"]["sum"]["ownerUserId"]
    
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
        SequencingReadFactory.create_batch(2, sample=sample_1, owner_user_id=sample_1.owner_user_id, collection_id=sample_1.collection_id)
        SequencingReadFactory.create_batch(3, sample=sample_2, owner_user_id=sample_2.owner_user_id, collection_id=sample_2.collection_id)

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
    assert results["data"]["samples"][0]["sequencingReadsAggregate"]["aggregate"]["count"] == 2
    assert results["data"]["samples"][1]["sequencingReadsAggregate"]["aggregate"]["count"] == 3

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
                    count(columns: water_control)
                }
            }
        }
    """
    results = await gql_client.query(query, user_id=111, member_projects=[888])
    assert results["data"]["samplesAggregate"]["aggregate"]["count"] == 4

    query = """
        query MyQuery {
            samplesAggregate {
                aggregate {
                    count(columns: water_control, distinct: true)
                }
            }
        }
    """
    results = await gql_client.query(query, user_id=111, member_projects=[888])
    assert results["data"]["samplesAggregate"]["aggregate"]["count"] == 2
