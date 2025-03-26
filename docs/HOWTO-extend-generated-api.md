# How To: Extending Platformics Generated API's
Platformics will generate a GraphQL API that exposes CRUD operations for each entity type in your LinkML schema. It is often the case, however, that you will need to expose more functionality in your API than just CRUD. There are a few options for extending generated code to add custom business logic to your application.


## Adding custom REST endpoints
Platformics primarily generates a GraphQL API, but there are certain functionalities (such as file downloads) that aren't practical to expose via GraphQL. Fortunately, Platformics is built on top of [FastAPI](https://fastapi.tiangolo.com/), a popular REST API framework. Adding custom endpoints is fairly straightforward:

```python
# your_app/main.py

# This code is already in main.py (app is a standard FastAPI application)
app = get_app(settings, schema)

# This adds an extra REST endpoint at GET http://localhost:9009/example
@app.get("/example")
def read_root():
    return {"Hello": "World"}

```

## Adding root-level GraphQL queries and mutations
Platformics will generate basic read and aggregate queries in `api/queries.py`. These are inherited by a query class in `custom_queries.py`, which will gain access to all the codegenned queries as well as allow you to implement your own queries. To add a new root level field (query), add the field to the query class in `custom_queries.py`:

```python
# your_app/custom_queries.py

import strawberry
from api.queries import Query as BaseQuery

# The resolver for the custom field should be decorated with `@strawberry.field`:
@strawberry.field
def my_custom_field(self) -> str:
    return "foo"

@strawberry.type
class Query(BaseQuery):
    foo: str = my_custom_field
```

Similarly, for custom mutations, root level mutations can be added to the `Mutation` class in `custom_mutations.py`, which inherits from the codegenned `Mutation` class in `api/mutations.py`

```python
# your_app/custom_mutations.py
import strawberry
from api.mutations import Mutation as BaseMutation

# The resolver for the custom mutation should be decorated with `@strawberry.mutation`:
@strawberry.mutation
def my_custom_mutation(self) -> str:
    return "bar"

@strawberry.type
class Mutation(BaseMutation):
    bar: str = my_custom_mutation
```

Both the custom query and mutation classes are imported into `main.py` and used by Strawberry to generate an API at runtime:
```python
# your_app/main.py
from custom_mutations import Mutation
from custom_queries import Query

schema = strawberry.Schema(query=Query, mutation=Mutation, config=get_strawberry_config(), extensions=[HandleErrors()])
```

### Overriding queries and mutations
By creating a field with the same name as an existing codegenned query or mutation, you can override the codegenned resolver.
```python
# your_app/custom_mutations.py
@strawberry.mutation
def my_override_mutation(self) -> str:
    return "Sorry, I overrode the mutation"

@strawberry.type
class Mutation(BaseMutation):
    create_sample: str = my_override_mutation
```

## Using your own templates
TODO: fill this out. Existing functionality.
