"""
Launch the GraphQL server.
"""

import strawberry
import uvicorn
from platformics.api.setup import get_app, get_strawberry_config
from platformics.api.core.error_handler import HandleErrors
from platformics.settings import APISettings
from database import models

from customMutations import Mutation

from customQueries import Query


settings = APISettings.model_validate({})  # Workaround for https://github.com/pydantic/pydantic/issues/3753
schema = strawberry.Schema(query=Query, mutation=Mutation, config=get_strawberry_config(), extensions=[HandleErrors()])


# Create and run app
app = get_app(settings, schema, models)

if __name__ == "__main__":
    config = uvicorn.Config("main:app", host="0.0.0.0", port=9008, log_level="info")
    server = uvicorn.Server(config)
    server.run()
