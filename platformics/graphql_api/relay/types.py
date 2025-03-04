from __future__ import annotations

import inspect
import itertools
import sys
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncIterable,
    AsyncIterator,
    ClassVar,
    ForwardRef,
    Generic,
    Iterable,
    Iterator,
    List,
    Optional,
    Sequence,
    Type,
    TypeVar,
    Union,
    cast,
    overload,
)

import strawberry

# from strawberry.relay import GlobalID
# from strawberry.relay import Node as StrawberryNode
from strawberry.types import get_object_definition
from strawberry.types.base import StrawberryContainer, StrawberryObjectDefinition
from strawberry.types.field import field
from strawberry.types.info import Info  # noqa: TCH001
from strawberry.types.object_type import interface, type
from strawberry.types.private import StrawberryPrivate
from strawberry.utils.aio import aenumerate, aislice, resolve_awaitable
from strawberry.utils.inspect import in_async_context
from strawberry.utils.typing import eval_type, is_classvar
from typing_extensions import Annotated, Literal, Self, TypeAlias, get_args, get_origin

from platformics.graphql_api.relay.exceptions import NodeIDAnnotationError

if TYPE_CHECKING:
    from strawberry.utils.await_maybe import AwaitableOrValue

_T = TypeVar("_T")

NodeIterableType: TypeAlias = Union[
    Iterator[_T],
    Iterable[_T],
    AsyncIterator[_T],
    AsyncIterable[_T],
]
NodeType = TypeVar("NodeType", bound="Node")

PREFIX = "arrayconnection"


class NodeIDPrivate(StrawberryPrivate):
    """Annotate a type attribute as its id.

    The `Node` interface will automatically create and resolve GlobalIDs
    based on the field annotated with `NodeID`. e.g:

      >>> @strawberry.type
      ... class Fruit(Node):
      ...     code: NodeID[str]

    In this case, `code` will be used to generate a global ID in the
    format `Fruit:<code>` and will be exposed as `id: GlobalID!` in the
    `Fruit` type.
    """


NodeID: TypeAlias = Annotated[_T, NodeIDPrivate()]


