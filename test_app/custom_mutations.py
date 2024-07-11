import strawberry
from api.mutations import Mutation as BaseMutation


@strawberry.mutation
def my_custom_mutation(self) -> str:
    return "bar"

@strawberry.mutation
def my_override_mutation(self) -> str:
    return "Sorry, I overrode the mutation"


@strawberry.type
class Mutation(BaseMutation):
    bar: str = my_custom_mutation
    create_sample: str = my_override_mutation
