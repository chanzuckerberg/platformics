"""
Code generation script to generate SQLAlchemy models, GraphQL types,
Cerbos policies, and Factoryboy factories from a LinkML schema.
"""

import logging

import click

from platformics.codegen.generator import generate
from platformics.security.token_auth import create_token
from platformics.settings import APISettings


@click.group()
@click.option(
    "--debug",
    is_flag=True,
    default=False,
    help="Enable debug output",
)
@click.option(
    "--token",
    type=str,
    help="Auth token to use for requests",
    envvar="PLATFORMICS_AUTH_TOKEN",
)
@click.pass_context
def cli(ctx: click.Context, debug: bool, token: str) -> None:
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    if debug:
        logger.setLevel(logging.DEBUG)
    ctx.ensure_object(dict)
    ctx.obj["auth_token"] = token


@cli.group()
def api() -> None:
    pass


@api.command("generate")
@click.option("--schemafile", type=str, required=True)
@click.option("--output-prefix", type=str, required=True)
@click.option("--template-override-paths", type=str, multiple=True)
@click.pass_context
def api_generate(
    ctx: click.Context,
    schemafile: str,
    output_prefix: str,
    template_override_paths: tuple[str],
) -> None:
    """
    Launch code generation
    """
    generate(schemafile, output_prefix, template_override_paths)


@cli.group()
def auth() -> None:
    pass


@auth.command("generate-token")
@click.argument("userid", required=True, type=int)
@click.option("--expiration", help="Duration of token in seconds", type=int)
@click.option(
    "--project",
    help="project_id:role associations to include in the header",
    type=str,
    default=["123:owner", "123:member", "456:member"],
    multiple=True,
)
@click.pass_context
def generate_token(ctx: click.Context, userid: int, project: list[str], expiration: int) -> None:
    settings = APISettings.model_validate({})
    private_key = settings.JWK_PRIVATE_KEY

    project_roles: dict[str, list[int]] = {"member": [], "owner": [], "viewer": []}
    for item in project:
        project_id, role = item.split(":")
        project_roles[role].append(int(project_id))
    token = create_token(private_key, userid, project_roles, expiration)
    print(token)


if __name__ == "__main__":
    cli()  # type: ignore
