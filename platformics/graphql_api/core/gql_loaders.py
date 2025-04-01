import typing
from collections import defaultdict
from typing import Any, Mapping, Optional, Sequence, Tuple

import sqlalchemy as sa
from sqlalchemy.orm import RelationshipProperty
from strawberry.dataloader import DataLoader

from platformics.database.connect import AsyncDB
from platformics.graphql_api.core.errors import PlatformicsError
from platformics.graphql_api.core.query_builder import get_aggregate_db_query, get_db_query, get_db_rows
from platformics.security.authorization import AuthzAction, AuthzClient, Principal
from platformics.support import sqlalchemy_helpers

E = typing.TypeVar("E")
T = typing.TypeVar("T")


def get_input_hash(input_dict: dict) -> int:
    """
    Create a deterministic hash value for a dictionary of query parameters.
    This hash is used as a cache key for dataloaders with specific filters.

    The function recursively processes nested dictionaries and handles lists
    by converting them to frozensets (which are hashable).
    """
    hash_dict = {}
    for k, v in input_dict.items():
        if isinstance(v, dict):
            v = get_input_hash(v)
        # NOTE - we're explicitly not supporting dicts inside lists since
        # our current where clause interface doesn't call for it.
        if isinstance(v, list):
            v = hash(frozenset(v))
        hash_dict[k] = v
    return hash(tuple(sorted(hash_dict.items())))


