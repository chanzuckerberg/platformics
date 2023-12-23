import strawberry
from strawberry import relay
from strawberry.types import Info
from typing import Iterable
import database.models as db


@strawberry.type
class Entity:
    id: strawberry.ID
    type: str
    producing_run_id: strawberry.ID
    owner_user_id: int
    collection_id: int


@strawberry.interface
class EntityInterface(relay.Node):
    # In the Strawberry docs, this field is called `code`, but we're using `id` instead.
    # Otherwise, Strawberry SQLAlchemyMapper errors with: "SequencingRead object has no
    # attribute code" (unless you create a column `code` in the table)
    id: relay.NodeID[str]

    @classmethod
    async def resolve_nodes(cls, *, info: Info, node_ids: Iterable[str], required: bool = False) -> list:
        dataloader = info.context["sqlalchemy_loader"]
        gql_type: str = cls.__strawberry_definition__.name  # type: ignore
        sql_model = getattr(db, gql_type)
        return await dataloader.resolve_nodes(sql_model, node_ids)
