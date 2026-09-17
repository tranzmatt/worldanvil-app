"""Two-pass world population with symbolic references and a UUID manifest."""

from __future__ import annotations

import re
from typing import Any, Mapping

from .client import WorldAnvilClient


class BlueprintError(ValueError):
    """A blueprint is invalid."""


class BlueprintExecutionError(RuntimeError):
    """Blueprint execution stopped; manifest contains resources already created."""

    def __init__(self, phase: str, manifest: dict[str, Any], cause: Exception):
        self.phase = phase
        self.manifest = manifest
        super().__init__(f"blueprint stopped during {phase}: {cause}; manifest={manifest}")


TOKEN = re.compile(r"\{\{(article|category):([a-z0-9_-]+)(?:\|([^}]+))?\}\}")


def validate_blueprint(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise BlueprintError("blueprint must be a JSON object")
    world = value.get("world")
    if not isinstance(world, dict) or not world.get("title"):
        raise BlueprintError("blueprint.world.title is required")
    categories = _keyed_list(value.get("categories", []), "categories")
    articles = _keyed_list(value.get("articles", []), "articles")
    category_keys = {item["key"] for item in categories}
    for index, article in enumerate(articles):
        for field in ("title", "templateType"):
            if not article.get(field):
                raise BlueprintError(f"blueprint.articles[{index}].{field} is required")
        category = article.get("category")
        if category is not None and category not in category_keys:
            raise BlueprintError(
                f"blueprint.articles[{index}].category refers to unknown key {category!r}"
            )
    return {
        "world": dict(world),
        "categories": categories,
        "articles": articles,
        "homepage": dict(value.get("homepage", {})),
    }


def preview_blueprint(value: Any) -> dict[str, Any]:
    blueprint = validate_blueprint(value)
    return {
        "valid": True,
        "world": blueprint["world"],
        "categoryCount": len(blueprint["categories"]),
        "articleCount": len(blueprint["articles"]),
        "categories": [item["key"] for item in blueprint["categories"]],
        "articles": [item["key"] for item in blueprint["articles"]],
        "phases": ["world", "categories", "article skeletons", "linked content", "homepage"],
    }


def apply_blueprint(client: WorldAnvilClient, value: Any) -> dict[str, Any]:
    blueprint = validate_blueprint(value)
    manifest: dict[str, Any] = {"world": None, "categories": {}, "articles": {}}
    phase = "world"
    try:
        world_result = client.create_world(blueprint["world"])
        world_id = _resource_id(world_result)
        manifest["world"] = world_id

        phase = "categories"
        for item in blueprint["categories"]:
            payload = {key: value for key, value in item.items() if key != "key"}
            payload["world"] = {"id": world_id}
            result = client.create_category(payload)
            manifest["categories"][item["key"]] = _resource_id(result)

        phase = "article skeletons"
        article_specs = {item["key"]: item for item in blueprint["articles"]}
        for item in blueprint["articles"]:
            payload = {
                key: value
                for key, value in item.items()
                if key not in {"key", "category", "content"}
            }
            payload["world"] = {"id": world_id}
            if item.get("category"):
                payload["category"] = {"id": manifest["categories"][item["category"]]}
            result = client.create_article(payload)
            manifest["articles"][item["key"]] = _resource_id(result)

        phase = "linked content"
        for item in blueprint["articles"]:
            content = item.get("content")
            if content is not None:
                rendered = render(content, blueprint, manifest, article_specs)
                client.update_article(manifest["articles"][item["key"]], {"content": rendered})

        phase = "homepage"
        if blueprint["homepage"]:
            homepage = {
                key: render(value, blueprint, manifest, article_specs)
                if isinstance(value, str) else value
                for key, value in blueprint["homepage"].items()
            }
            client.update_world(world_id, homepage)
    except Exception as exc:
        raise BlueprintExecutionError(phase, manifest, exc) from exc
    return {"success": True, "manifest": manifest}


def render(
    text: str,
    blueprint: Mapping[str, Any],
    manifest: Mapping[str, Any],
    article_specs: Mapping[str, Mapping[str, Any]],
) -> str:
    def replace(match: re.Match[str]) -> str:
        kind, key, label = match.groups()
        if kind == "article":
            if key not in manifest["articles"]:
                raise BlueprintError(f"unknown article token key {key!r}")
            spec = article_specs[key]
            return f"@[{label or spec['title']}]({spec['templateType']}:{manifest['articles'][key]})"
        if key not in manifest["categories"]:
            raise BlueprintError(f"unknown category token key {key!r}")
        category = next(item for item in blueprint["categories"] if item["key"] == key)
        return f"[category:{manifest['categories'][key]}]{label or category['title']}[/category]"
    return TOKEN.sub(replace, text)


def _keyed_list(value: Any, field: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise BlueprintError(f"blueprint.{field} must be an array")
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, dict) or not item.get("key"):
            raise BlueprintError(f"blueprint.{field}[{index}].key is required")
        key = item["key"]
        if not isinstance(key, str) or not re.fullmatch(r"[a-z0-9_-]+", key):
            raise BlueprintError(f"blueprint.{field}[{index}].key has invalid characters")
        if key in seen:
            raise BlueprintError(f"duplicate blueprint.{field} key {key!r}")
        seen.add(key)
        result.append(dict(item))
    return result


def _resource_id(value: Any) -> str:
    candidates = [value]
    if isinstance(value, dict):
        candidates.extend(value.get(key) for key in ("entity", "data", "world", "category", "article"))
    for candidate in candidates:
        if isinstance(candidate, dict) and candidate.get("id"):
            return str(candidate["id"])
    raise BlueprintError("API response did not contain a resource id")
