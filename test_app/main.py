"""
Launch the GraphQL server.
"""

import strawberry
import uvicorn
from api.types.sample import SampleCreateInput
from platformics.api.setup import get_app, get_strawberry_config
from platformics.api.core.error_handler import HandleErrors
from platformics.settings import APISettings
from database import models
from platformics.api.core.strawberry_extensions import RegisteredPlatformicsPlugins

from api.mutations import Mutation
from api.queries import Query
from typing import Any
from strawberry.types import Info


def validate_sample_name(source: Any, info: Info, **kwargs: SampleCreateInput) -> None:
    if kwargs["input"].name == "foo":
        raise ValueError("Sample name cannot be 'foo'")


RegisteredPlatformicsPlugins.register("before", "sample", "create", validate_sample_name)

settings = APISettings.model_validate({})  # Workaround for https://github.com/pydantic/pydantic/issues/3753
schema = strawberry.Schema(query=Query, mutation=Mutation, config=get_strawberry_config(), extensions=[HandleErrors()])


# Create and run app
app = get_app(settings, schema, models)

if __name__ == "__main__":
    config = uvicorn.Config("main:app", host="0.0.0.0", port=9008, log_level="info")
    server = uvicorn.Server(config)
    server.run()
