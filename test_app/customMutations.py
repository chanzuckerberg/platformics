import strawberry
from api.mutations import BaseMutation


@strawberry.mutation
def my_custom_mutation(self) -> str:
    return "bar"


@strawberry.type
class Mutation(BaseMutation):
    bar: str = my_custom_mutation