@interface(description="An object with a Globally Unique ID")
class Node:
    """Node interface for GraphQL types.

    Subclasses must type the id field using `NodeID`. It will be private to the
    schema because it will be converted to a global ID and exposed as `id: GlobalID!`

    The following methods can also be implemented:
        resolve_id:
            (Optional) Called to resolve the node's id. Can be overriden to
            customize how the id is retrieved (e.g. in case you don't want
            to define a `NodeID` field)
        resolve_nodes:
            Called to retrieve an iterable of node given their ids
        resolve_node:
            (Optional) Called to retrieve a node given its id. If not defined
            the default implementation will call `.resolve_nodes` with that
            single node id.

    Example:

        >>> @strawberry.type
        ... class Fruit(Node):
        ...     id: NodeID[int]
        ...     name: str
        ...
        ... @classmethod
        ... def resolve_nodes(cls, *, info, node_ids, required=False):
        ...     # Return an iterable of fruits in here
        ...     ...

    """

    _id_attr: ClassVar[Optional[str]] = None

    @field(name="id", description="The Globally Unique ID of this object")
    @classmethod
    def _id(cls, root: Node | Any, info: Info) -> strawberry.ID:
        # NOTE: root might not be a Node instance when using integrations which
        # return an object that is compatible with the type (e.g. the django one).
        # In that case, we can retrieve the type itself from info
        if isinstance(root, Node):
            resolve_id = root.__class__.resolve_id
            resolve_typename = root.__class__.resolve_typename
        else:
            parent_type = info._raw_info.parent_type
            type_def = info.schema.get_type_by_name(parent_type.name)
            assert isinstance(type_def, StrawberryObjectDefinition)
            origin = cast(Type[Node], type_def.origin)
            resolve_id = origin.resolve_id
            resolve_typename = origin.resolve_typename

        type_name = resolve_typename(root, info)
        assert isinstance(type_name, str)
        node_id = resolve_id(root, info=info)
        assert node_id is not None

        return cast(strawberry.ID, node_id)

    @classmethod
    def resolve_id_attr(cls) -> str:
        if cls._id_attr is not None:
            return cls._id_attr

        candidates: list[str] = []
        for base in cls.__mro__:
            base_namespace = sys.modules[base.__module__].__dict__

            for attr_name, attr in getattr(base, "__annotations__", {}).items():
                # Some ClassVar might raise TypeError when being resolved
                # on some python versions. This is fine to skip since
                # we are not interested in ClassVars here
                if is_classvar(base, attr):
                    continue

                evaled = eval_type(
                    ForwardRef(attr) if isinstance(attr, str) else attr,
                    globalns=base_namespace,
                )

                if get_origin(evaled) is Annotated and any(isinstance(a, NodeIDPrivate) for a in get_args(evaled)):
                    candidates.append(attr_name)

            # If we found candidates in this base, stop looking for more
            # This is to support subclasses to define something else than
            # its superclass as a NodeID
            if candidates:
                break

        if len(candidates) == 0:
            raise NodeIDAnnotationError(f'No field annotated with `NodeID` found in "{cls.__name__}"', cls)
        if len(candidates) > 1:
            raise NodeIDAnnotationError(
                f'More than one field annotated with `NodeID` found in "{cls.__name__}"',
                cls,
            )

        cls._id_attr = candidates[0]
        return cls._id_attr

    @classmethod
    def resolve_id(
        cls,
        root: Self,
        *,
        info: Info,
    ) -> AwaitableOrValue[str]:
        """Resolve the node id.

        By default this will return `getattr(root, <id_attr>)`, where <id_attr>
        is the field typed with `NodeID`.

        You can override this method to provide a custom implementation.

        Args:
            info:
                The strawberry execution info resolve the type name from
            root:
                The node to resolve

        Returns:
            The resolved id (which is expected to be str)

        """
        return getattr(root, cls.resolve_id_attr())

    @classmethod
    def resolve_typename(cls, root: Self, info: Info) -> str:
        typename = info.path.typename
        assert typename is not None
        return typename

    @overload
    @classmethod
    def resolve_nodes(
        cls,
        *,
        info: Info,
        node_ids: Iterable[str],
        required: Literal[True],
    ) -> AwaitableOrValue[Iterable[Self]]: ...

    @overload
    @classmethod
    def resolve_nodes(
        cls,
        *,
        info: Info,
        node_ids: Iterable[str],
        required: Literal[False] = ...,
    ) -> AwaitableOrValue[Iterable[Optional[Self]]]: ...

    @overload
    @classmethod
    def resolve_nodes(
        cls,
        *,
        info: Info,
        node_ids: Iterable[str],
        required: bool,
    ) -> Union[AwaitableOrValue[Iterable[Self]], AwaitableOrValue[Iterable[Optional[Self]]]]: ...

    @classmethod
    def resolve_nodes(
        cls,
        *,
        info: Info,
        node_ids: Iterable[str],
        required: bool = False,
    ):
        """Resolve a list of nodes.

        This method *should* be defined by anyone implementing the `Node` interface.

        The nodes should be returned in the same order as the provided ids.
        Also, if `required` is `True`, all ids must be resolved or an error
        should be raised. If `required` is `False`, missing nodes should be
        returned as `None`.

        Args:
            info:
                The strawberry execution info resolve the type name from
            node_ids:
                List of node ids that should be returned
            required:
                If `True`, all `node_ids` requested must exist. If they don't,
                an error must be raised. If `False`, missing nodes should be
                returned as `None`. It only makes sense when passing a list of
                `node_ids`, otherwise it will should ignored.

        Returns:
            An iterable of resolved nodes.

        """
        raise NotImplementedError

    @overload
    @classmethod
    def resolve_node(
        cls,
        node_id: str,
        *,
        info: Info,
        required: Literal[True],
    ) -> AwaitableOrValue[Self]: ...

    @overload
    @classmethod
    def resolve_node(
        cls,
        node_id: str,
        *,
        info: Info,
        required: Literal[False] = ...,
    ) -> AwaitableOrValue[Optional[Self]]: ...

    @overload
    @classmethod
    def resolve_node(
        cls,
        node_id: str,
        *,
        info: Info,
        required: bool,
    ) -> AwaitableOrValue[Optional[Self]]: ...

    @classmethod
    def resolve_node(
        cls,
        node_id: str,
        *,
        info: Info,
        required: bool = False,
    ) -> AwaitableOrValue[Optional[Self]]:
        """Resolve a node given its id.

        This method is a convenience method that calls `resolve_nodes` for
        a single node id.

        Args:
            info:
                The strawberry execution info resolve the type name from
            node_id:
                The id of the node to be retrieved
            required:
                if the node is required or not to exist. If not, then None
                should be returned if it doesn't exist. Otherwise an exception
                should be raised.

        Returns:
            The resolved node or None if it was not found

        """
        retval = cls.resolve_nodes(info=info, node_ids=[node_id], required=required)

        if inspect.isawaitable(retval):
            return resolve_awaitable(retval, lambda resolved: next(iter(resolved)))

        return next(iter(cast(Iterable[Self], retval)))


