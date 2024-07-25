from __future__ import annotations

import asyncio
import dataclasses
import inspect
from collections.abc import AsyncIterable
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncIterator,
    Callable,
    Dict,
    ForwardRef,
    Iterable,
    Iterator,
    List,
    Mapping,
    Optional,
    Sequence,
    Type,
    Union,
    cast,
    overload,
)

import strawberry
from strawberry.annotation import StrawberryAnnotation
from strawberry.arguments import StrawberryArgument, argument
from strawberry.extensions.field_extension import (
    AsyncExtensionResolver,
    FieldExtension,
    SyncExtensionResolver,
)
from strawberry.field import _RESOLVER_TYPE, StrawberryField, field
from strawberry.lazy_type import LazyType
from strawberry.type import StrawberryList, StrawberryOptional
from strawberry.types.fields.resolver import StrawberryResolver
from strawberry.utils.aio import asyncgen_to_list
from strawberry.utils.typing import eval_type
from typing_extensions import Annotated, get_origin

from platformics.graphql_api.relay.exceptions import (
    RelayWrongAnnotationError,
    RelayWrongResolverAnnotationError,
)

from .types import Connection, Node, NodeIterableType, NodeType

if TYPE_CHECKING:
    from strawberry.permission import BasePermission
    from strawberry.types.info import Info
    from typing_extensions import Literal


class NodeExtension(FieldExtension):
    def apply(self, field: StrawberryField) -> None:
        # TODO FIXME why did I have to comment this out????
        # assert field.base_resolver is None

        if isinstance(field.type, StrawberryList):
            resolver = self.get_node_list_resolver(field)
        else:
            resolver = self.get_node_resolver(field)

        field.base_resolver = StrawberryResolver(resolver, type_override=field.type)

    def resolve(self, next_: SyncExtensionResolver, source: Any, info: Info, **kwargs: Any) -> Any:
        return next_(source, info, **kwargs)

    async def resolve_async(self, next_: SyncExtensionResolver, source: Any, info: Info, **kwargs: Any) -> Any:
        retval = next_(source, info, **kwargs)
        # If the resolve_nodes method is not async, retval will not actually
        # be awaitable. We still need the `resolve_async` in here because
        # otherwise this extension can't be used together with other
        # async extensions.
        return await retval if inspect.isawaitable(retval) else retval

    def get_node_resolver(self, field: StrawberryField):  # noqa: ANN201
        type_ = field.type
        is_optional = isinstance(type_, StrawberryOptional)

        def resolver(
            info: Info,
            id: Annotated[strawberry.ID, argument(description="The ID of the object.")],
        ):
            type_resolvers = []
            for selected_type in info.selected_fields[0].selections:
                field_type = selected_type.type_condition
                type_def = info.schema.get_type_by_name(field_type)
                origin = type_def.origin.resolve_type if isinstance(type_def.origin, LazyType) else type_def.origin
                assert issubclass(origin, Node)
                type_resolvers.append(origin)
            # FIXME TODO this only works if we're getting a *single* subclassed `Node` type --
            # if we're getting multiple subclass types, we need to resolve them all somehow
            return type_resolvers[0].resolve_node(
                id,
                info=info,
                required=not is_optional,
            )

        return resolver

    def nodes_by_gid(self, node_lists):
        result: Dict[strawberry.ID, Type[Node]] = {}
        for node_list in node_lists:
            result.update({str(item.id): item for item in node_list})
        return result

    def get_node_list_resolver(self, field: StrawberryField):  # noqa: ANN201
        type_ = field.type
        assert isinstance(type_, StrawberryList)
        is_optional = isinstance(type_.of_type, StrawberryOptional)

        def resolver(
            info: Info,
            ids: Annotated[List[strawberry.ID], argument(description="The IDs of the objects.")],
        ):
            # Identify the types identified by the query so we can send ID's to their resolvers in a moment
            type_resolvers = []
            for selected_type in info.selected_fields[0].selections:
                field_type = selected_type.type_condition
                type_def = info.schema.get_type_by_name(field_type)
                origin = type_def.origin.resolve_type if isinstance(type_def.origin, LazyType) else type_def.origin
                assert issubclass(origin, Node)
                type_resolvers.append(origin)

            resolved_nodes = [
                node_t.resolve_nodes(
                    info=info,
                    node_ids=ids,
                    required=not is_optional,
                )
                for node_t in type_resolvers
            ]
            awaitable_nodes = [nodes for nodes in resolved_nodes if inspect.isawaitable(nodes)]
            # Async generators are not awaitable, so we need to handle them separately
            asyncgen_nodes = [nodes for nodes in resolved_nodes if inspect.isasyncgen(nodes)]

            if awaitable_nodes or asyncgen_nodes:

                async def resolve(resolved=resolved_nodes):  # noqa: ANN001
                    # Resolve all awaitable nodes concurrently
                    resolved = await asyncio.gather(
                        *awaitable_nodes,
                        *(asyncgen_to_list(nodes) for nodes in asyncgen_nodes),
                    )

                    # Resolve any generator to lists
                    resolved = [list(nodes) for nodes in resolved]
                    nodes_by_gid = self.nodes_by_gid(resolved)
                    return [nodes_by_gid.get(gid) for gid in ids]

                return resolve()

            # Resolve any generator to lists
            resolved = [list(cast(Iterator[Node], nodes)) for nodes in resolved_nodes]
            nodes_by_gid = self.nodes_by_gid(resolved)
            return [nodes_by_gid.get(gid) for gid in ids]

        return resolver


