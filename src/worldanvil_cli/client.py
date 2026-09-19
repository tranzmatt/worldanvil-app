"""Dependency-free client for the World Anvil Boromir API."""

from __future__ import annotations

import json
import os
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

DEFAULT_BASE_URL = "https://www.worldanvil.com/api/external/boromir"


class WorldAnvilError(RuntimeError):
    """An API, network, configuration, or response error."""

    def __init__(self, message: str, *, status: int | None = None, body: Any = None):
        super().__init__(message)
        self.status = status
        self.body = body


class WorldAnvilClient:
    """A compact client which keeps credentials in memory and out of URLs."""

    def __init__(
        self,
        application_key: str,
        auth_token: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        user_agent: str = "Tranzmatt-WorldAnvil (local, 0.1)",
        timeout: float = 30,
    ) -> None:
        if not application_key or not auth_token:
            raise WorldAnvilError("Both an application key and auth token are required")
        self.application_key = application_key
        self.auth_token = auth_token
        self.base_url = base_url.rstrip("/")
        self.user_agent = user_agent
        self.timeout = timeout

    @classmethod
    def from_env(cls, **kwargs: Any) -> "WorldAnvilClient":
        """Construct from WORLDANVIL_API_KEY and WORLDANVIL_TOKEN."""
        key = os.environ.get("WORLDANVIL_API_KEY", "")
        token = os.environ.get("WORLDANVIL_TOKEN", "")
        if not key or not token:
            missing = [
                name
                for name, value in (
                    ("WORLDANVIL_API_KEY", key),
                    ("WORLDANVIL_TOKEN", token),
                )
                if not value
            ]
            raise WorldAnvilError(
                "Missing required environment variable(s): "
                + ", ".join(missing)
                + ". Set them in the environment that launches the World Anvil plugin, "
                "then restart the host application so it can inherit them."
            )
        return cls(key, token, **kwargs)

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json_body: Any = None,
    ) -> Any:
        """Send one JSON request. Authentication is always sent in headers."""
        if not path.startswith("/"):
            path = "/" + path
        query = urlencode(
            [(key, value) for key, value in (params or {}).items() if value is not None],
            doseq=True,
        )
        url = self.base_url + path + (("?" + query) if query else "")
        data = None if json_body is None else json.dumps(json_body).encode("utf-8")
        request = Request(
            url,
            data=data,
            method=method.upper(),
            headers={
                "x-application-key": self.application_key,
                "x-auth-token": self.auth_token,
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": self.user_agent,
            },
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                payload = response.read()
        except HTTPError as exc:
            payload = exc.read()
            body = _decode_response(payload)
            message = _error_message(body) or exc.reason or "HTTP error"
            raise WorldAnvilError(
                f"World Anvil returned HTTP {exc.code}: {message}",
                status=exc.code,
                body=body,
            ) from None
        except (URLError, TimeoutError) as exc:
            reason = getattr(exc, "reason", exc)
            raise WorldAnvilError(f"Could not reach World Anvil: {reason}") from None
        return _decode_response(payload)

    def identity(self) -> Any:
        return self.request("GET", "/identity")

    def worlds(self, user_id: str, *, limit: int = 50, offset: int = 0) -> Any:
        return self.request(
            "POST", "/user/worlds", params={"id": user_id},
            json_body={"limit": limit, "offset": offset},
        )

    def world(self, world_id: str, *, granularity: int = 1) -> Any:
        return self.request("GET", "/world", params={"id": world_id, "granularity": granularity})

    def create_world(self, document: Mapping[str, Any]) -> Any:
        return self.request("PUT", "/world", json_body=document)

    def update_world(self, world_id: str, changes: Mapping[str, Any]) -> Any:
        return self.request("PATCH", "/world", params={"id": world_id}, json_body=changes)

    def delete_world(self, world_id: str) -> Any:
        return self.request("DELETE", "/world", params={"id": world_id})

    def articles(
        self, world_id: str, *, limit: int = 50, offset: int = 0,
        category: str | None = None,
    ) -> Any:
        body: dict[str, Any] = {"limit": limit, "offset": offset}
        if category is not None:
            body["category"] = category
        return self.request("POST", "/world/articles", params={"id": world_id}, json_body=body)

    def categories(self, world_id: str, *, limit: int = 50, offset: int = 0) -> Any:
        return self.request(
            "POST", "/world/categories", params={"id": world_id},
            json_body={"limit": limit, "offset": offset},
        )

    def category(self, category_id: str, *, granularity: int = 2) -> Any:
        return self.request(
            "GET", "/category", params={"id": category_id, "granularity": granularity}
        )

    def create_category(self, document: Mapping[str, Any]) -> Any:
        return self.request("PUT", "/category", json_body=document)

    def update_category(self, category_id: str, changes: Mapping[str, Any]) -> Any:
        return self.request("PATCH", "/category", params={"id": category_id}, json_body=changes)

    def delete_category(self, category_id: str) -> Any:
        return self.request("DELETE", "/category", params={"id": category_id})

    def article(self, article_id: str, *, granularity: int = 2) -> Any:
        return self.request(
            "GET", "/article", params={"id": article_id, "granularity": granularity}
        )

    def create_article(self, document: Mapping[str, Any]) -> Any:
        return self.request("PUT", "/article", json_body=document)

    def update_article(self, article_id: str, changes: Mapping[str, Any]) -> Any:
        return self.request("PATCH", "/article", params={"id": article_id}, json_body=changes)

    def delete_article(self, article_id: str) -> Any:
        return self.request("DELETE", "/article", params={"id": article_id})


def _decode_response(payload: bytes) -> Any:
    if not payload:
        return None
    text = payload.decode("utf-8", errors="replace")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def _error_message(body: Any) -> str | None:
    if isinstance(body, dict):
        for key in ("message", "error", "detail", "description"):
            value = body.get(key)
            if isinstance(value, str):
                return value
    return body if isinstance(body, str) else None
