"""
Launch the GraphQL server.
"""

import strawberry
import uvicorn
from api.mutation import Mutation
from api.query import Query
from platformics.api.setup import get_app, get_strawberry_config
from platformics.settings import APISettings

settings = APISettings.model_validate({})  # Workaround for https://github.com/pydantic/pydantic/issues/3753
strawberry_config = get_strawberry_config()
schema = strawberry.Schema(query=Query, mutation=Mutation, config=strawberry_config)


# Create and run app
app = get_app(settings, schema)

if __name__ == "__main__":
    config = uvicorn.Config("api.main:app", host="0.0.0.0", port=8009, log_level="info")
    server = uvicorn.Server(config)
    server.run()
