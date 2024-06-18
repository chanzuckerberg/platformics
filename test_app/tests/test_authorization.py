"""
Authorization spot-checks
"""

import uuid

import pytest
from database.models import Sample
from conftest import GQLTestClient, SessionStorage
from test_infra.factories.sample import SampleFactory
from test_infra.factories.sequencing_read import SequencingReadFactory
from platformics.database.connect import SyncDB


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "project_ids,num_results,cities",
    [([], 0, ()), ([333], 2, {"City1"}), ([333, 555], 4, {"City1", "City3"})],
)
async def test_collection_authorization(
    project_ids: list[int],
    num_results: int,
    cities: tuple[str],
    sync_db: SyncDB,
    gql_client: GQLTestClient,
) -> None:
    """
    Make sure users can only see samples in collections they have access to.
    """
    owner_user_id = 333
    user_id = 12345

    # Create mock data
    with sync_db.session() as session:
        SessionStorage.set_session(session)
        SampleFactory.create_batch(2, collection_location="City1", owner_user_id=owner_user_id, collection_id=333)
        SampleFactory.create_batch(2, collection_location="City2", owner_user_id=owner_user_id, collection_id=444)
        SampleFactory.create_batch(2, collection_location="City3", owner_user_id=owner_user_id, collection_id=555)

    # Fetch all samples
    query = """
        query MyQuery {
            samples {
                id
                collectionLocation
            }
        }
    """
    output = await gql_client.query(query, user_id=user_id, member_projects=project_ids)
    assert len(output["data"]["samples"]) == num_results
    assert {sample["collectionLocation"] for sample in output["data"]["samples"]} == set(cities)


@pytest.mark.asyncio
async def test_system_fields_only_creatable_by_system(
    gql_client: GQLTestClient,
) -> None:
    """
    Make sure only system users can set system fields
    """
    user_id = 12345
    project_ids = [333]
    producing_run_id = str(uuid.uuid4())
    query = f"""
        mutation MyMutation {{
          createGenomicRange(input: {{collectionId: {project_ids[0]}, producingRunId: "{producing_run_id}" }}) {{
            collectionId
            producingRunId
          }}
        }}
    """

    # Our mutation should have been saved because we are a system user.
    output = await gql_client.query(query, user_id=user_id, member_projects=project_ids, service_identity="workflows")
    assert output["data"]["createGenomicRange"]["collectionId"] == 333
    assert output["data"]["createGenomicRange"]["producingRunId"] == producing_run_id

    # Our mutation should have ignored producing run because we're not a system user.
    output = await gql_client.query(query, user_id=user_id, member_projects=project_ids)
    assert output["data"]["createGenomicRange"]["collectionId"] == 333
    assert output["data"]["createGenomicRange"]["producingRunId"] is None


@pytest.mark.asyncio
async def test_system_fields_only_mutable_by_system(
    sync_db: SyncDB,
    gql_client: GQLTestClient,
) -> None:
    """
    Make sure only system users can mutate system fields
    """
    user_id = 12345
    project_ids = [333]

    with sync_db.session() as session:
        SessionStorage.set_session(session)
        sample = SampleFactory.create(collection_location="City1", owner_user_id=999, collection_id=333)

    # Fetch all samples
    def get_query(input_value: str) -> str:
        return f"""
            mutation MyMutation {{
              updateSample(
                  where: {{id: {{_eq: "{sample.id}" }} }},
                  input: {{systemMutableField: "{input_value}"}}) {{
                id
                systemMutableField
              }}
            }}
        """

    output = await gql_client.query(
        get_query("hello"), user_id=user_id, member_projects=project_ids, service_identity="workflows"
    )
    # Our mutation should have been saved because we are a system user.
    assert output["data"]["updateSample"][0]["systemMutableField"] == "hello"

    output = await gql_client.query(get_query("goodbye"), user_id=user_id, member_projects=project_ids)
    # This field should have been ignored because we're not a system user
    assert output["data"]["updateSample"][0]["systemMutableField"] == "hello"