@type(description="Information to aid in pagination.")
class PageInfo:
    """Information to aid in pagination.

    Attributes:
        has_next_page:
            When paginating forwards, are there more items?
        has_previous_page:
            When paginating backwards, are there more items?
        start_cursor:
            When paginating backwards, the cursor to continue
        end_cursor:
            When paginating forwards, the cursor to continue

    """

    has_next_page: bool = field(
        description="When paginating forwards, are there more items?",
    )
    has_previous_page: bool = field(
        description="When paginating backwards, are there more items?",
    )
    start_cursor: Optional[str] = field(
        description="When paginating backwards, the cursor to continue.",
    )
    end_cursor: Optional[str] = field(
        description="When paginating forwards, the cursor to continue.",
    )


@type(description="An edge in a connection.")
class Edge(Generic[NodeType]):
    """An edge in a connection.

    Attributes:
        cursor:
            A cursor for use in pagination
        node:
            The item at the end of the edge

    """

    cursor: str = field(
        description="A cursor for use in pagination",
    )
    node: NodeType = field(
        description="The item at the end of the edge",
    )

    @classmethod
    def resolve_edge(cls, node: NodeType, *, cursor: Any = None) -> Self:
        return cls(cursor=cursor, node=node)


@type(description="A connection to a list of items.")
class Connection(Generic[NodeType]):
    """A connection to a list of items.

    Attributes:
        page_info:
            Pagination data for this connection
        edges:
            Contains the nodes in this connection

    """

    page_info: PageInfo = field(
        description="Pagination data for this connection",
    )
    edges: List[Edge[NodeType]] = field(
        description="Contains the nodes in this connection",
    )

    @classmethod
    def resolve_node(cls, node: Any, *, info: Info, **kwargs: Any) -> NodeType:
        """The identity function for the node.

        This method is used to resolve a node of a different type to the
        connection's `NodeType`.

        By default it returns the node itself, but subclasses can override
        this to provide a custom implementation.

        Args:
            node:
                The resolved node which should return an instance of this
                connection's `NodeType`
            info:
                The strawberry execution info resolve the type name from

        """
        return node

    @classmethod
    def resolve_connection(
        cls,
        nodes: NodeIterableType[NodeType],
        *,
        info: Info,
        before: Optional[str] = None,
        after: Optional[str] = None,
        first: Optional[int] = None,
        last: Optional[int] = None,
        **kwargs: Any,
    ) -> AwaitableOrValue[Self]:
        """Resolve a connection from nodes.

        Subclasses must define this method to paginate nodes based
        on `first`/`last`/`before`/`after` arguments.

        Args:
            info:
                The strawberry execution info resolve the type name from
            nodes:
                An iterable/iteretor of nodes to paginate
            before:
                Returns the items in the list that come before the specified cursor
            after:
                Returns the items in the list that come after the specified cursor
            first:
                Returns the first n items from the list
            last:
                Returns the items in the list that come after the specified cursor

        Returns:
            The resolved `Connection`

        """
        raise NotImplementedError


