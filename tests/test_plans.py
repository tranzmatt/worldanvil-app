import unittest
from unittest.mock import Mock

from worldanvil_cli.plans import PlanError, PlanExecutionError, apply_plan, parse_plan, preview


class PlanTests(unittest.TestCase):
    def test_plan_must_be_an_object(self):
        with self.assertRaisesRegex(PlanError, "JSON object"):
            parse_plan([])

    def test_plan_requires_operations(self):
        with self.assertRaisesRegex(PlanError, "non-empty array"):
            parse_plan({"operations": []})

    def test_update_requires_id(self):
        with self.assertRaisesRegex(PlanError, "id is required"):
            parse_plan({"operations": [{"action": "article.update", "data": {}}]})

    def test_unknown_action_is_rejected(self):
        with self.assertRaisesRegex(PlanError, "must be one of"):
            parse_plan({"operations": [{"action": "world.explode"}]})

    def test_world_create_requires_title_not_world_reference(self):
        operations = parse_plan({"operations": [{
            "action": "world.create",
            "data": {"title": "The Lantern Sea", "state": "private"},
        }]})
        self.assertEqual(operations[0].data["title"], "The Lantern Sea")

    def test_preview_validates_and_counts_destructive_operations(self):
        operations = parse_plan({"operations": [
            {"action": "category.create", "data": {"world": {"id": "w"}, "title": "Places"}},
            {"action": "article.delete", "id": "a"},
        ]})
        result = preview(operations)
        self.assertEqual(result["operationCount"], 2)
        self.assertEqual(result["destructiveOperationCount"], 1)

    def test_create_requires_semantic_fields(self):
        with self.assertRaisesRegex(PlanError, "data.templateType"):
            parse_plan({"operations": [
                {"action": "article.create", "data": {"world": {"id": "w"}, "title": "Harbor"}}
            ]})

    def test_apply_dispatches_in_order(self):
        client = Mock()
        client.create_category.return_value = {"id": "c"}
        client.update_article.return_value = {"id": "a"}
        operations = parse_plan({"operations": [
            {"action": "category.create", "data": {"world": {"id": "w"}, "title": "Places"}},
            {"action": "article.update", "id": "a", "data": {"title": "New"}},
        ]})
        result = apply_plan(client, operations)
        self.assertEqual(result["applied"], 2)
        client.create_category.assert_called_once()
        client.update_article.assert_called_once_with("a", {"title": "New"})

    def test_apply_reports_partial_completion(self):
        client = Mock()
        client.create_category.return_value = {"id": "c"}
        client.update_article.side_effect = RuntimeError("failed")
        operations = parse_plan({"operations": [
            {"action": "category.create", "data": {"world": {"id": "w"}, "title": "Places"}},
            {"action": "article.update", "id": "a", "data": {"title": "New"}},
        ]})
        with self.assertRaises(PlanExecutionError) as caught:
            apply_plan(client, operations)
        self.assertEqual(caught.exception.index, 1)
        self.assertEqual(len(caught.exception.completed), 1)

    def test_create_requires_nested_world_reference(self):
        with self.assertRaisesRegex(PlanError, "object containing id"):
            parse_plan({"operations": [{
                "action": "category.create",
                "data": {"world": "w", "title": "Places"},
            }]})


if __name__ == "__main__":
    unittest.main()
