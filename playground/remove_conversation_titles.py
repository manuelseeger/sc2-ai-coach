from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import click

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.persistence.database import get_database


@dataclass(frozen=True)
class UnsetFieldMigration:
    name: str
    description: str
    collection: str
    field: str

    @property
    def query(self) -> dict[str, Any]:
        return {self.field: {"$exists": True}}

    @property
    def update(self) -> dict[str, dict[str, str]]:
        return {"$unset": {self.field: ""}}


MIGRATIONS: dict[str, UnsetFieldMigration] = {
    "conversation-titles": UnsetFieldMigration(
        name="conversation-titles",
        description="Unset legacy title fields from ai_conversations documents.",
        collection="ai_conversations",
        field="title",
    ),
    "conversation-item-included-in-context": UnsetFieldMigration(
        name="conversation-item-included-in-context",
        description=(
            "Unset legacy included_in_context fields from ai_conversation_items documents."
        ),
        collection="ai_conversation_items",
        field="included_in_context",
    ),
}


def run_migration(database: Any, migration: UnsetFieldMigration, apply: bool) -> None:
    collection = database.raw[migration.collection]
    before_count = collection.count_documents(migration.query)

    click.echo(f"[{migration.name}] {migration.description}")
    click.echo(f"Documents with legacy {migration.field} field: {before_count}")

    if not apply:
        click.echo("Dry run only. Re-run with --apply to unset the field.")
        return

    result = collection.update_many(migration.query, migration.update)
    after_count = collection.count_documents(migration.query)

    click.echo(f"Matched documents: {result.matched_count}")
    click.echo(f"Modified documents: {result.modified_count}")
    click.echo(f"Remaining with {migration.field} field: {after_count}")


@click.command(
    context_settings={"help_option_names": ["-h", "--help"]},
    help="Run one or more simple field-unset migrations against the local database.",
)
@click.argument(
    "migrations",
    nargs=-1,
    type=click.Choice(sorted(MIGRATIONS)),
)
@click.option(
    "--apply",
    is_flag=True,
    help="Apply the selected migrations. Without this flag the script only reports counts.",
)
def main(migrations: tuple[str, ...], apply: bool) -> int:
    selected = migrations or tuple(MIGRATIONS)
    database = get_database()

    try:
        for index, migration_name in enumerate(selected):
            if index > 0:
                click.echo()
            run_migration(database, MIGRATIONS[migration_name], apply=apply)
        return 0
    finally:
        database.close()


if __name__ == "__main__":
    main()