import typing
from enum import Enum
from sqlalchemy import inspect

from cerbos.sdk.client import CerbosClient
from cerbos.sdk.model import ResourceDesc
from cerbos.sdk.model import Principal as CerbosPrincipal
from sqlalchemy.sql import Select

import platformics.database.models as db
from platformics.settings import APISettings
from platformics.thirdparty.cerbos_sqlalchemy.query import get_query
from cerbos.sdk.model import Resource
from platformics.security.token_auth import get_token_claims


class AuthzAction(str, Enum):
    VIEW = "view"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"

# TODO - right now this is an unmodified alias of Cerbos' principal, but we can extend it in the future
# if need be. The properties/methods of this class are *only* referenced in this file!
class Principal(CerbosPrincipal):
    pass

def hydrate_auth_principal(
    settings: APISettings,
    user_token: typing.Optional[str],
) -> typing.Optional[Principal]:
    if not user_token:
        return None
    try:
        claims = get_token_claims(settings.JWK_PRIVATE_KEY, user_token)
    except:  # noqa
        return None

    if "project_roles" not in claims:
        raise Exception("no project roles in claims")

    project_claims = claims["project_roles"]

    try:
        for role, project_ids in project_claims.items():
            assert role in ["member", "owner", "viewer"]
            assert isinstance(project_ids, list)
            for item in project_ids:
                assert int(item)
    except Exception:
        return None

    return Principal(
        claims["sub"],
        roles=["user"],
        attr={
            "user_id": int(claims["sub"]),
            "owner_projects": project_claims.get("owner", []),
            "member_projects": project_claims.get("member", []),
            "viewer_projects": project_claims.get("viewer", []),
            "service_identity": claims["service_identity"],
        },
    )

class AuthzClient:
    def __init__(self, settings: APISettings):
        self.settings = settings
        self.client = CerbosClient(host=settings.CERBOS_URL)
    
    # Convert a model object to a dictionary
    def obj_to_dict(self, obj):
        mydict = {}
        relationships = obj.__mapper__.relationships
        for col in obj.__mapper__.all_orm_descriptors:
            # Don't send related fields to cerbos for authz checks
            if col.key in relationships:
                continue
            value = getattr(obj, col.key)
            if type(value) not in [int, str, bool, float]:
                # TODO, we probably want to look into a smarter way to serialize fields for cerbos
                value = str(value)
            mydict[col.key] = value
        return mydict

    def can_create(self, resource, principal: Principal) -> bool:
        resource_type = type(resource).__tablename__
        attr = self.obj_to_dict(resource)
        resource = Resource(id="NEW_ID", kind=resource_type, attr=attr)
        if self.client.is_allowed(AuthzAction.CREATE, principal, resource):
            return True
        return False
    
    def can_update(self, resource, principal: Principal) -> bool:
        resource_type = type(resource).__tablename__
        attr = self.obj_to_dict(resource)
        # TODO - this should send in the actual resource ID instead of a placeholder string
        # There are two complexities there though: UUID's don't natively serialize to json,
        # so they cannot be sent in cerbos perms checks, and we need to find/use the table's
        # primary key instead of a hardcoded column name.
        resource = Resource(id="resource_id", kind=resource_type, attr=attr)
        if self.client.is_allowed(AuthzAction.UPDATE, principal, resource):
            return True
        return False

    def get_resource_query(
        self,
        principal: Principal,
        action: AuthzAction,
        model_cls: typing.Union[type[db.Base]],  # type: ignore
    ) -> Select:
        rd = ResourceDesc(model_cls.__tablename__)
        plan = self.client.plan_resources(action, principal, rd)
        # if model_cls == db.File:  # type: ignore
        #   raise NotImplementedError("You need to fix the files thing!!")
        # else:
        if True:
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