class ConnectionExtension(FieldExtension):
    connection_type: Type[Connection[Node]]

    def apply(self, field: StrawberryField) -> None:
        field.arguments = [
            *field.arguments,
            StrawberryArgument(
                python_name="before",
                graphql_name=None,
                type_annotation=StrawberryAnnotation(Optional[str]),
                description=("Returns the items in the list that come before the specified cursor."),
                default=None,
            ),
            StrawberryArgument(
                python_name="after",
                graphql_name=None,
                type_annotation=StrawberryAnnotation(Optional[str]),
                description=("Returns the items in the list that come after the specified cursor."),
                default=None,
            ),
            StrawberryArgument(
                python_name="first",
                graphql_name=None,
                type_annotation=StrawberryAnnotation(Optional[int]),
                description="Returns the first n items from the list.",
                default=None,
            ),
            StrawberryArgument(
                python_name="last",
                graphql_name=None,
                type_annotation=StrawberryAnnotation(Optional[int]),
                description=("Returns the items in the list that come after the specified cursor."),
                default=None,
            ),
        ]

        f_type = field.type
        if not isinstance(f_type, type) or not issubclass(f_type, Connection):
            raise RelayWrongAnnotationError(field.name, cast(type, field.origin))

        assert field.base_resolver
        # TODO: We are not using resolver_type.type because it will call
        # StrawberryAnnotation.resolve, which will strip async types from the
        # type (i.e. AsyncGenerator[Fruit] will become Fruit). This is done there
        # for subscription support, but we can't use it here. Maybe we can refactor
        # this in the future.
        resolver_type = field.base_resolver.signature.return_annotation
        if isinstance(resolver_type, str):
            resolver_type = ForwardRef(resolver_type)
        if isinstance(resolver_type, ForwardRef):
            resolver_type = eval_type(
                resolver_type,
                field.base_resolver._namespace,
                None,
            )

        origin = get_origin(resolver_type)
        if origin is None or not issubclass(origin, (Iterator, Iterable, AsyncIterator, AsyncIterable)):
            raise RelayWrongResolverAnnotationError(field.name, field.base_resolver)

        self.connection_type = cast(Type[Connection[Node]], field.type)

    def resolve(
        self,
        next_: SyncExtensionResolver,
        source: Any,
        info: Info,
        *,
        before: Optional[str] = None,
        after: Optional[str] = None,
        first: Optional[int] = None,
        last: Optional[int] = None,
        **kwargs: Any,
    ) -> Any:
        assert self.connection_type is not None
        return self.connection_type.resolve_connection(
            cast(Iterable[Node], next_(source, info, **kwargs)),
            info=info,
            before=before,
            after=after,
            first=first,
            last=last,
        )

    async def resolve_async(
        self,
        next_: AsyncExtensionResolver,
        source: Any,
        info: Info,
        *,
        before: Optional[str] = None,
        after: Optional[str] = None,
        first: Optional[int] = None,
        last: Optional[int] = None,
        **kwargs: Any,
    ) -> Any:
        assert self.connection_type is not None
        nodes = next_(source, info, **kwargs)
        # nodes might be an AsyncIterable/AsyncIterator
        # In this case we don't await for it
        if inspect.isawaitable(nodes):
            nodes = await nodes

        resolved = self.connection_type.resolve_connection(
            cast(Iterable[Node], nodes),
            info=info,
            before=before,
            after=after,
            first=first,
            last=last,
        )

        # If nodes was an AsyncIterable/AsyncIterator, resolve_connection
        # will return a coroutine which we need to await
        if inspect.isawaitable(resolved):
            resolved = await resolved
        return resolved


