"""Dependency-free stdio MCP server backed by the World Anvil client."""

from __future__ import annotations

import json
import os
import platform
import sys
from importlib.metadata import PackageNotFoundError, version
from typing import Any, Callable

from .blueprints import apply_blueprint, preview_blueprint
from .client import WorldAnvilClient, WorldAnvilError
from .plans import apply_plan, parse_plan, preview


def _object(properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    schema: dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if required:
        schema["required"] = required
    return schema


ID = {"type": "string", "minLength": 1}
INTEGER = {"type": "integer", "minimum": 0}

TOOLS: list[dict[str, Any]] = [
    {
        "name": "worldanvil_doctor",
        "description": "Check local configuration. With live=true, make only read-only identity and world-list calls.",
        "inputSchema": _object({"live": {"type": "boolean", "default": False}}),
        "annotations": {"readOnlyHint": True, "destructiveHint": False},
    },
    {
        "name": "worldanvil_list_worlds",
        "description": "List worlds owned by the authenticated World Anvil user.",
        "inputSchema": _object({
            "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 50},
            "offset": INTEGER,
        }),
        "annotations": {"readOnlyHint": True, "destructiveHint": False},
    },
    {
        "name": "worldanvil_get_world",
        "description": "Read one World Anvil world by opaque UUID.",
        "inputSchema": _object({"id": ID, "granularity": {"type": "integer", "enum": [-1, 0, 1]}}, ["id"]),
        "annotations": {"readOnlyHint": True, "destructiveHint": False},
    },
    {
        "name": "worldanvil_list_categories",
        "description": "List categories in a World Anvil world.",
        "inputSchema": _object({"world_id": ID, "limit": {"type": "integer", "minimum": 1, "maximum": 50}, "offset": INTEGER}, ["world_id"]),
        "annotations": {"readOnlyHint": True, "destructiveHint": False},
    },
    {
        "name": "worldanvil_get_category",
        "description": "Read one World Anvil category by opaque UUID.",
        "inputSchema": _object({"id": ID, "granularity": {"type": "integer", "enum": [-1, 0, 1, 2]}}, ["id"]),
        "annotations": {"readOnlyHint": True, "destructiveHint": False},
    },
    {
        "name": "worldanvil_list_articles",
        "description": "List articles in a World Anvil world, optionally filtered by category UUID.",
        "inputSchema": _object({
            "world_id": ID,
            "category": {"type": "string"},
            "limit": {"type": "integer", "minimum": 1, "maximum": 50},
            "offset": INTEGER,
        }, ["world_id"]),
        "annotations": {"readOnlyHint": True, "destructiveHint": False},
    },
    {
        "name": "worldanvil_get_article",
        "description": "Read one World Anvil article by opaque UUID.",
        "inputSchema": _object({"id": ID, "granularity": {"type": "integer", "enum": [-1, 0, 1, 2, 3]}}, ["id"]),
        "annotations": {"readOnlyHint": True, "destructiveHint": False},
    },
    {
        "name": "worldanvil_preview_plan",
        "description": "Validate and preview a JSON mutation plan without credentials or network access.",
        "inputSchema": _object({"plan": {"type": "object"}}, ["plan"]),
        "annotations": {"readOnlyHint": True, "destructiveHint": False},
    },
    {
        "name": "worldanvil_apply_plan",
        "description": "Apply the exact previously previewed plan. Set confirmed=true only after the user explicitly confirms that preview immediately before this call.",
        "inputSchema": _object({"plan": {"type": "object"}, "confirmed": {"type": "boolean"}}, ["plan", "confirmed"]),
        "annotations": {"readOnlyHint": False, "destructiveHint": True},
    },
    {
        "name": "worldanvil_preview_blueprint",
        "description": "Validate and preview a new interconnected world blueprint without network access.",
        "inputSchema": _object({"blueprint": {"type": "object"}}, ["blueprint"]),
        "annotations": {"readOnlyHint": True, "destructiveHint": False},
    },
    {
        "name": "worldanvil_apply_blueprint",
        "description": "Create a world from the exact previously previewed blueprint. Set confirmed=true only after immediate explicit user confirmation. API world deletion may be unavailable, so cleanup is not guaranteed.",
        "inputSchema": _object({"blueprint": {"type": "object"}, "confirmed": {"type": "boolean"}}, ["blueprint", "confirmed"]),
        "annotations": {"readOnlyHint": False, "destructiveHint": True},
    },
]


def _client() -> WorldAnvilClient:
    return WorldAnvilClient.from_env()


def _identity_id(client: WorldAnvilClient) -> str:
    value = client.identity()
    candidates = [value]
    if isinstance(value, dict):
        candidates.extend(value.get(key) for key in ("entity", "user", "data"))
    for candidate in candidates:
        if isinstance(candidate, dict) and candidate.get("id"):
            return str(candidate["id"])
    raise WorldAnvilError("The /identity response did not contain a user id")


def call_tool(name: str, arguments: dict[str, Any] | None = None) -> Any:
    args = arguments or {}
    if name == "worldanvil_doctor":
        credentials = {
            key: bool(os.environ.get(key))
            for key in ("WORLDANVIL_API_KEY", "WORLDANVIL_TOKEN")
        }
        try:
            package_version = version("worldanvil-cli")
        except PackageNotFoundError:
            package_version = "development"
        result: dict[str, Any] = {
            "ok": all(credentials.values()),
            "version": package_version,
            "python": platform.python_version(),
            "credentials": credentials,
            "live": False,
        }
        if args.get("live"):
            client = _client()
            user_id = _identity_id(client)
            worlds = client.worlds(user_id, limit=1)
            result.update({
                "ok": True,
                "live": True,
                "identity": {"id": user_id},
                "worldAccess": {
                    "ok": isinstance(worlds, dict) and isinstance(worlds.get("entities"), list)
                },
            })
        return result
    if name == "worldanvil_preview_plan":
        return preview(parse_plan(args["plan"]))
    if name == "worldanvil_preview_blueprint":
        return preview_blueprint(args["blueprint"])
    if name == "worldanvil_apply_plan":
        _require_confirmation(args)
        return apply_plan(_client(), parse_plan(args["plan"]))
    if name == "worldanvil_apply_blueprint":
        _require_confirmation(args)
        return apply_blueprint(_client(), args["blueprint"])

    client = _client()
    if name == "worldanvil_list_worlds":
        return client.worlds(
            _identity_id(client), limit=args.get("limit", 50), offset=args.get("offset", 0)
        )
    if name == "worldanvil_get_world":
        return client.world(args["id"], granularity=args.get("granularity", 1))
    if name == "worldanvil_list_categories":
        return client.categories(
            args["world_id"], limit=args.get("limit", 50), offset=args.get("offset", 0)
        )
    if name == "worldanvil_get_category":
        return client.category(args["id"], granularity=args.get("granularity", 2))
    if name == "worldanvil_list_articles":
        return client.articles(
            args["world_id"],
            limit=args.get("limit", 50),
            offset=args.get("offset", 0),
            category=args.get("category"),
        )
    if name == "worldanvil_get_article":
        return client.article(args["id"], granularity=args.get("granularity", 2))
    raise ValueError(f"Unknown tool: {name}")


def _require_confirmation(arguments: dict[str, Any]) -> None:
    if arguments.get("confirmed") is not True:
        raise ValueError(
            "Refusing mutation: preview the exact payload, obtain immediate explicit user "
            "confirmation, then call again with confirmed=true"
        )


def handle_message(message: dict[str, Any]) -> dict[str, Any] | None:
    method = message.get("method")
    request_id = message.get("id")
    if request_id is None:
        return None
    try:
        if method == "initialize":
            requested = (message.get("params") or {}).get("protocolVersion")
            result = {
                "protocolVersion": requested or "2025-06-18",
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "worldanvil", "version": "0.2.0"},
            }
        elif method == "ping":
            result = {}
        elif method == "tools/list":
            result = {"tools": TOOLS}
        elif method == "tools/call":
            params = message.get("params") or {}
            value = call_tool(params.get("name", ""), params.get("arguments"))
            result = {
                "content": [{
                    "type": "text",
                    "text": json.dumps(value, ensure_ascii=False, indent=2),
                }],
                "isError": False,
            }
            if isinstance(value, dict):
                result["structuredContent"] = value
        else:
            return _error(request_id, -32601, f"Method not found: {method}")
        return {"jsonrpc": "2.0", "id": request_id, "result": result}
    except Exception as exc:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "content": [{"type": "text", "text": str(exc)}],
                "isError": True,
            },
        }


def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }


def main() -> int:
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            message = json.loads(line)
            response = handle_message(message)
        except Exception as exc:
            response = _error(None, -32700, f"Parse error: {exc}")
        if response is not None:
            sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
