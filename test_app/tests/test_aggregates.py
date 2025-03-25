"""
Test basic queries and mutations
"""

import datetime

import pytest
from tests.helpers import deep_eq

from platformics.database.connect import SyncDB
from platformics.test_infra.factories.base import SessionStorage
from test_infra.factories.homework_assignment import HomeworkAssignmentFactory
from test_infra.factories.homework_score import HomeworkScoreFactory
from test_infra.factories.school import SchoolFactory
from test_infra.factories.district import DistrictFactory
from test_infra.factories.student import StudentFactory

date_now = datetime.datetime.now()


@pytest.mark.asyncio
async def test_simple_aggregate(
    sync_db: SyncDB,
    gql_client,
) -> None:
    """
    Test that we can aggregate and filter by both our own fields *and* 1:many fields, *and* that we don't
    wind up with a cartesian product if there are multiple matches for the related class filter.
    """

    # Create mock data
    auth_args = {"owner_user_id": 10, "collection_id": 10}
    with sync_db.session() as session:
        SessionStorage.set_session(session)
        r1 = SchoolFactory.create(name="001", **auth_args)
        r2 = SchoolFactory.create(name="002", **auth_args)
        # create a school that matches the student filter but not the name filter.
        r3 = SchoolFactory.create(name="012", **auth_args)
        for school in [r1, r2, r3]:
            # important: add *two* smith students for each school!
            StudentFactory.create(school=school, name="jack smith", **auth_args)
            StudentFactory.create(school=school, name="jane smith", **auth_args)
            StudentFactory.create(school=school, name="bob jones", **auth_args)
        # create a school that matches the name filter but not the student filter
        r4 = SchoolFactory.create(name="003", **auth_args)
        StudentFactory.create(school=r4, name="NewSchool", **auth_args)

    # Fetch all schools that have smith students and names starting with "00"
    query = """
        query MyQuery {
            schools (where: {name: {_like: "00%"}, students: {name: {_like: "%smith%"}}}) {
                studentsAggregate {
                    aggregate {
                        count
                    }
                }
            }
        }
    """
    output = await gql_client.query(query, member_projects=[10])
    schools = output["data"]["schools"]
    assert len(schools) == 2
    # I know this looks weird, but this is actually correct!!
    # We've filtered *schools* by students named smith, but for the matching schools
    # we want to count *ALL* students.
    assert schools[0]["studentsAggregate"]["aggregate"][0]["count"] == 3


@pytest.mark.asyncio
async def test_filtered_aggregate(
    sync_db: SyncDB,
    gql_client,
) -> None:
    """
    Test that we can aggregate and filter by both our own fields *and* 1:many fields, *and* that we don't
    wind up with a cartesian product if there are multiple matches for the related class filter.
    """

    # Create mock data
    auth_args = {"owner_user_id": 10, "collection_id": 10}
    with sync_db.session() as session:
        SessionStorage.set_session(session)
        r1 = SchoolFactory.create(name="001", **auth_args)
        r2 = SchoolFactory.create(name="002", **auth_args)
        # create a school that matches the student filter but not the name filter.
        r3 = SchoolFactory.create(name="012", **auth_args)
        for school in [r1, r2, r3]:
            # important: add *two* smith students for each school!
            StudentFactory.create(school=school, name="jack smith", **auth_args)
            StudentFactory.create(school=school, name="jane smith", **auth_args)
            StudentFactory.create(school=school, name="bob jones", **auth_args)
        # create a student that matches the name filter but not the homeworkAssignment filter
        r4 = SchoolFactory.create(name="003", **auth_args)
        StudentFactory.create(school=r4, name="jackie jee", **auth_args)

    # Fetch all schools that have smith students and names starting with "00"
    query = """
        query MyQuery {
            schoolsAggregate (where: {name: {_like: "00%"}, students: {name: {_like: "%smith%"}}}) {
                aggregate {
                  count
                }
            }
        }
    """
    output = await gql_client.query(query, member_projects=[10])
    students = output["data"]["schoolsAggregate"]
    assert len(students) == 1
    assert students["aggregate"][0]["count"] == 2


@pytest.mark.asyncio
async def test_onetomany_groupby_aggregate(
    sync_db: SyncDB,
    gql_client,
) -> None:
    """
    Test that we can group aggregates on 1:many relationships.
    """

    # Create mock data
    auth_args = {"owner_user_id": 10, "collection_id": 10}
    with sync_db.session() as session:
        SessionStorage.set_session(session)
        dis1 = DistrictFactory.create(**auth_args)
        dis2 = DistrictFactory.create(**auth_args)
        sch1 = SchoolFactory.create(district=dis1, **auth_args)
        sch2 = SchoolFactory.create(district=dis2, **auth_args)
        sch3 = SchoolFactory.create(district=dis2, **auth_args)

        StudentFactory.create(name="alice", school=sch1, **auth_args)
        StudentFactory.create(name="bob", school=sch1, **auth_args)

        StudentFactory.create(name="alice", school=sch2, **auth_args)
        StudentFactory.create(name="catherine", school=sch2, **auth_args)

        StudentFactory.create(name="alice", school=sch3, **auth_args)
        StudentFactory.create(name="bob", school=sch3, **auth_args)

    query = """
        query MyQuery {
            districts {
                id
                schoolsAggregate {
                    aggregate {
                        count(columns: id)
                        groupBy {
                            students {
                                name
                            }
                        }
                    }
                }
            }
        }
    """
    output = await gql_client.query(query, member_projects=[10])
    dis1_expected = [
        {"count": 1, "groupBy": {"students": {"name": "alice"}}},
        {"count": 1, "groupBy": {"students": {"name": "bob"}}},
    ]
    dis2_expected = [
        {"count": 2, "groupBy": {"students": {"name": "alice"}}},
        {"count": 1, "groupBy": {"students": {"name": "bob"}}},
        {"count": 1, "groupBy": {"students": {"name": "catherine"}}},
    ]
    districts = output["data"]["districts"]
    assert len(districts) == 2
    gql_dep_1 = [item for item in districts if item["id"] == dis1.id].pop()
    gql_dep_2 = [item for item in districts if item["id"] == dis2.id].pop()

    dis1_actual = sorted(gql_dep_1["schoolsAggregate"]["aggregate"], key=lambda x: x["groupBy"]["students"]["name"])
    dis2_actual = sorted(gql_dep_2["schoolsAggregate"]["aggregate"], key=lambda x: x["groupBy"]["students"]["name"])

    assert deep_eq(dis1_actual, dis1_expected)
    assert deep_eq(dis2_actual, dis2_expected)


