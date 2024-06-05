"""
Test basic queries and mutations
"""

import datetime

import pytest
from conftest import GQLTestClient

date_now = datetime.datetime.now()


@pytest.mark.asyncio
async def test_hidden_fields(
    gql_client: GQLTestClient,
) -> None:
    """
    Test that we can hide fields from the GQL interface
    """
    user_id = 12345
    project_id = 123

    # Introspect the GenomicRange type
    query = """
        query MyQuery {
          __type(name: "GenomicRange") {
            name
            fields {
              name
              type {
                name
                kind
              }
            }
          }
        }
    """
    output = await gql_client.query(query, user_id=user_id, member_projects=[project_id])
    field_names = [field["name"] for field in output["data"]["__type"]["fields"]]

    # entityId is a hidden field, make sure it's not part if our type def.
    assert "entityId" not in field_names

    # ownerUserId is a regular field inherited from Entity, make sure we can see it.
    assert "ownerUserId" in field_names

    # file is a regular field on the GR table, make sure we can see it.
    assert "file" in field_names
    assert "fileId" in field_names


@pytest.mark.asyncio
async def test_hidden_mutations(
    gql_client: GQLTestClient,
) -> None:
    """
    Test that we don't generate mutations unless they make sense
    """
    user_id = 12345
    project_id = 123

    # Introspect the Mutations fields
    query = """
        query MyQuery {
          __schema {
            mutationType {
              fields {
                name
              }
            }
          }
        }
    """
    output = await gql_client.query(query, user_id=user_id, member_projects=[project_id])
    mutations = [field["name"] for field in output["data"]["__schema"]["mutationType"]["fields"]]

    # ImmutableType has `mutable: false` set on the entire table so it shouldn't have a mutation
    assert "updateImmutableType" not in mutations

    # ImmutableType still allows creation.
    assert "createImmutableType" in mutations


# Make sure we only allow certain fields to be set at entity creation time.
@pytest.mark.asyncio
async def test_update_fields(
    gql_client: GQLTestClient,
) -> None:
    """
    Test that we don't show immutable fields in update mutations.
    """
    user_id = 12345
    project_id = 123

    # Introspect the Mutations fields
    query = """
        fragment FullType on __Type {
          kind
          name
          inputFields {
            ...InputValue
          }
        }
        fragment InputValue on __InputValue {
          name
          type {
            ...TypeRef
          }
          defaultValue
        }
        fragment TypeRef on __Type {
          kind
          name
          ofType {
            kind
            name
          }
        }
        query IntrospectionQuery {
          __schema {
            types {
              ...FullType
            }
          }
       }
    """
    output = await gql_client.query(query, user_id=user_id, member_projects=[project_id])
    create_type = [item for item in output["data"]["__schema"]["types"] if item["name"] == "SequencingReadUpdateInput"][
        0
    ]
    fields = [field["name"] for field in create_type["inputFields"]]
    # We have a limited subset of mutable fields on SequencingRead
    assert set(fields) == set(["nucleicAcid", "clearlabsExport", "technology", "sampleId", "deletedAt"])


# Make sure we only allow certain fields to be set at entity creation time.
@pytest.mark.asyncio
async def test_creation_fields(
    gql_client: GQLTestClient,
) -> None:
    """
    Test that we don't generate mutations unless they actually do something
    """
    user_id = 12345
    project_id = 123

    # Introspect the Mutations fields
    query = """
        fragment FullType on __Type {
          kind
          name
          inputFields {
            ...InputValue
          }
        }
        fragment InputValue on __InputValue {
          name
          type {
            ...TypeRef
          }
          defaultValue
        }
        fragment TypeRef on __Type {
          kind
          name
          ofType {
            kind
            name
          }
        }
        query IntrospectionQuery {
          __schema {
            types {
              ...FullType
            }
          }
       }
    """
    output = await gql_client.query(query, user_id=user_id, member_projects=[project_id])
    create_type = [item for item in output["data"]["__schema"]["types"] if item["name"] == "GenomicRangeCreateInput"][0]
    fields = [field["name"] for field in create_type["inputFields"]]
    # Producing run id and collection id are always settable on a new entity.
    # producingRunId is only settable by a system user, and collectionId is settable by users.
    assert set(fields) == set(["producingRunId", "collectionId", "deletedAt"])
