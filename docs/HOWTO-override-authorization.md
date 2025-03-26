# How To: Override Default Authorization

## Auth Principals

By default, Platformics reads user and role information from JWT's with a special structure:

```json
{
  "sub": "USERID GOES HERE",
  "project_claims": {
    "member": [123, 456],
    "owner": [789],
    "viewer": [333]
  }
}

```

However, this may not work for every use case - if your application needs to fetch user and role information from some other source (cookies, external databases, etc) then you'll need to replace Platformics' default behavior with your own. This is pretty straightforward though, since Platformics uses dependency injection to allow many of its default behaviors to be customized!

```python
# your_app/main.py

from platformics.settings import APISettings
from database import models
from fastapi import Depends
from platformics.api.core.deps import get_auth_principal
from platformics.security.authorization import Principal
from platformics.graphql_api.core.deps import get_settings, get_user_token
from platformics.security.token_auth import get_token_claims
from starlette.requests import Request

...

# Create and run app
app = get_app(settings, schema)


# This is a FastAPI Dependency (https://fastapi.tiangolo.com/tutorial/dependencies/) and can
# depend on any of platformics' built-in dependencies, or any extra dependencies you may choose
# to define!
def override_auth_principal(request: Request, settings: APISettings = Depends(get_settings), user_token: typing.optional[str] = Depends(get_user_token)) -> typing.Optional[Principal]:
    if user_token:
        claims = get_token_claims(user_token)
    else:
        claims = {"sub": "anonymous"}

    # Create an anonymous auth scope if we don't have a logged in user!
    return Principal(
        claims["sub"[,
        roles=["user"],
        attr={
            "user_id": claims["sub"],
            "owner_projects": [],
            "member_projects": [],
            "service_identity": [],
            # This value can be read from a secret or external db or anything you wish.
            # It's just hardcoded here for brevity.
            "viewer_projects": [444],
        },
    )

# This override ensures that every time the API tries to fetch information about a user and their
# roles, your code will be called instead of the Platformics built-in functionality.
app.dependency_overrides[get_auth_principal] = override_auth_principal

...
```

## Authorized Queries

Platformics generates authorized SQL queries via [Cerbos' SQLAlchemy](https://docs.cerbos.dev/cerbos/latest/recipes/orm/sqlalchemy/index.html) integration by default. If you need to add additional filters to queries, or even skip using Cerbos entirely, you'll need to extend the base `platformics.security.authorization.AuthzClient` class to suit your own needs, and update the app's dependencies to use your modified AuthzClient class instead:

```python
# your_app/main.py
import typing

from cerbos.sdk.model import Resource, ResourceDesc
from platformics.security.authorization import Principal, AuthzClient
from platformics.settings import APISettings
from sqlalchemy.sql import Select
from platformics.graphql_api.core.deps import get_authz_client
from fastapi import Depends

...

# You can override any subset of the following methods!
class CustomAuthzClient(AuthzClient):
    def __init__(self, settings: APISettings):
       # Set up your class
       ...

    def can_create(self, resource, principal: Principal) -> bool:
       # Return a boolean value representing whether the user has permission to create the resource
       ...

    def can_update(self, resource, principal: Principal) -> bool:
       # Return a boolean value representing whether the user has permission to update the resource
       ...

    def get_resource_query(self, principal: Principal, action: AuthzAction, model_cls, relationship) -> Select:
       # Return a SQLAlchemy query for the given model_cls with security filters already applied
       ...

    def modify_where_clause(self, principal: Principal, action: AuthzAction, model_cls, where_clauses) -> Select:
       # Add additional filters to a query before it is executed.
       ...

def get_customized_authz_client(settings: APISettings = Depends(get_settings)):
    return CustomAuthzClient(settings)

# This override ensures that every time the API tries to fetch an authorization client
# roles, your code will be called instead of the Platformics built-in functionality.
app.dependency_overrides[get_authz_client] = get_customized_authz_client

...