@pytest.mark.asyncio
async def test_manytoone_groupby_aggregate(
    sync_db: SyncDB,
    gql_client,
) -> None:
    """
    Test that we can group aggregates on many:1 relationships.
    """

    # Create mock data
    auth_args = {"owner_user_id": 10, "collection_id": 10}
    with sync_db.session() as session:
        SessionStorage.set_session(session)
        dis1 = DistrictFactory.create(**auth_args)
        dis2 = DistrictFactory.create(**auth_args)
        sch1 = SchoolFactory.create(district=dis1, **auth_args)
        sch2 = SchoolFactory.create(district=dis2, **auth_args)

        StudentFactory.create(name="alice", school=sch1, **auth_args)
        StudentFactory.create(name="bob", school=sch1, **auth_args)

        StudentFactory.create(name="alice", school=sch2, **auth_args)
        StudentFactory.create(name="bob", school=sch2, **auth_args)
        StudentFactory.create(name="catherine", school=sch2, **auth_args)

    query = """
        query MyQuery {
            schools {
                id
                studentsAggregate {
                    aggregate {
                        count(columns: id)
                        groupBy {
                            school {
                              district {
                                id
                              }
                            }
                        }
                    }
                }
            }
        }
    """
    output = await gql_client.query(query, member_projects=[10])

    dis1_expected = [
        {"count": 2, "groupBy": {"school": {"district": {"id": dis1.id}}}},
    ]
    dis2_expected = [
        {"count": 3, "groupBy": {"school": {"district": {"id": dis2.id}}}},
    ]
    schools = output["data"]["schools"]
    assert len(schools) == 2
    gql_dep_1 = [item for item in schools if item["id"] == sch1.id].pop()
    gql_dep_2 = [item for item in schools if item["id"] == sch2.id].pop()

    dis1_actual = sorted(
        gql_dep_1["studentsAggregate"]["aggregate"], key=lambda x: x["groupBy"]["school"]["district"]["id"]
    )
    dis2_actual = sorted(
        gql_dep_2["studentsAggregate"]["aggregate"], key=lambda x: x["groupBy"]["school"]["district"]["id"]
    )

    assert deep_eq(dis1_actual, dis1_expected)
    assert deep_eq(dis2_actual, dis2_expected)


@pytest.mark.asyncio
async def test_group_by_custom_relationship_field_names(
    sync_db: SyncDB,
    gql_client,
) -> None:
    """
    The relationship between HomeworkAssignment and HomeworkScore is called HomeworkAssignment.scores rather
    than HomeworkAssignment.homework_scores There was a bug where the groupby output processing was assuming
    that related group_by fields in our SQL queries would be named with the remote TABLE name instead of the
    RELATIONSHIP field name. This test ensures that we're deserializing query outputs properly when table
    names and field names don't match.
    """

    # Create mock data
    auth_args = {"owner_user_id": 10, "collection_id": 10}
    with sync_db.session() as session:
        SessionStorage.set_session(session)
        d1 = HomeworkAssignmentFactory.create(**auth_args)
        HomeworkScoreFactory.create(homework_assignment=d1, score_type="Penmanship", score_value=111, **auth_args)
        HomeworkScoreFactory.create(homework_assignment=d1, score_type="Composition", score_value=222, **auth_args)
        d2 = HomeworkAssignmentFactory.create(**auth_args)
        HomeworkScoreFactory.create(homework_assignment=d2, score_type="Composition", score_value=222, **auth_args)
        HomeworkScoreFactory.create(homework_assignment=d2, score_type="Content", score_value=333, **auth_args)

    # Fetch all schools that have at least one student
    query = """
        query MyQuery {
          homeworkAssignmentsAggregate {
            aggregate {
              count
              groupBy {
                scores {
                  scoreType
                  scoreValue
                }
              }
            }
          }
        }
    """
    output = await gql_client.query(query, member_projects=[10])
    expected = [
        {"count": 2, "groupBy": {"scores": {"scoreType": "Composition", "scoreValue": 222}}},
        {"count": 1, "groupBy": {"scores": {"scoreType": "Content", "scoreValue": 333}}},
        {"count": 1, "groupBy": {"scores": {"scoreType": "Penmanship", "scoreValue": 111}}},
    ]
    sorted_output = sorted(
        output["data"]["homeworkAssignmentsAggregate"]["aggregate"],
        key=lambda x: x["groupBy"]["scores"]["scoreType"],
    )
    assert deep_eq(sorted_output, expected)
