"""
Test basic queries and mutations
"""

import datetime

import pytest
from tests.helpers import deep_eq

from platformics.database.connect import SyncDB
from platformics.test_infra.factories.base import SessionStorage
from test_infra.factories.school import SchoolFactory
from test_infra.factories.district import DistrictFactory

date_now = datetime.datetime.now()


@pytest.mark.asyncio
async def test_top_meta_fields_aggregate(
    sync_db: SyncDB,
    gql_client,
) -> None:
    """
    Test that we can include gql meta fields at each level of an aggregate query
    """

    # Create mock data
    auth_args = {"owner_user_id": 10, "collection_id": 10}
    with sync_db.session() as session:
        SessionStorage.set_session(session)
        DistrictFactory.create(id=12345, **auth_args)
        DistrictFactory.create(id=23456, **auth_args)
        DistrictFactory.create(id=34567, **auth_args)

    # Fetch all schools that have at least one run
    query = """
        query MyQuery {
          districtsAggregate {
            __typename
            aggregate {
              __typename
              count(columns: id)
              groupBy {
                __typename
                id
              }
            }
          }
        }
    """
    output = await gql_client.query(query, member_projects=[10])
    assert output["data"]["districtsAggregate"]["__typename"] == "DistrictAggregate"
    aggregates = output["data"]["districtsAggregate"]["aggregate"]
    assert len(aggregates) == 3
    dep_ids = {12345, 23456, 34567}
    for item in aggregates:
        assert item["__typename"] == "DistrictAggregateFunctions"
        assert item["count"] == 1
        assert item["groupBy"]["__typename"] == "DistrictGroupByOptions"
        assert item["groupBy"]["id"] in dep_ids


@pytest.mark.asyncio
async def test_nested_meta_fields_aggregate(
    sync_db: SyncDB,
    gql_client,
) -> None:
    """
    Test that we can include gql meta fields at each level of a nested aggregate query
    """

    # Create mock data
    auth_args = {"owner_user_id": 10, "collection_id": 10}
    with sync_db.session() as session:
        SessionStorage.set_session(session)
        d1 = DistrictFactory.create(id=12345, **auth_args)
        SchoolFactory.create(district=d1, id=222, **auth_args)

    # Fetch all schools that have at least one run
    query = """
        query MyQuery {
          districts {
            __typename
            id
            schoolsAggregate {
              __typename
              aggregate {
                __typename
                count(columns: id, distinct: true)
                sum {
                  __typename
                  id
                }
                groupBy {
                  __typename
                  id
                }
              }
            }
          }
        }
    """
    output = await gql_client.query(query, member_projects=[10])
    assert len(output["data"]["districts"]) == 1
    aggregate = output["data"]["districts"][0]
    assert aggregate["__typename"] == "District"
    assert aggregate["id"] == 12345

    agg_info = aggregate["schoolsAggregate"]
    assert agg_info["__typename"] == "SchoolAggregate"
    assert len(agg_info["aggregate"]) == 1

    agg_data = agg_info["aggregate"][0]
    assert agg_data["__typename"] == "SchoolAggregateFunctions"
    assert agg_data["count"] == 1
    assert agg_data["sum"]["__typename"] == "SchoolNumericalColumns"
    assert agg_data["sum"]["id"] == 222
    assert agg_data["groupBy"]["__typename"] == "SchoolGroupByOptions"
    assert agg_data["groupBy"]["id"] == 222


@pytest.mark.asyncio
async def test_nested_meta_fields_resolver(
    sync_db: SyncDB,
    gql_client,
) -> None:
    """
    Test that we can include gql meta fields at each level of a nested NON-aggregate query
    """

    # Create mock data
    auth_args = {"owner_user_id": 10, "collection_id": 10}
    with sync_db.session() as session:
        SessionStorage.set_session(session)
        d1 = DistrictFactory.create(id=12345, **auth_args)
        SchoolFactory.create(district=d1, id=222, **auth_args)

    # Fetch all schools that have at least one run
    query = """
        query MyQuery {
          districts {
            __typename
            id
            schools {
              __typename
              edges {
                __typename
                node {
                  __typename
                  id
                  district {
                    __typename
                    id
                  }
                }
              }
            }
          }
        }
    """
    output = await gql_client.query(query, member_projects=[10])

    expected = {
        "data": {
            "districts": [
                {
                    "__typename": "District",
                    "id": 12345,
                    "schools": {
                        "__typename": "SchoolConnection",
                        "edges": [
                            {
                                "__typename": "SchoolEdge",
                                "node": {
                                    "__typename": "School",
                                    "id": 222,
                                    "district": {
                                        "__typename": "District",
                                        "id": 12345,
                                    },
                                },
                            },
                        ],
                    },
                },
            ],
        },
    }
    assert deep_eq(output, expected)
