"""
Test that field descriptions are present in the GQL API
"""

import datetime
import pytest
from conftest import GQLTestClient

date_now = datetime.datetime.now()


@pytest.mark.asyncio
async def test_field_description(
    gql_client: GQLTestClient,
) -> None:
    """
    Test that we can only fetch samples from the database that we have access to
    """

    # Fetch all samples
    query = """
       {
         __type(name: "AutoUpdatedType") {
           name
           fields {
             name
             description
          }
        }
      }
    """
    output = await gql_client.query(query, user_id=999, member_projects=[999])
    fields = output["data"]["__type"]["fields"]
    field = {}
    for field in fields:
        if field["name"] == "name":
            break
    assert field["description"] == "This is a field description"
