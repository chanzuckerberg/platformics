"""
Test basic error handling
"""

import pytest
from conftest import GQLTestClient


@pytest.mark.asyncio
async def test_unauthorized_error(
    gql_client: GQLTestClient,
) -> None:
    """
    Validate that expected errors don't get masked by our error handler.
    """
    query = """
        mutation createOneSample {
            createSample(input: {
                name: "Test Sample"
                sampleType: "Type 1"
                waterControl: false
                collectionLocation: "San Francisco, CA"
                collectionDate: "2024-01-01"
                collectionId: 123
            }) {
                id,
                collectionLocation
            }
        }
    """
    output = await gql_client.query(query, member_projects=[456])

    # Make sure we haven't masked expected errors.
    assert output["data"] is None
    assert output["errors"][0]["message"].startswith("Unauthorized: Cannot create entity")


@pytest.mark.asyncio
async def test_python_error(
    gql_client: GQLTestClient,
) -> None:
    """
    Validate that unexpected errors do get masked by our error handler.
    """
    query = """
        query causeException {
            uncaughtException
        }
    """
    output = await gql_client.query(query, member_projects=[456])

    # Make sure we have masked unexpected errors.
    assert output["data"] is None
    assert "Unexpected error" in output["errors"][0]["message"]
