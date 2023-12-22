"""
Tests for nested queries + authorization
"""

import base64
import pytest
from collections import defaultdict
from platformics.database.connect import SyncDB
from platformics.codegen.conftest import GQLTestClient, SessionStorage
from platformics.codegen.tests.output.test_infra.factories.sample import SampleFactory
from platformics.codegen.tests.output.test_infra.factories.sequencing_read import SequencingReadFactory
from api.types.entities import Entity


def get_id(entity: Entity) -> str:
    entity_type = entity.__class__.__name__
    node_id = f"{entity_type}:{entity.id}".encode("ascii")
    node_id_b64 = base64.b64encode(node_id).decode("utf-8")
    return node_id_b64


@pytest.mark.asyncio
async def test_nested_query(
    sync_db: SyncDB,
    gql_client: GQLTestClient,
) -> None:
    """
    Fetch sequencing reads and their associated sample (1:1)
    """
    with sync_db.session() as session:
        SessionStorage.set_session(session)
        sequencing_reads = SequencingReadFactory.create_batch(5, owner_user_id=111, collection_id=888)

    # Nested query with 1:1 relationship so don't use relay-style edges/node
    query = """
        query MyQuery {
          sequencingReads {
            id
            protocol
            technology
            sample {
              id
              name
              collectionLocation
            }
          }
        }
    """
    results = await gql_client.query(query, user_id=111, member_projects=[888])
    for i in range(len(sequencing_reads)):
        assert results["data"]["sequencingReads"][i]["id"] == str(sequencing_reads[i].id)
        assert results["data"]["sequencingReads"][i]["sample"]["name"] == sequencing_reads[i].sample.name


@pytest.mark.asyncio
async def test_nested_query_relay(
    sync_db: SyncDB,
    gql_client: GQLTestClient,
) -> None:
    """
    Fetch samples and their associated sequencing reads (1:M)
    """
    user1_id = 111
    user2_id = 222
    project1_id = 888
    project2_id = 999

    # Create mock data
    with sync_db.session() as session:
        SessionStorage.set_session(session)
        # create some samples with multiple SequencingReads
        sa1 = SampleFactory(owner_user_id=user1_id, collection_id=project1_id)
        sa2 = SampleFactory(owner_user_id=user2_id, collection_id=project1_id)
        sa3 = SampleFactory(owner_user_id=user2_id, collection_id=project2_id)

        seq1 = SequencingReadFactory.create_batch(
            3, sample=sa1, owner_user_id=sa1.owner_user_id, collection_id=sa1.collection_id
        )
        seq2 = SequencingReadFactory.create_batch(
            2,
            sample=sa2,
            owner_user_id=sa2.owner_user_id,
            collection_id=sa2.collection_id,
        )
        SequencingReadFactory.create_batch(
            2,
            sample=sa3,
            owner_user_id=sa3.owner_user_id,
            collection_id=sa3.collection_id,
        )

    # Fetch samples and nested sequencing reads AND nested samples again!
    query = """
        query MyQuery {
          samples {
            id
            name
            collectionLocation
            ownerUserId
            collectionId
            sequencingReads(where: { collectionId: { _eq: 888 } }) {
              edges {
                node {
                  collectionId
                  ownerUserId
                  protocol
                  nucleicAcid
                  sample {
                    id
                    ownerUserId
                    collectionId
                    name
                    sequencingReads {
                      edges {
                        node {
                          protocol
                        }
                      }
                    }
                  }
                }
              }
            }
          }
        }
    """

    # Make sure user1 can only see samples from project1
    results = await gql_client.query(query, user_id=user1_id, member_projects=[project1_id])
    expected_sequences_by_owner = {user1_id: len(seq1), user2_id: len(seq2)}
    actual_samples_by_owner: dict[int, int] = defaultdict(int)
    actual_sequences_by_owner: dict[int, int] = defaultdict(int)
    for sample in results["data"]["samples"]:
        assert sample["collectionId"] == project1_id
        actual_samples_by_owner[sample["ownerUserId"]] += 1
        actual_sequences_by_owner[sample["ownerUserId"]] = len(sample["sequencingReads"]["edges"])
        assert sample["sequencingReads"]["edges"][0]["node"]["sample"]["id"] == sample["id"]

    for userid in expected_sequences_by_owner:
        assert actual_sequences_by_owner[userid] == expected_sequences_by_owner[userid]
    for userid in [user1_id, user2_id]:
        assert actual_samples_by_owner[userid] == 1


@pytest.mark.asyncio
async def test_relay_node_queries(
    sync_db: SyncDB,
    gql_client: GQLTestClient,
) -> None:
    """
    Use Relay-style node queries
    """
    with sync_db.session() as session:
        SessionStorage.set_session(session)
        sample1 = SampleFactory(owner_user_id=111, collection_id=888)
        sample2 = SampleFactory(owner_user_id=111, collection_id=888)
        sequencing_read = SequencingReadFactory(sample=sample1, owner_user_id=111, collection_id=888)
        sample1_id = get_id(sample1)
        sample2_id = get_id(sample2)
        sequencing_read_id = get_id(sequencing_read)

    # Fetch one node
    query = f"""
        query MyQuery {{
          node(id: "{sample1_id}") {{
            ... on Sample {{
              name
            }}
          }}
        }}
    """
    results = await gql_client.query(query, user_id=111, member_projects=[888])
    assert results["data"]["node"]["name"] == sample1.name

    # Fetch multiple nodes
    query = f"""
        query MyQuery {{
          nodes(ids: ["{sample1_id}", "{sample2_id}"]) {{
            ... on Sample {{
              name
            }}
          }}
        }}
    """
    results = await gql_client.query(query, user_id=111, member_projects=[888])
    assert results["data"]["nodes"][0]["name"] == sample1.name
    assert results["data"]["nodes"][1]["name"] == sample2.name

    # Fetch multiple nodes of different types
    query = f"""
        query MyQuery {{
          nodes(ids: ["{sample1_id}", "{sample2_id}", "{sequencing_read_id}"]) {{
            ... on Sample {{
              name
            }}
            ... on SequencingRead {{
              technology
            }}
          }}
        }}
    """
    results = await gql_client.query(query, user_id=111, member_projects=[888])
    assert results["data"]["nodes"][0]["name"] == sample1.name
    assert results["data"]["nodes"][1]["name"] == sample2.name
    assert results["data"]["nodes"][2]["technology"] == sequencing_read.technology
