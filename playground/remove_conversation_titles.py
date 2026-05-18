from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.persistence.database import get_database


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Unset legacy title fields from ai_conversations documents."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply the migration. Without this flag the script only reports counts.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    database = get_database()

    try:
        collection = database.raw["ai_conversations"]
        query = {"title": {"$exists": True}}
        before_count = collection.count_documents(query)

        print(f"Conversations with legacy title field: {before_count}")

        if not args.apply:
            print("Dry run only. Re-run with --apply to unset the field.")
            return 0

        result = collection.update_many(query, {"$unset": {"title": ""}})
        after_count = collection.count_documents(query)

        print(f"Matched documents: {result.matched_count}")
        print(f"Modified documents: {result.modified_count}")
        print(f"Remaining with title field: {after_count}")
        return 0
    finally:
        database.close()


if __name__ == "__main__":
    raise SystemExit(main())