if TYPE_CHECKING:
    node = field
else:

    def node(*args: Any, **kwargs: Any) -> StrawberryField:
        kwargs["extensions"] = [*kwargs.get("extensions", []), NodeExtension()]
        return field(*args, **kwargs)


@overload
def connection(
    graphql_type: Optional[Type[Connection[NodeType]]] = None,
    *,
    resolver: Optional[_RESOLVER_TYPE[NodeIterableType[Any]]] = None,
    name: Optional[str] = None,
    is_subscription: bool = False,
    description: Optional[str] = None,
    init: Literal[True] = True,
    permission_classes: Optional[List[Type[BasePermission]]] = None,
    deprecation_reason: Optional[str] = None,
    default: Any = dataclasses.MISSING,
    default_factory: Union[Callable[..., object], object] = dataclasses.MISSING,
    metadata: Optional[Mapping[Any, Any]] = None,
    directives: Optional[Sequence[object]] = (),
    extensions: List[FieldExtension] = (),  # type: ignore
) -> Any: ...


@overload
def connection(
    graphql_type: Optional[Type[Connection[NodeType]]] = None,
    *,
    name: Optional[str] = None,
    is_subscription: bool = False,
    description: Optional[str] = None,
    permission_classes: Optional[List[Type[BasePermission]]] = None,
    deprecation_reason: Optional[str] = None,
    default: Any = dataclasses.MISSING,
    default_factory: Union[Callable[..., object], object] = dataclasses.MISSING,
    metadata: Optional[Mapping[Any, Any]] = None,
    directives: Optional[Sequence[object]] = (),
    extensions: List[FieldExtension] = (),  # type: ignore
) -> StrawberryField: ...


def connection(
    graphql_type: Optional[Type[Connection[NodeType]]] = None,
    *,
    resolver: Optional[_RESOLVER_TYPE[Any]] = None,
    name: Optional[str] = None,
    is_subscription: bool = False,
    description: Optional[str] = None,
    permission_classes: Optional[List[Type[BasePermission]]] = None,
    deprecation_reason: Optional[str] = None,
    default: Any = dataclasses.MISSING,
    default_factory: Union[Callable[..., object], object] = dataclasses.MISSING,
    metadata: Optional[Mapping[Any, Any]] = None,
    directives: Optional[Sequence[object]] = (),
    extensions: List[FieldExtension] = (),  # type: ignore
    # This init parameter is used by pyright to determine whether this field
    # is added in the constructor or not. It is not used to change
    # any behavior at the moment.
    init: Literal[True, False, None] = None,
) -> Any:
    """Annotate a property or a method to create a relay connection field.

    Relay connections are mostly used for pagination purposes. This decorator
    helps creating a complete relay endpoint that provides default arguments
    and has a default implementation for the connection slicing.

    Note that when setting a resolver to this field, it is expected for this
    resolver to return an iterable of the expected node type, not the connection
    itself. That iterable will then be paginated accordingly. So, the main use
    case for this is to provide a filtered iterable of nodes by using some custom
    filter arguments.

    Examples:
        Annotating something like this:

        >>> @strawberry.type
        >>> class X:
        ...     some_node: relay.Connection[SomeType] = relay.connection(
                    resolver=get_some_nodes,
        ...         description="ABC",
        ...     )
        ...
        ...     @relay.connection(relay.Connection[SomeType], description="ABC")
        ...     def get_some_nodes(self, age: int) -> Iterable[SomeType]:
        ...         ...

        Will produce a query like this:

        ```
        query {
            someNode (
                before: String
                after: String
                first: String
                after: String
                age: Int
            ) {
                totalCount
                pageInfo {
                    hasNextPage
                    hasPreviousPage
                    startCursor
                    endCursor
                }
                edges {
                    cursor
                    node {
                        id
                        ...
                    }
                }
            }
        }
        ```

    .. _Relay connections:
        https://relay.dev/graphql/connections.htm

    """
    f = StrawberryField(
        python_name=None,
        graphql_name=name,
        description=description,
        type_annotation=StrawberryAnnotation.from_annotation(graphql_type),
        is_subscription=is_subscription,
        permission_classes=permission_classes or [],
        deprecation_reason=deprecation_reason,
        default=default,
        default_factory=default_factory,
        metadata=metadata,
        directives=directives or (),
        extensions=[*extensions, ConnectionExtension()],
    )
    if resolver is not None:
        f = f(resolver)
    return f
