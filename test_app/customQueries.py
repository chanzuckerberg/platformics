import strawberry
from api.queries import BaseQuery


@strawberry.field
def my_custom_field(self) -> str:
    return "foo"


@strawberry.type
class Query(BaseQuery):

    foo: str = my_custom_field
