import typing
from collections import defaultdict
from typing import Any, Mapping, Optional, Sequence, Tuple

import database.models as db
from cerbos.sdk.client import CerbosClient
from cerbos.sdk.model import Principal
from platformics.database.connect import AsyncDB
from platformics.security.authorization import CerbosAction
from sqlalchemy.orm import RelationshipProperty
from strawberry.dataloader import DataLoader
from platformics.security.authorization import CerbosAction
from platformics.api.core.helpers import get_db_query, get_db_rows, get_aggregate_db_query

E = typing.TypeVar("E", db.File, db.Entity)  # type: ignore
T = typing.TypeVar("T")


def get_where_hash(input_dict: dict) -> int:
    hash_dict = {}
    for k, v in input_dict.items():
        if type(v) == dict:
            v = get_where_hash(v)
        # NOTE - we're explicitly not supporting dicts inside lists since
        # our current where clause interface doesn't call for it.
        if type(v) == list:
            v = hash(frozenset(v))
        hash_dict[k] = v
    return hash(tuple(sorted(hash_dict.items())))


class EntityLoader:
    """
    Creates DataLoader instances on-the-fly for SQLAlchemy relationships
    """

    _loaders: dict[RelationshipProperty, DataLoader]
    _aggregate_loaders: dict[RelationshipProperty, DataLoader]

    def __init__(self, engine: AsyncDB, cerbos_client: CerbosClient, principal: Principal) -> None:
        self._loaders = {}
        self._aggregate_loaders = {}
        self.engine = engine
        self.cerbos_client = cerbos_client
        self.principal = principal

    async def resolve_nodes(self, cls: Any, node_ids: list[str]) -> Sequence[E]:
        """
        Given a list of node IDs from a Relay `node()` query, return corresponding entities
        """
        db_session = self.engine.session()
        where = {"entity_id": {"_in": node_ids}}
        rows = await get_db_rows(cls, db_session, self.cerbos_client, self.principal, where)
        await db_session.close()
        return rows

    def loader_for(self, relationship: RelationshipProperty, where: Optional[Any] = None) -> DataLoader:
        """
        Retrieve or create a DataLoader for the given relationship
        """
        if not where:
            where = {}
        where_hash = get_where_hash(where)
        try:
            return self._loaders[(relationship, where_hash)]  # type: ignore
        except KeyError:
            related_model = relationship.entity.entity

            async def load_fn(keys: list[Any]) -> typing.Sequence[Any]:
                if not relationship.local_remote_pairs:
                    raise Exception("invalid relationship")
                filters = []
                for _, remote in relationship.local_remote_pairs:
                    filters.append(remote.in_(keys))
                order_by: list = []
                if relationship.order_by:
                    order_by = [relationship.order_by]
                query = get_db_query(
                    related_model, CerbosAction.VIEW, self.cerbos_client, self.principal, where  # type: ignore
                )
                for item in filters:
                    query = query.where(item)
                for item in order_by:
                    query = query.order_by(item)
                db_session = self.engine.session()
                rows = (await db_session.execute(query)).scalars().all()
                await db_session.close()

                def group_by_remote_key(row: Any) -> Tuple:
                    if not relationship.local_remote_pairs:
                        raise Exception("invalid relationship")
                    # TODO -- Technically, SA supports multiple field filters in a relationship! We'll need to handle this case
                    return [getattr(row, remote.key) for _, remote in relationship.local_remote_pairs if remote.key][0]

                grouped_keys: Mapping[Any, list[Any]] = defaultdict(list)
                for row in rows:
                    grouped_keys[group_by_remote_key(row)].append(row)
                if relationship.uselist:
                    return [grouped_keys[key] for key in keys]
                else:
                    return [grouped_keys[key][0] if grouped_keys[key] else None for key in keys]

            self._loaders[(relationship, where_hash)] = DataLoader(load_fn=load_fn)  # type: ignore
            return self._loaders[(relationship, where_hash)]  # type: ignore
        
    def aggregate_loader_for(self, relationship: RelationshipProperty, where: Optional[Any] = None, aggregate: Optional[Any] = None) -> DataLoader:
        """
        Retrieve or create a DataLoader that aggregates data for the given relationship
        """
        if not where:
            where = {}
        where_hash = get_where_hash(where)
        try:
            return self._aggregate_loaders[(relationship, where_hash)]  # type: ignore
        except KeyError:
            related_model = relationship.entity.entity

            async def load_fn(keys: list[Any]) -> typing.Sequence[Any]:
                if not relationship.local_remote_pairs:
                    raise Exception("invalid relationship")
                filters = []
                for _, remote in relationship.local_remote_pairs:
                    filters.append(remote.in_(keys))
                order_by: list = []
                if relationship.order_by:
                    order_by = [relationship.order_by]
                query = get_aggregate_db_query(
                    related_model, CerbosAction.VIEW, self.cerbos_client, self.principal, where, aggregate, remote  # type: ignore
                )
                for item in filters:
                    query = query.where(item)
                for item in order_by:
                    query = query.order_by(item)
                db_session = self.engine.session()
                rows = (await db_session.execute(query)).mappings().all()
                await db_session.close()

                def group_by_remote_key(row: Any) -> Tuple:
                    if not relationship.local_remote_pairs:
                        raise Exception("invalid relationship")
                    # TODO -- Technically, SA supports multiple field filters in a relationship! We'll need to handle this case
                    return [row[remote.key] for _, remote in relationship.local_remote_pairs if remote.key][0]

                grouped_keys: Mapping[Any, list[Any]] = defaultdict(list)
                for row in rows:
                    grouped_keys[group_by_remote_key(row)].append(row)
                if relationship.uselist:
                    return [grouped_keys[key] for key in keys]
                else:
                    return [grouped_keys[key][0] if grouped_keys[key] else None for key in keys]

            self._aggregate_loaders[(relationship, where_hash)] = DataLoader(load_fn=load_fn)  # type: ignore
            return self._aggregate_loaders[(relationship, where_hash)]  # type: ignore
