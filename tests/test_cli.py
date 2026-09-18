import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

from worldanvil_cli.cli import _execute, main, parser


class CliTests(unittest.TestCase):
    def test_doctor_is_offline_and_does_not_expose_credentials(self):
        stdout = io.StringIO()
        with patch.dict(os.environ, {
            "WORLDANVIL_API_KEY": "private-app-key",
            "WORLDANVIL_TOKEN": "private-token",
        }, clear=True), redirect_stdout(stdout):
            status = main(["doctor"])
        self.assertEqual(status, 0)
        result = json.loads(stdout.getvalue())
        self.assertTrue(result["ok"])
        self.assertFalse(result["live"])
        self.assertNotIn("private-app-key", stdout.getvalue())
        self.assertNotIn("private-token", stdout.getvalue())

    def test_plan_preview_does_not_require_credentials(self):
        plan = {"operations": [{
            "action": "category.create",
            "data": {"world": {"id": "world-id"}, "title": "Places"},
        }]}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "plan.json")
            path.write_text(json.dumps(plan), encoding="utf-8")
            stdout = io.StringIO()
            with patch.dict(os.environ, {}, clear=True), redirect_stdout(stdout):
                status = main(["plan", str(path)])
        self.assertEqual(status, 0)
        self.assertEqual(json.loads(stdout.getvalue())["operationCount"], 1)

    def test_create_article_refuses_without_confirmation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "article.json")
            path.write_text("{}", encoding="utf-8")
            args = parser().parse_args(["create-article", "--file", str(path)])
            with self.assertRaisesRegex(ValueError, "without --yes"):
                _execute(Mock(), args)

    def test_apply_plan_refuses_without_confirmation(self):
        plan = {"operations": [{
            "action": "category.create",
            "data": {"world": {"id": "world-id"}, "title": "Places"},
        }]}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "plan.json")
            path.write_text(json.dumps(plan), encoding="utf-8")
            args = parser().parse_args(["apply-plan", str(path)])
            with self.assertRaisesRegex(ValueError, "without --yes"):
                _execute(Mock(), args)

    def test_invalid_plan_returns_nonzero_and_diagnostic(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "plan.json")
            path.write_text('{"operations":[]}', encoding="utf-8")
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                status = main(["plan", str(path)])
        self.assertEqual(status, 1)
        self.assertIn("non-empty array", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
