"""Command-line interface for World Anvil."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .client import DEFAULT_BASE_URL, WorldAnvilClient, WorldAnvilError


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="worldanvil", description="Manipulate World Anvil via Boromir")
    root.add_argument("--base-url", default=DEFAULT_BASE_URL)
    root.add_argument("--user-agent", default="Tranzmatt-WorldAnvil (local, 0.1)")
    root.add_argument("--timeout", type=float, default=30)
    commands = root.add_subparsers(dest="command", required=True)

    commands.add_parser("identity", help="Show the authenticated user's identity")

    worlds = commands.add_parser("worlds", help="List worlds owned by a user")
    worlds.add_argument("--user-id", help="User UUID; omitted to discover it from /identity")
    _pagination(worlds)

    world = commands.add_parser("world", help="Read a world")
    world.add_argument("id")
    world.add_argument("--granularity", type=int, choices=(-1, 0, 1), default=1)

    articles = commands.add_parser("articles", help="List articles in a world")
    articles.add_argument("world_id")
    articles.add_argument("--category", help="Category UUID, or -1 for uncategorized")
    _pagination(articles)

    article = commands.add_parser("article", help="Read an article")
    article.add_argument("id")
    article.add_argument("--granularity", type=int, choices=(-1, 0, 1, 2, 3), default=2)

    create = commands.add_parser("create-article", help="Create an article from a JSON document")
    create.add_argument("--file", required=True, type=Path)

    update = commands.add_parser("update-article", help="Patch an article from a JSON document")
    update.add_argument("id")
    update.add_argument("--file", required=True, type=Path)

    delete = commands.add_parser("delete-article", help="Permanently delete an article")
    delete.add_argument("id")
    delete.add_argument("--yes", action="store_true", help="Confirm irreversible deletion")

    request = commands.add_parser("request", help="Call any Boromir endpoint")
    request.add_argument("method", choices=("GET", "POST", "PUT", "PATCH", "DELETE"))
    request.add_argument("path")
    request.add_argument("--param", action="append", default=[], metavar="KEY=VALUE")
    request.add_argument("--file", type=Path, help="JSON request body")
    request.add_argument("--yes", action="store_true", help="Confirm PUT/PATCH/DELETE")
    return root


def _pagination(command: argparse.ArgumentParser) -> None:
    command.add_argument("--limit", type=int, default=50)
    command.add_argument("--offset", type=int, default=0)


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        client = WorldAnvilClient.from_env(
            base_url=args.base_url, user_agent=args.user_agent, timeout=args.timeout
        )
        result = _execute(client, args)
        json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        return 0
    except (WorldAnvilError, ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"worldanvil: {exc}", file=sys.stderr)
        return 1


def _execute(client: WorldAnvilClient, args: argparse.Namespace) -> Any:
    if args.command == "identity":
        return client.identity()
    if args.command == "worlds":
        user_id = args.user_id or _extract_id(client.identity())
        return client.worlds(user_id, limit=args.limit, offset=args.offset)
    if args.command == "world":
        return client.world(args.id, granularity=args.granularity)
    if args.command == "articles":
        return client.articles(
            args.world_id, limit=args.limit, offset=args.offset, category=args.category
        )
    if args.command == "article":
        return client.article(args.id, granularity=args.granularity)
    if args.command == "create-article":
        return client.create_article(_load_object(args.file))
    if args.command == "update-article":
        return client.update_article(args.id, _load_object(args.file))
    if args.command == "delete-article":
        _require_yes(args.yes, "article deletion")
        return client.delete_article(args.id)
    if args.command == "request":
        if args.method in {"PUT", "PATCH", "DELETE"}:
            _require_yes(args.yes, f"{args.method} request")
        params = dict(_key_value(item) for item in args.param)
        body = _load_json(args.file) if args.file else None
        return client.request(args.method, args.path, params=params, json_body=body)
    raise AssertionError(f"Unhandled command: {args.command}")


def _extract_id(identity: Any) -> str:
    candidates = [identity]
    if isinstance(identity, dict):
        candidates.extend(identity.get(key) for key in ("entity", "user", "data"))
    for candidate in candidates:
        if isinstance(candidate, dict) and candidate.get("id"):
            return str(candidate["id"])
    raise WorldAnvilError("The /identity response did not contain a user id; pass --user-id")


def _load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def _load_object(path: Path) -> dict[str, Any]:
    value = _load_json(path)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _key_value(value: str) -> tuple[str, str]:
    if "=" not in value:
        raise ValueError(f"Expected KEY=VALUE, got {value!r}")
    return tuple(value.split("=", 1))  # type: ignore[return-value]


def _require_yes(confirmed: bool, action: str) -> None:
    if not confirmed:
        raise ValueError(f"Refusing {action} without --yes")


if __name__ == "__main__":
    raise SystemExit(main())

