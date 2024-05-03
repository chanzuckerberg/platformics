from typing import Iterable

import strawberry
from platformics.api import relay

# from strawberry import relay
from strawberry.types import Info


@strawberry.type
class Entity:
    id: strawberry.ID
    type: str
    producing_run_id: strawberry.ID
    owner_user_id: int
    collection_id: int


@strawberry.interface
class EntityInterface3:
    id: strawberry.ID
    pass


@strawberry.interface
class EntityInterface(relay.Node):
    # In the Strawberry docs, this field is called `code`, but we're using `id` instead.
    # Otherwise, Strawberry SQLAlchemyMapper errors with: "SequencingRead object has no
    # attribute code" (unless you create a column `code` in the table)
    id: relay.NodeID[str]

    @classmethod
    async def resolve_nodes(cls, *, info: Info, node_ids: Iterable[str], required: bool = False) -> list:
        dataloader = info.context["sqlalchemy_loader"]
        # TODO FIXME this db_module thing is silly.
        db_module = info.context["db_module"]
        gql_type: str = cls.__strawberry_definition__.name  # type: ignore
        sql_model = getattr(db_module, gql_type)
        return await dataloader.resolve_nodes(sql_model, node_ids)
