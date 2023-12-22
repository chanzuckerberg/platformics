from platformics.thirdparty.cerbos_sqlalchemy.query import get_query
from cerbos.sdk.client import CerbosClient
import database.models as db
from cerbos.sdk.model import Principal, ResourceDesc
from enum import Enum
import typing
from sqlalchemy.sql import Select


class CerbosAction(str, Enum):
    VIEW = "view"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


def get_resource_query(
    principal: Principal,
    cerbos_client: CerbosClient,
    action: CerbosAction,
    model_cls: typing.Union[type[db.Entity], type[db.File]],  # type: ignore
) -> Select:
    rd = ResourceDesc(model_cls.__tablename__)
    plan = cerbos_client.plan_resources(action, principal, rd)
    if model_cls == db.File:  # type: ignore
        attr_map = {
            "request.resource.attr.owner_user_id": db.Entity.owner_user_id,  # type: ignore
            "request.resource.attr.collection_id": db.Entity.collection_id,  # type: ignore
        }
        joins = [(db.Entity, db.File.entity_id == db.Entity.id)]  # type: ignore
    else:
        attr_map = {
            "request.resource.attr.owner_user_id": model_cls.owner_user_id,  # type: ignore
            "request.resource.attr.collection_id": model_cls.collection_id,  # type: ignore
        }
        joins = []
    query = get_query(
        plan,
        model_cls,  # type: ignore
        attr_map,  # type: ignore
        joins,  # type: ignore
    )
    return query
