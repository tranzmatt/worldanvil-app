import unittest
from unittest.mock import Mock

from worldanvil_cli.plans import PlanError, PlanExecutionError, apply_plan, parse_plan, preview


class PlanTests(unittest.TestCase):
    def test_preview_validates_and_counts_destructive_operations(self):
        operations = parse_plan({"operations": [
            {"action": "category.create", "data": {"world": "w", "title": "Places"}},
            {"action": "article.delete", "id": "a"},
        ]})
        result = preview(operations)
        self.assertEqual(result["operationCount"], 2)
        self.assertEqual(result["destructiveOperationCount"], 1)

    def test_create_requires_semantic_fields(self):
        with self.assertRaisesRegex(PlanError, "data.template"):
            parse_plan({"operations": [
                {"action": "article.create", "data": {"world": "w", "title": "Harbor"}}
            ]})

    def test_apply_dispatches_in_order(self):
        client = Mock()
        client.create_category.return_value = {"id": "c"}
        client.update_article.return_value = {"id": "a"}
        operations = parse_plan({"operations": [
            {"action": "category.create", "data": {"world": "w", "title": "Places"}},
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
            {"action": "category.create", "data": {"world": "w", "title": "Places"}},
            {"action": "article.update", "id": "a", "data": {"title": "New"}},
        ]})
        with self.assertRaises(PlanExecutionError) as caught:
            apply_plan(client, operations)
        self.assertEqual(caught.exception.index, 1)
        self.assertEqual(len(caught.exception.completed), 1)


if __name__ == "__main__":
    unittest.main()