class EntityLoader:
    """
    Creates DataLoader instances on-the-fly for SQLAlchemy relationships

    The DataLoader pattern solves the "N+1 query problem" in GraphQL:
    Instead of making one database query per related object (which could be hundreds),
    DataLoaders batch multiple requests together into a single database query.

    For example, if a GraphQL query requests 100 users and each user's posts,
    without DataLoader: 1 query for users + 100 queries for each user's posts = 101 queries
    with DataLoader: 1 query for users + 1 batch query for all users' posts = 2 queries

    This class creates and manages DataLoader instances for each relationship type.
    """

    _loaders: dict[RelationshipProperty, DataLoader]  # Cache of relationship dataloaders
    _aggregate_loaders: dict[RelationshipProperty, DataLoader]  # Cache for aggregate operations

    def __init__(self, engine: AsyncDB, authz_client: AuthzClient, principal: Principal) -> None:
        """
        Initialize the EntityLoader with database connection and security context.

        Args:
            engine: The async database connection
            authz_client: Client that handles authorization checks
            principal: The user/service making the request
        """
        self._loaders = {}
        self._aggregate_loaders = {}
        self.engine = engine
        self.authz_client = authz_client
        self.principal = principal

    async def resolve_nodes(self, cls: Any, node_ids: list[str]) -> Sequence[E]:
        """
        Fetch entities by their node IDs for GraphQL Relay's node interface.

        The Relay node interface lets clients fetch any object by ID without
        knowing its type. This method handles those requests by looking up
        objects of a specific class by their IDs.

        Args:
            cls: The entity class to query
            node_ids: List of IDs to fetch

        Returns:
            A sequence of found entities
        """
        db_session = self.engine.session()

        # What's the class identifier?
        pk_col_name, pk_field = sqlalchemy_helpers.get_primary_key(cls)
        field_type = pk_field.property.columns[0].type

        # if the field type is an int, we need to convert the node_ids to int
        # TODO - handle other types like date, bool, etc?
        if isinstance(field_type, (sa.Integer, sa.BigInteger, sa.SmallInteger)):
            node_ids = [int(node_id) for node_id in node_ids]  # type: ignore
        if pk_col_name is None:
            raise Exception("Primary keys are required for each class")
        where = {pk_col_name: {"_in": node_ids}}
        rows = await get_db_rows(cls, db_session, self.authz_client, self.principal, where)
        await db_session.close()
        return rows

    def loader_for(
        self,
        relationship: RelationshipProperty,
        where: Optional[Any] = None,
        order_by: Optional[Any] = None,
    ) -> DataLoader:
        """
        Get or create a DataLoader for a specific relationship with optional filters.

        This is the core method of the EntityLoader. It does several important things:
        1. Creates a unique cache key based on the relationship and any filters
        2. Returns an existing DataLoader if we've created one before
        3. Creates a new DataLoader with a custom load function if needed

        The load function will:
        - Batch multiple requests for related objects
        - Make a single optimized query with all the requested IDs
        - Distribute the results back to the individual resolvers

        Args:
            relationship: The SQLAlchemy relationship to load data for
            where: Optional filter conditions
            order_by: Optional sort order

        Returns:
            A DataLoader configured for the specific relationship and filters
        """

        # Initialize empty filters if none provided
        if not where:
            where = {}
        if not order_by:
            order_by = []

        # Create a hash of all query parameters to use as a cache key
        # This ensures we reuse the same DataLoader for identical queries
        input_dict = {}  # type: ignore
        input_dict.update(where)
        for item in order_by:
            input_dict.update(item)
        input_hash = get_input_hash(input_dict)

        # Check if we already have a DataLoader for this relationship + filters
        try:
            return self._loaders[(relationship, input_hash)]  # type: ignore
        except KeyError:
            # If not, we need to create a new one
            related_model = relationship.entity.entity

            # Define the batch loading function that will be called by the DataLoader
            async def load_fn(keys: list[Any]) -> typing.Sequence[Any]:
                """
                Batch loading function that fetches multiple related objects in one query.

                The DataLoader will collect all individual requests over a tick of the event loop,
                then call this function once with all the requested keys.

                Args:
                    keys: List of parent object keys to fetch related objects for

                Returns:
                    A sequence of results in the same order as the requested keys
                """
                if not relationship.local_remote_pairs:
                    raise Exception("invalid relationship")

                # Build filters to fetch all related objects for the requested keys
                filters = []
                for _, remote in relationship.local_remote_pairs:
                    # Create an "IN" clause with all the requested keys
                    filters.append(remote.in_(keys))

                # Build the base query with security checks and user-provided filters
                query = get_db_query(
                    related_model,
                    AuthzAction.VIEW,
                    self.authz_client,
                    self.principal,
                    where,
                    order_by,  # type: ignore
                    relationship,  # type: ignore
                )

                # Add the filters to get only objects related to the requested keys
                for item in filters:
                    query = query.where(item)

                # Execute the query
                db_session = self.engine.session()
                rows = (await db_session.execute(query)).scalars().all()
                await db_session.close()

                # Helper function to group the returned rows by the parent object they're related to.
                def group_by_remote_key(row: Any) -> Tuple:
                    if not relationship.local_remote_pairs:
                        raise Exception("invalid relationship")
                    # TODO -- Technically, SA supports multiple field filters in a relationship! We'll need to handle this case
                    return [getattr(row, remote.key) for _, remote in relationship.local_remote_pairs if remote.key][0]

                # Group the results by their foreign keys
                grouped_keys: Mapping[Any, list[Any]] = defaultdict(list)
                for row in rows:
                    grouped_keys[group_by_remote_key(row)].append(row)

                # Return results in the same order as the input keys
                if relationship.uselist:
                    # For one-to-many relationships, return a list for each key
                    return [grouped_keys[key] for key in keys]
                else:
                    # For one-to-one relationships, return a single object (or None) for each key
                    return [grouped_keys[key][0] if grouped_keys[key] else None for key in keys]

            # Create and cache the new DataLoader
            self._loaders[(relationship, input_hash)] = DataLoader(load_fn=load_fn)  # type: ignore
            return self._loaders[(relationship, input_hash)]  # type: ignore

    def aggregate_loader_for(
        self,
        relationship: RelationshipProperty,
        where: Optional[Any] = None,
        selections: Optional[Any] = None,
    ) -> DataLoader:
        """
        Retrieve or create a DataLoader that aggregates data for the given relationship
        """
        if not where:
            where = {}
        if not selections:
            selections = []

        input_hash = get_input_hash(where)
        str_selections = str(selections)

        try:
            return self._aggregate_loaders[(relationship, str_selections, input_hash)]  # type: ignore
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

                if selections:
                    aggregate_selections = [selection for selection in selections if selection.name != "groupBy"]
                    groupby_selections = [selection for selection in selections if selection.name == "groupBy"]
                    groupby_selections = groupby_selections[0].selections if groupby_selections else []
                else:
                    aggregate_selections = []
                    groupby_selections = []
                if not aggregate_selections:
                    raise PlatformicsError("No aggregate functions selected")

                query, group_by = get_aggregate_db_query(
                    related_model,
                    AuthzAction.VIEW,
                    self.authz_client,
                    self.principal,
                    where,
                    aggregate_selections,
                    groupby_selections,
                    None,
                    remote,  # type: ignore
                )
                for item in filters:
                    query = query.where(item)
                for item in order_by:
                    query = query.order_by(item)
                if group_by:
                    query = query.group_by(*group_by)  # type: ignore
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

            self._aggregate_loaders[(relationship, str_selections, input_hash)] = DataLoader(load_fn=load_fn)  # type: ignore
            return self._aggregate_loaders[(relationship, str_selections, input_hash)]  # type: ignore
