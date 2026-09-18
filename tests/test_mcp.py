import os
import unittest
from unittest.mock import patch

from worldanvil_cli.mcp import TOOLS, call_tool, handle_message


class McpTests(unittest.TestCase):
    def test_tool_names_are_unique(self):
        names = [tool["name"] for tool in TOOLS]
        self.assertEqual(len(names), len(set(names)))

    def test_initialize_and_tool_listing(self):
        initialized = handle_message({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2025-06-18"},
        })
        self.assertEqual(initialized["result"]["protocolVersion"], "2025-06-18")
        listed = handle_message({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        self.assertGreater(len(listed["result"]["tools"]), 5)

    def test_preview_plan_is_offline(self):
        result = call_tool("worldanvil_preview_plan", {
            "plan": {
                "operations": [{
                    "action": "article.update",
                    "id": "article-id",
                    "data": {"title": "Revised"},
                }]
            }
        })
        self.assertTrue(result["valid"])
        self.assertEqual(result["operationCount"], 1)

    def test_mutation_requires_confirmation_before_client_creation(self):
        with patch("worldanvil_cli.mcp._client") as client:
            with self.assertRaisesRegex(ValueError, "Refusing mutation"):
                call_tool("worldanvil_apply_plan", {
                    "confirmed": False,
                    "plan": {
                        "operations": [{
                            "action": "article.delete",
                            "id": "article-id",
                        }]
                    },
                })
        client.assert_not_called()

    def test_doctor_reports_names_not_values(self):
        with patch.dict(os.environ, {
            "WORLDANVIL_API_KEY": "do-not-print-key",
            "WORLDANVIL_TOKEN": "do-not-print-token",
        }, clear=True):
            result = call_tool("worldanvil_doctor")
        self.assertEqual(result["credentials"], {
            "WORLDANVIL_API_KEY": True,
            "WORLDANVIL_TOKEN": True,
        })
        self.assertNotIn("do-not-print", str(result))

    def test_tool_errors_use_mcp_result(self):
        response = handle_message({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "worldanvil_apply_plan", "arguments": {}},
        })
        self.assertTrue(response["result"]["isError"])


if __name__ == "__main__":
    unittest.main()
