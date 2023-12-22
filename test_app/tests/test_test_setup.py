"""
Make sure we are testing the mock schema, not the real one
"""

import pytest
from fastapi import FastAPI
from platformics.codegen.conftest import GQLTestClient


@pytest.mark.asyncio
async def test_graphql_query(gql_client: GQLTestClient, api_test_schema: FastAPI) -> None:
    """
    Make sure we're using the right schema and http client
    """
    assert api_test_schema.title == "Codegen Tests"
    assert gql_client.http_client.base_url.host == "test-codegen"

    # Reference genomes is not an entity in the mock schema but is one in the real schema
    query = """
        query MyQuery {
            referenceGenomes {
                id
            }
        }
    """
    output = await gql_client.query(query)
    assert output["data"] is None
    assert output["errors"][0]["message"] == "Cannot query field 'referenceGenomes' on type 'Query'."