@type(name="Connection", description="A connection to a list of items.")
class ListConnection(Connection[NodeType]):
    """A connection to a list of items.

    Attributes:
        page_info:
            Pagination data for this connection
        edges:
            Contains the nodes in this connection

    """

    page_info: PageInfo = field(
        description="Pagination data for this connection",
    )
    edges: List[Edge[NodeType]] = field(
        description="Contains the nodes in this connection",
    )

    @classmethod
    def resolve_connection(
        cls,
        nodes: NodeIterableType[NodeType],
        *,
        info: Info,
        before: Optional[str] = None,
        after: Optional[str] = None,
        first: Optional[int] = None,
        last: Optional[int] = None,
        **kwargs: Any,
    ) -> AwaitableOrValue[Self]:
        """Resolve a connection from the list of nodes.

        This uses the described Relay Pagination algorithm_

        Args:
            info:
                The strawberry execution info resolve the type name from
            nodes:
                An iterable/iteretor of nodes to paginate
            before:
                Returns the items in the list that come before the specified cursor
            after:
                Returns the items in the list that come after the specified cursor
            first:
                Returns the first n items from the list
            last:
                Returns the items in the list that come after the specified cursor

        Returns:
            The resolved `Connection`

        .. _Relay Pagination algorithm:
            https://relay.dev/graphql/connections.htm#sec-Pagination-algorithm

        """
        max_results = info.schema.config.relay_max_results
        start: Optional[int] = 0
        end: Optional[int] = None

        if after:
            start = int(after) + 1
        if before:
            end = int(before) + 1

        if isinstance(first, int):
            if first < 0:
                raise ValueError("Argument 'first' must be a non-negative integer.")

            if first > max_results:
                raise ValueError(f"Argument 'first' cannot be higher than {max_results}.")

            if end is not None:
                start = max(0, end - 1)

            end = start + first
        if isinstance(last, int):
            if last < 0:
                raise ValueError("Argument 'last' must be a non-negative integer.")

            if last > max_results:
                raise ValueError(f"Argument 'last' cannot be higher than {max_results}.")

            if end is not None:
                start = max(start, end - last)
            else:
                end = sys.maxsize

        if end is None:
            end = start + max_results

        expected = end - start if end != sys.maxsize else None
        # Overfetch by 1 to check if we have a next result
        overfetch = end + 1 if end != sys.maxsize else end

        type_def = get_object_definition(cls)
        assert type_def
        field_def = type_def.get_field("edges")
        assert field_def

        field = field_def.resolve_type(type_definition=type_def)
        while isinstance(field, StrawberryContainer):
            field = field.of_type

        edge_class = cast(Edge[NodeType], field)

        if isinstance(nodes, (AsyncIterator, AsyncIterable)) and in_async_context():

            async def resolver():
                try:
                    iterator = cast(
                        Union[AsyncIterator[NodeType], AsyncIterable[NodeType]],
                        cast(Sequence, nodes)[start:overfetch],
                    )
                except TypeError:
                    # TODO: Why mypy isn't narrowing this based on the if above?
                    assert isinstance(nodes, (AsyncIterator, AsyncIterable))
                    iterator = aislice(
                        nodes,
                        start,
                        overfetch,
                    )

                # The slice above might return an object that now is not async
                # iterable anymore (e.g. an already cached django queryset)
                if isinstance(iterator, (AsyncIterator, AsyncIterable)):
                    edges: List[Edge] = [
                        edge_class.resolve_edge(
                            cls.resolve_node(v, info=info, **kwargs),
                            cursor=start + i,
                        )
                        async for i, v in aenumerate(iterator)
                    ]
                else:
                    edges: List[Edge] = [  # type: ignore[no-redef]
                        edge_class.resolve_edge(
                            cls.resolve_node(v, info=info, **kwargs),
                            cursor=start + i,
                        )
                        for i, v in enumerate(iterator)
                    ]

                has_previous_page = start > 0
                if expected is not None and len(edges) == expected + 1:
                    # Remove the overfetched result
                    edges = edges[:-1]
                    has_next_page = True
                elif end == sys.maxsize:
                    # Last was asked without any after/before
                    assert last is not None
                    original_len = len(edges)
                    edges = edges[-last:]
                    has_next_page = False
                    has_previous_page = len(edges) != original_len
                else:
                    has_next_page = False

                return cls(
                    edges=edges,
                    page_info=PageInfo(
                        start_cursor=edges[0].cursor if edges else None,
                        end_cursor=edges[-1].cursor if edges else None,
                        has_previous_page=has_previous_page,
                        has_next_page=has_next_page,
                    ),
                )

            return resolver()

        try:
            iterator = cast(
                Union[Iterator[NodeType], Iterable[NodeType]],
                cast(Sequence, nodes)[start:overfetch],
            )
        except TypeError:
            assert isinstance(nodes, (Iterable, Iterator))
            iterator = itertools.islice(
                nodes,
                start,
                overfetch,
            )

        edges = [
            edge_class.resolve_edge(
                cls.resolve_node(v, info=info, **kwargs),
                cursor=start + i,
            )
            for i, v in enumerate(iterator)
        ]

        has_previous_page = start > 0
        if expected is not None and len(edges) == expected + 1:
            # Remove the overfetched result
            edges = edges[:-1]
            has_next_page = True
        elif end == sys.maxsize:
            # Last was asked without any after/before
            assert last is not None
            original_len = len(edges)
            edges = edges[-last:]
            has_next_page = False
            has_previous_page = len(edges) != original_len
        else:
            has_next_page = False

        return cls(
            edges=edges,
            page_info=PageInfo(
                start_cursor=edges[0].cursor if edges else None,
                end_cursor=edges[-1].cursor if edges else None,
                has_previous_page=has_previous_page,
                has_next_page=has_next_page,
            ),
        )
