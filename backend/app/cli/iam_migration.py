"""Operator entrypoint for the one-time IAM migration."""

import json

import click
from flask import current_app

from app.services.iam_migration_service import IamMigrationApi, LegacyIamMigrator


@click.command("iam-migrate")
@click.option(
    "--apply",
    is_flag=True,
    help="执行迁移；不传时只做只读预检。",
)
@click.option(
    "--link-existing",
    multiple=True,
    metavar="USERNAME_OR_EMAIL",
    help="显式允许旧账号绑定 IAM 中同名的既有账号，可重复指定。",
)
@click.option(
    "--force",
    is_flag=True,
    help="重新提交已成功实体，用于受控对账。",
)
def iam_migrate_command(apply: bool, link_existing: tuple[str, ...], force: bool):
    """Preflight or migrate legacy users, tenants and memberships into IAM."""
    preflight = LegacyIamMigrator.preflight()
    if not apply:
        click.echo(json.dumps(preflight.as_dict(), ensure_ascii=False, indent=2))
        if not preflight.ok:
            raise click.ClickException("IAM 迁移预检失败")
        return
    if not preflight.ok:
        click.echo(json.dumps(preflight.as_dict(), ensure_ascii=False, indent=2))
        raise click.ClickException("IAM 迁移预检失败，未写入任何迁移数据")

    api = IamMigrationApi(
        current_app.config["IAM_INTERNAL_URL"],
        current_app.config["IAM_REALM"],
        current_app.config["IAM_MIGRATOR_CLIENT_ID"],
        current_app.config["IAM_MIGRATOR_CLIENT_SECRET"],
    )
    report = LegacyIamMigrator(
        api,
        link_existing=set(link_existing),
        bootstrap_username=current_app.config.get("ADMIN_USERNAME", "admin"),
        force=force,
    ).run()
    click.echo(json.dumps(report.as_dict(), ensure_ascii=False, indent=2))
    if not report.ok:
        raise click.ClickException("IAM 迁移存在失败实体，可修复后重新执行")


def register_commands(app) -> None:
    app.cli.add_command(iam_migrate_command)