@pytest.mark.asyncio
async def test_system_types_only_mutable_by_system(
    sync_db: SyncDB,
    gql_client: GQLTestClient,
) -> None:
    """
    Make sure only system users can mutate system fields
    """
    user_id = 12345
    project_ids = [333]

    # Fetch all samples
    def get_update_query(id: str, input_value: str) -> str:
        return f"""
            mutation MyMutation {{
              updateSystemWritableOnlyType(
                  where: {{id: {{_eq: "{id}" }} }},
                  input: {{name: "{input_value}"}}) {{
                id
                name
              }}
            }}
        """

    # Fetch all samples
    create_query = """
        mutation MyMutation {
          createSystemWritableOnlyType(
            input: {
              collectionId: 333,
              name: "row name here"
            }
          ) { id, name }
        }
    """

    # Our mutation should have been saved because we are a system user.
    output = await gql_client.query(
        create_query, user_id=user_id, member_projects=project_ids, service_identity="workflows"
    )
    assert output["data"]["createSystemWritableOnlyType"]["name"] == "row name here"
    item_id = output["data"]["createSystemWritableOnlyType"]["id"]

    # Our mutation should have failed with an authorization error because we are not a system user
    output = await gql_client.query(create_query, user_id=user_id, member_projects=project_ids)
    assert "Unauthorized" in output["errors"][0]["message"]
    assert "not creatable" in output["errors"][0]["message"]

    # This field should have been ignored because we're not a system user
    output = await gql_client.query(get_update_query(item_id, "new_name"), user_id=user_id, member_projects=project_ids)
    assert "Unauthorized" in output["errors"][0]["message"]
    assert "not mutable" in output["errors"][0]["message"]

    # This field should have been ignored because we're not a system user
    output = await gql_client.query(
        get_update_query(item_id, "new_name"),
        user_id=user_id,
        member_projects=project_ids,
        service_identity="workflows",
    )
    assert output["data"]["updateSystemWritableOnlyType"][0]["name"] == "new_name"


@pytest.mark.asyncio
async def test_update_wont_associate_inaccessible_relationships(
    sync_db: SyncDB,
    gql_client: GQLTestClient,
) -> None:
    """
    Make sure users can only see samples in collections they have access to.
    """
    owner_user_id = 333
    user_id = 12345

    # Create mock data
    with sync_db.session() as session:
        SessionStorage.set_session(session)
        test_sample0 = SampleFactory.create(collection_location="City1", owner_user_id=999, collection_id=444)
        test_sample1 = SampleFactory.create(collection_location="City2", owner_user_id=999, collection_id=444)
        test_sample2 = SampleFactory.create(collection_location="City3", owner_user_id=999, collection_id=444)
        test_sample3 = SampleFactory.create(collection_location="City4", owner_user_id=999, collection_id=444)
        test_sequencing_read = SequencingReadFactory.create(
            sample=test_sample0, owner_user_id=owner_user_id, collection_id=111
        )

    def gen_query(test_sample: Sample) -> str:
        # Fetch all samples
        query = f"""
            mutation MyMutation {{
              updateSequencingRead(
                where: {{id: {{_eq: "{test_sequencing_read.id}"}} }},
                input: {{
                  sampleId: "{test_sample.id}"
                }}
              ) {{
                id
                sample {{
                  id
                }}
              }}
            }}
        """
        return query

    # We are a member of 444 so this should work.
    output = await gql_client.query(gen_query(test_sample1), user_id=user_id, member_projects=[111, 444])
    assert output["data"]["updateSequencingRead"][0]["sample"]["id"] == str(test_sample1.id)

    # We are NOT a member of 444 so this should break.
    output = await gql_client.query(gen_query(test_sample2), user_id=user_id, member_projects=[111, 555])
    assert "Unauthorized" in output["errors"][0]["message"]

    # Project 444 is public so this should work
    output = await gql_client.query(
        gen_query(test_sample3), user_id=user_id, member_projects=[111, 555], viewer_projects=[444]
    )
    assert output["data"]["updateSequencingRead"][0]["sample"]["id"] == str(test_sample3.id)


@pytest.mark.asyncio
async def test_create_wont_associate_inaccessible_relationships(
    sync_db: SyncDB,
    gql_client: GQLTestClient,
) -> None:
    """
    Make sure users can only see samples in collections they have access to.
    """
    owner_user_id = 333
    user_id = 12345

    # Create mock data
    with sync_db.session() as session:
        SessionStorage.set_session(session)
        test_sample = SampleFactory.create(collection_location="City2", owner_user_id=owner_user_id, collection_id=444)

    # Fetch all samples
    query = f"""
        mutation MyMutation {{
          createSequencingRead(
            input: {{
              collectionId: 111,
              sampleId: "{test_sample.id}",
              protocol: MNGS,
              technology: Illumina,
              nucleicAcid: RNA,
            }}
          ) {{ id }}
        }}
    """
    # We are a member of 444 so this should work.
    output = await gql_client.query(query, user_id=user_id, member_projects=[111, 444])
    assert output["data"]["createSequencingRead"]["id"]

    # We are NOT a member of 444 so this should break.
    output = await gql_client.query(query, user_id=user_id, member_projects=[111, 555])
    assert "Unauthorized" in output["errors"][0]["message"]

    # Project 444 is public so this should work
    output = await gql_client.query(query, user_id=user_id, member_projects=[111, 555], viewer_projects=[444])
    assert output["data"]["createSequencingRead"]["id"]
