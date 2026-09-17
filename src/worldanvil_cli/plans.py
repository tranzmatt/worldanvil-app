"""Validated, reviewable mutation plans for agent-driven World Anvil changes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from .client import WorldAnvilClient


class PlanError(ValueError):
    """A plan is malformed or contains an unsupported operation."""


class PlanExecutionError(RuntimeError):
    """A plan stopped after one or more operations may have succeeded."""

    def __init__(self, index: int, operation: "Operation", completed: list[dict[str, Any]], cause: Exception):
        self.index = index
        self.operation = operation
        self.completed = completed
        super().__init__(
            f"plan stopped at operation {index} ({operation.action}) after "
            f"{len(completed)} successful operation(s): {cause}"
        )


@dataclass(frozen=True)
class Operation:
    action: str
    data: dict[str, Any]
    resource_id: str | None = None
    note: str | None = None

    @classmethod
    def parse(cls, value: Any, index: int) -> "Operation":
        if not isinstance(value, dict):
            raise PlanError(f"operations[{index}] must be an object")
        action = value.get("action")
        if action not in ACTIONS:
            choices = ", ".join(sorted(ACTIONS))
            raise PlanError(f"operations[{index}].action must be one of: {choices}")
        data = value.get("data", {})
        if not isinstance(data, dict):
            raise PlanError(f"operations[{index}].data must be an object")
        resource_id = value.get("id")
        if action.endswith((".update", ".delete")) and not resource_id:
            raise PlanError(f"operations[{index}].id is required for {action}")
        for required in ACTIONS[action]:
            if not data.get(required):
                raise PlanError(f"operations[{index}].data.{required} is required for {action}")
        note = value.get("note")
        return cls(action, dict(data), str(resource_id) if resource_id else None, note)

    def summary(self) -> dict[str, Any]:
        result: dict[str, Any] = {"action": self.action}
        if self.resource_id:
            result["id"] = self.resource_id
        if self.data:
            result["data"] = self.data
        if self.note:
            result["note"] = self.note
        return result


ACTIONS: dict[str, tuple[str, ...]] = {
    "category.create": ("world", "title"),
    "category.update": (),
    "category.delete": (),
    "article.create": ("world", "title", "template"),
    "article.update": (),
    "article.delete": (),
}


def parse_plan(value: Any) -> list[Operation]:
    if not isinstance(value, dict):
        raise PlanError("plan must be a JSON object")
    raw = value.get("operations")
    if not isinstance(raw, list) or not raw:
        raise PlanError("plan.operations must be a non-empty array")
    return [Operation.parse(item, index) for index, item in enumerate(raw)]


def preview(operations: Sequence[Operation]) -> dict[str, Any]:
    destructive = sum(op.action.endswith(".delete") for op in operations)
    return {
        "valid": True,
        "operationCount": len(operations),
        "destructiveOperationCount": destructive,
        "operations": [op.summary() for op in operations],
    }


def apply_plan(client: WorldAnvilClient, operations: Sequence[Operation]) -> dict[str, Any]:
    """Apply in order and stop at the first failure; this is not transactional."""
    results: list[dict[str, Any]] = []
    for index, operation in enumerate(operations):
        try:
            result = _apply(client, operation)
        except Exception as exc:
            raise PlanExecutionError(index, operation, results, exc) from exc
        results.append({"index": index, "action": operation.action, "result": result})
    return {"success": True, "applied": len(results), "results": results}


def _apply(client: WorldAnvilClient, operation: Operation) -> Any:
    if operation.action == "category.create":
        return client.create_category(operation.data)
    if operation.action == "category.update":
        return client.update_category(operation.resource_id or "", operation.data)
    if operation.action == "category.delete":
        return client.delete_category(operation.resource_id or "")
    if operation.action == "article.create":
        return client.create_article(operation.data)
    if operation.action == "article.update":
        return client.update_article(operation.resource_id or "", operation.data)
    if operation.action == "article.delete":
        return client.delete_article(operation.resource_id or "")
    raise AssertionError(operation.action)
