"""
Test basic queries and mutations
"""

import datetime
import pytest
from platformics.database.connect import SyncDB
from conftest import GQLTestClient, SessionStorage
from test_infra.factories.sample import SampleFactory

date_now = datetime.datetime.now()

@pytest.mark.asyncio
async def test_autoupdate_fields(gql_client: GQLTestClient, sync_db: SyncDB) -> None:
    """
    Validate that can only create/modify samples in collections the user has access to
    """
    with sync_db.session() as session:
        SessionStorage.set_session(session)
        SampleFactory.create_batch(2, collection_location="San Francisco, CA", owner_user_id=10, collection_id=10)

    project_id = 123
    projects_allowed = [project_id]
    query = f"""
        mutation createAuto {{
            createAutoUpdatedType(input: {{
                name: "Test row",
                collectionId: {project_id},
            }}) {{
                id,
                name,
                autoIncField,
                defaultValue,
                defaultSaFunc,
                defaultCallable,
                onupdateCallable,
                onupdateSaFunc,
                comboField
            }}
        }}
    """
    output = await gql_client.query(query, member_projects=projects_allowed)
    assert "errors" not in output

    row = output["data"]["createAutoUpdatedType"]
    assert row["name"] == "Test row"
    assert row["defaultSaFunc"].startswith(datetime.datetime.now().isoformat()[:11])
    assert row["defaultCallable"].startswith(datetime.datetime.now().isoformat()[:11])
    assert row["comboField"].startswith(datetime.datetime.now().isoformat()[:11])
    assert row["onupdateCallable"] is None
    assert row["onupdateSaFunc"] is None
    assert row["defaultValue"] == "ifabsent_value"

    new_name = "updated test row"
    identifier = row["id"]
    query = f"""
        mutation modifyQuery {{
            updateAutoUpdatedType(
                input: {{
                    name: "{new_name}",
                    defaultValue: "updated_default"
                }}
                where: {{
                    id: {{ _eq: "{identifier}" }}
                }}
            ) {{
                id,
                name,
                autoIncField,
                defaultValue,
                defaultSaFunc,
                defaultCallable,
                onupdateCallable,
                onupdateSaFunc,
                comboField
            }}
        }}
    """
    output = await gql_client.query(query, member_projects=projects_allowed)
    assert "errors" not in output
    row = output["data"]["updateAutoUpdatedType"][0]
    assert row["name"] == new_name

    assert row["defaultSaFunc"].startswith(datetime.datetime.now().isoformat()[:11])
    assert row["defaultCallable"].startswith(datetime.datetime.now().isoformat()[:11])
    assert row["comboField"].startswith(datetime.datetime.now().isoformat()[:11])
    assert row["onupdateCallable"].startswith(datetime.datetime.now().isoformat()[:11])
    assert row["onupdateSaFunc"].startswith(datetime.datetime.now().isoformat()[:11])
    assert row["onupdateCallable"] > row["defaultCallable"]
    assert row["onupdateSaFunc"] > row["defaultSaFunc"]
    assert row["defaultValue"] == "updated_default"

    # Test deletion
    query = f"""
        mutation deleteOne {{
            deleteAutoUpdatedType(
                where: {{ id: {{ _eq: "{identifier}" }} }}
            ) {{
                id,
                name,
                autoIncField,
                defaultValue,
                defaultSaFunc,
                defaultCallable,
                onupdateCallable,
                onupdateSaFunc
            }}
        }}
    """
    output = await gql_client.query(query, member_projects=projects_allowed)
    assert "errors" not in output
    assert len(output["data"]["deleteAutoUpdatedType"]) == 1
    assert output["data"]["deleteAutoUpdatedType"][0]["id"] == identifier
    assert output["data"]["deleteAutoUpdatedType"][0]["name"] == new_name

    # Try to fetch sample now that it's deleted
    query = f"""
        query getDeleted {{
            autoUpdatedTypes ( where: {{ id: {{ _eq: "{identifier}" }} }}) {{
                id,
                name
            }}
        }}
    """
    output = await gql_client.query(query, member_projects=projects_allowed)
    assert output["data"]["autoUpdatedTypes"] == []
