import boto3
import typing

from botocore.client import Config
from cerbos.sdk.client import CerbosClient
from cerbos.sdk.model import Principal
from fastapi import Depends
from mypy_boto3_s3.client import S3Client
from mypy_boto3_sts.client import STSClient
from platformics.settings import APISettings
from platformics.database.connect import AsyncDB, init_async_db
from platformics.security.token_auth import get_token_claims
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request


def get_settings(request: Request) -> APISettings:
    """Get the settings object from the app state"""
    return request.app.state.entities_settings


async def get_engine(
    settings: APISettings = Depends(get_settings),
) -> typing.AsyncGenerator[AsyncDB, None]:
    """Wrap resolvers in a DB engine"""
    engine = init_async_db(settings.DB_URI)
    try:
        yield engine
    finally:
        pass


async def get_db_session(
    engine: AsyncDB = Depends(get_engine),
) -> typing.AsyncGenerator[AsyncSession, None]:
    """Wrap resolvers in a sqlalchemy-compatible db session"""
    session = engine.session()
    try:
        yield session
    finally:
        await session.close()  # type: ignore


def get_cerbos_client(settings: APISettings = Depends(get_settings)) -> CerbosClient:
    return CerbosClient(host=settings.CERBOS_URL)


def get_auth_principal(request: Request, settings: APISettings = Depends(get_settings)) -> typing.Optional[Principal]:
    auth_header = request.headers.get("authorization")
    if auth_header:
        parts = auth_header.split()
    if not auth_header or len(parts) != 2:
        return None
    if parts[0].lower() != "bearer":
        return None

    try:
        claims = get_token_claims(settings.JWK_PRIVATE_KEY, parts[1])
    except:  # noqa
        return None

    # role_map is a bit brute-force to make cerbos-sqlalchemy happy, but it's fine
    # for now.
    role_map: dict[str, list[int]] = {}
    for project in claims["projects"]:
        for role in project["roles"]:
            if role not in role_map:
                role_map[role] = []
            role_map[role].append(project["project_id"])
    return Principal(
        claims["sub"],
        roles=["user"],
        attr={
            "user_id": int(claims["sub"]),
            "admin_projects": role_map.get("admin", []),
            "member_projects": role_map.get("member", []),
        },
    )


def require_auth_principal(
    principal: typing.Optional[Principal] = Depends(get_auth_principal),
) -> Principal:
    if not principal:
        raise Exception("Unauthorized")
    return principal


def get_s3_client(
    settings: APISettings = Depends(get_settings),
) -> S3Client:
    return boto3.client(
        "s3",
        region_name=settings.AWS_REGION,
        endpoint_url=settings.BOTO_ENDPOINT_URL,
        config=Config(signature_version="s3v4"),
    )


def get_sts_client(
    settings: APISettings = Depends(get_settings),
) -> STSClient:
    return boto3.client("sts", region_name=settings.AWS_REGION, endpoint_url=settings.BOTO_ENDPOINT_URL)
