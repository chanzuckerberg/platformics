"""
Authorization spot-checks
"""

import uuid
import json
from typing import Any

import pytest
from conftest import GQLTestClient, SessionStorage
from test_infra.factories.constraint_checked_type import ConstraintCheckedTypeFactory
from platformics.database.connect import SyncDB


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "field_name,invalid_values,valid_values",
    [
        ("length3To8", ["a", "", "  a   ", "  abcdefghi  "], ["abcde", "   abc    ", "abcdefgh   "]),
        ("regexFormatCheck", ["hi", "aaa-bbb-ccc", "100-100-10000"], ["222-33-4444", "  aaa333-44-5555ccc  "]),
        ("minValue0", [-7, -14], [0, 3, 999999]),
        ("maxValue9", [11, 44444], [0, -17, 9]),
        ("minValue0MaxValue9", [-39, 10, 9999], [0, 6, 9]),
        ("float1dot1To2dot2", [0, 3.3], [1.1, 1.2, 2.2]),
        ("noStringChecks", [], ["", "aasdfasdfasd", "  lorem ipsum !@#$%^&*()  "]),
        ("noIntChecks", [], [65, 0, 400, 7]),
        ("noFloatChecks", [], [-65.50, 0.00001, 400.6, 7]),
        ("boolField", [], [True, False]),
        ("enumField", [], ["RNA", "DNA"]),
    ],
)
async def test_create_validation(
    field_name: str,
    invalid_values: list[Any],
    valid_values: list[Any],
    gql_client: GQLTestClient,
) -> None:
    """
    Make sure input field validation works.
    """
    user_id = 12345
    project_ids = [333]

    def get_query(field_name: str, value: Any) -> str:
        if "enum" not in field_name:
            value = json.dumps(value)
        query = f"""
            mutation MyMutation {{
              createConstraintCheckedType(input: {{collectionId: {project_ids[0]}, {field_name}: {value} }}) {{
                collectionId
                {field_name}
              }}
            }}
        """
        return query

    # These should succeed
    for value in valid_values:
        query = get_query(field_name, value)
        output = await gql_client.query(query, user_id=user_id, member_projects=project_ids)
        if isinstance(value, str):
            assert output["data"]["createConstraintCheckedType"][field_name] == value.strip()
        else:
            assert output["data"]["createConstraintCheckedType"][field_name] == value

    # These should fail
    for value in invalid_values:
        query = get_query(field_name, value)
        output = await gql_client.query(query, user_id=user_id, member_projects=project_ids)
        assert "Validation Error" in output["errors"][0]["message"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "field_name,invalid_values,valid_values",
    [
        ("length3To8", ["a", "", "  a   ", "  abcdefghi  "], ["abcde", "   abc    ", "abcdefgh   "]),
        ("regexFormatCheck", ["hi", "aaa-bbb-ccc", "100-100-10000"], ["222-33-4444", "  aaa333-44-5555ccc  "]),
        ("minValue0", [-7, -14], [0, 3, 999999]),
        ("maxValue9", [11, 44444], [0, -17, 9]),
        ("minValue0MaxValue9", [-39, 10, 9999], [0, 6, 9]),
        ("float1dot1To2dot2", [0, 3.3], [1.1, 1.2, 2.2]),
        ("noStringChecks", [], ["", "aasdfasdfasd", "  lorem ipsum !@#$%^&*()  "]),
        ("noIntChecks", [], [65, 0, 400, 7]),
        ("noFloatChecks", [], [-65.50, 0.00001, 400.6, 7]),
        ("boolField", [], [True, False]),
        ("enumField", [], ["RNA", "DNA"]),
    ],
)
async def test_update_validation(
    field_name: str,
    invalid_values: list[Any],
    valid_values: list[Any],
    gql_client: GQLTestClient,
    sync_db: SyncDB,
) -> None:
    """
    Make sure input field validation works.
    """
    with sync_db.session() as session:
        SessionStorage.set_session(session)
        instance = ConstraintCheckedTypeFactory.create(owner_user_id=999, collection_id=333)

    user_id = 12345
    project_ids = [333]

    def get_query(id: uuid.UUID, field_name: str, value: Any) -> str:
        if "enum" not in field_name:
            value = json.dumps(value)
        query = f"""
            mutation MyMutation {{
              updateConstraintCheckedType(where: {{id: {{_eq: "{id}" }} }}, input: {{ {field_name}: {value} }}) {{
                collectionId
                {field_name}
              }}
            }}
        """
        return query

    # These should succeed
    for value in valid_values:
        query = get_query(instance.id, field_name, value)
        output = await gql_client.query(query, user_id=user_id, member_projects=project_ids)
        if isinstance(value, str):
            assert output["data"]["updateConstraintCheckedType"][0][field_name] == value.strip()
        else:
            assert output["data"]["updateConstraintCheckedType"][0][field_name] == value

    # These should fail
    for value in invalid_values:
        query = get_query(instance.id, field_name, value)
        output = await gql_client.query(query, user_id=user_id, member_projects=project_ids)
        assert "Validation Error" in output["errors"][0]["message"]
