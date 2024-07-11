# How To: Extending Platformics Generated Code
Platformics will generate a GraphQL API that exposes CRUD operations for each entity type in your LinkML schema. It is often the case, however, that you will need to expose more functionality in your API than just CRUD. There are a few options for extending generated code to add custom business logic to your application.

## Adding root-level queries and mutations
Platformics will generate basic read and aggregate queries in `api/queries.py`. These are inherited by a query class in `custom_queries.py`, which will gain access to all the codegenned queries as well as allow you to implement your own queries. To add a new root level field (query), add the field to the query class in `custom_queries.py`:

```
@strawberry.type
class Query(BaseQuery):
    foo: str = my_custom_field
```
The resolver for the custom field should be decorated with `@strawberry.field`:
```
@strawberry.field
def my_custom_field(self) -> str:
    return "foo"
```

Similarly, for custom mutations, root level mutations can be added to the `Mutation` class in `custom_mutations.py`, which inherits from the codegenned `Mutation` class in `api/mutations.py`

```
@strawberry.type
class Mutation(BaseMutation):
    bar: str = my_custom_mutation
```
The resolver for the custom mutation should be decorated with `@strawberry.mutation`:
```
@strawberry.mutation
def my_custom_mutation(self) -> str:
    return "bar"
```
Both the custom query and mutation classes are imported into `main.py` and used by Strawberry to generate an API at runtime:
```
from custom_mutations import Mutation
from custom_queries import Query

schema = strawberry.Schema(query=Query, mutation=Mutation, config=get_strawberry_config(), extensions=[HandleErrors()])
```

### Overriding queries and mutations
By creating a field with the same name as an existing codegenned query or mutation, you can override the codegenned resolver.
```
@strawberry.mutation
def my_override_mutation(self) -> str:
    return "Sorry, I overrode the mutation"

@strawberry.type
class Mutation(BaseMutation):
    create_sample: str = my_override_mutation
```

## Using your own templates
TODO: fill this out. Existing functionality.
