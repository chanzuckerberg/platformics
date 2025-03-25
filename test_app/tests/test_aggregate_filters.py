"""
Test basic queries and mutations
"""

import datetime

import pytest

from platformics.database.connect import SyncDB
from platformics.test_infra.factories.base import SessionStorage
from test_infra.factories.school import SchoolFactory
from test_infra.factories.district import DistrictFactory
from test_infra.factories.student import StudentFactory

date_now = datetime.datetime.now()


@pytest.mark.asyncio
async def test_simple_aggregate_filter(
    sync_db: SyncDB,
    gql_client,
) -> None:
    """
    Test that we can filter school by the number of students they have
    """

    # Create mock data
    auth_args = {"owner_user_id": 10, "collection_id": 10}
    with sync_db.session() as session:
        SessionStorage.set_session(session)
        d1 = SchoolFactory.create(id=12345, **auth_args)
        d2 = SchoolFactory.create(id=23456, **auth_args)
        d3 = SchoolFactory.create(id=34567, **auth_args)
        SchoolFactory.create(id=45678, **auth_args)  # Just extra data that shouldn't be included by default.
        StudentFactory.create_batch(3, school=d1, name="__first__", **auth_args)
        StudentFactory.create_batch(6, school=d2, name="__second__", **auth_args)
        StudentFactory.create_batch(9, school=d3, name="__third__", **auth_args)

    # Fetch all schools that have at least one student
    query = """
        query MyQuery {
            schools(
                where: {studentsAggregate: {count: {predicate: {_gt: 0}}}}
            ) {
                id
            }
        }
    """
    output = await gql_client.query(query, member_projects=[10])
    result_ids = {item["id"] for item in output["data"]["schools"]}
    assert result_ids == {12345, 23456, 34567}

    # Fetch all schools that have between 4 and 8 students
    query = """
        query MyQuery {
            schools(
                where: {studentsAggregate: {count: {predicate: {_gt: 3, _lt: 9}}}}
            ) {
                id
            }
        }
    """
    output = await gql_client.query(query, member_projects=[10])
    result_ids = {item["id"] for item in output["data"]["schools"]}
    assert result_ids == {23456}

    # Fetch schools that <= 1 student whose name is like "second"
    query = """
        query MyQuery {
            schools(
              where: {studentsAggregate: {count: {
                predicate: {_eq: 1},
                distinct: true,
                arguments: name,
                filter: {name: {_like: "%second%"}}}
              }}
            ) {
              id
            }
        }
    """
    output = await gql_client.query(query, member_projects=[10])
    result_ids = {item["id"] for item in output["data"]["schools"]}
    assert result_ids == {23456}


@pytest.mark.asyncio
async def test_nested_aggregate_filter(
    sync_db: SyncDB,
    gql_client,
) -> None:
    """
    Test that we can filter districts by the number of students in schools
    """

    # Create mock data
    auth_args = {"owner_user_id": 10, "collection_id": 10}
    with sync_db.session() as session:
        SessionStorage.set_session(session)
        dep1 = DistrictFactory(id=111, **auth_args)
        dep2 = DistrictFactory(id=222, **auth_args)
        dep3 = DistrictFactory(id=333, **auth_args)
        d1 = SchoolFactory.create(id=12345, district=dep1, **auth_args)
        d2 = SchoolFactory.create(id=23456, district=dep2, **auth_args)
        d3 = SchoolFactory.create(id=34567, district=dep3, **auth_args)  # Two schools with the same district
        d4 = SchoolFactory.create(id=45678, district=dep3, **auth_args)  # Two schools with the same district
        StudentFactory.create_batch(3, school=d1, name="__first__", **auth_args)
        StudentFactory.create_batch(6, school=d2, name="__second__", **auth_args)
        StudentFactory.create_batch(9, school=d3, name="__third__", **auth_args)
        StudentFactory.create_batch(1, school=d4, name="__fourth__", **auth_args)

    # Fetch all districts that have schools with 9 students
    query = """
        query MyQuery($_num_students: Int = 9) {
          districts(
            where: {schools: {studentsAggregate: {count: {predicate: {_eq: $_num_students}}}}}
          ) {
            id
          }
        }
    """
    output = await gql_client.query(query, member_projects=[10])
    district_ids = {item["id"] for item in output["data"]["districts"]}
    assert district_ids == {333}
