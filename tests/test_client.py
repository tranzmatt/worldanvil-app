import io
import json
import os
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from worldanvil_cli.client import WorldAnvilClient, WorldAnvilError


class Response:
    def __init__(self, value):
        self.value = value

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read(self):
        return json.dumps(self.value).encode()


class ClientTests(unittest.TestCase):
    def setUp(self):
        self.client = WorldAnvilClient("app-secret", "user-secret")

    @patch("worldanvil_cli.client.urlopen")
    def test_articles_uses_post_query_and_json_body(self, mocked):
        mocked.return_value = Response({"entities": []})
        result = self.client.articles("world-123", limit=10, offset=5)
        request = mocked.call_args.args[0]
        self.assertEqual(result, {"entities": []})
        self.assertEqual(request.method, "POST")
        self.assertEqual(request.full_url, self.client.base_url + "/world/articles?id=world-123")
        self.assertEqual(json.loads(request.data), {"limit": 10, "offset": 5})
        self.assertEqual(request.headers["X-application-key"], "app-secret")

    @patch("worldanvil_cli.client.urlopen")
    def test_http_error_is_sanitized_and_structured(self, mocked):
        mocked.side_effect = HTTPError(
            "https://example.invalid", 401, "Unauthorized", {}, io.BytesIO(b'{"message":"bad token"}')
        )
        with self.assertRaises(WorldAnvilError) as caught:
            self.client.identity()
        self.assertEqual(caught.exception.status, 401)
        self.assertNotIn("user-secret", str(caught.exception))

    @patch("worldanvil_cli.client.urlopen")
    def test_categories_uses_collection_contract(self, mocked):
        mocked.return_value = Response({"entities": []})
        self.client.categories("world-123", limit=25, offset=50)
        request = mocked.call_args.args[0]
        self.assertEqual(request.method, "POST")
        self.assertEqual(request.full_url, self.client.base_url + "/world/categories?id=world-123")
        self.assertEqual(json.loads(request.data), {"limit": 25, "offset": 50})

    @patch("worldanvil_cli.client.urlopen")
    def test_category_create_update_delete_contracts(self, mocked):
        mocked.return_value = Response({"success": True})
        self.client.create_category({"world": "w", "title": "Places"})
        create = mocked.call_args.args[0]
        self.assertEqual(create.method, "PUT")
        self.assertEqual(create.full_url, self.client.base_url + "/category")
        self.assertEqual(json.loads(create.data), {"world": "w", "title": "Places"})

        self.client.update_category("c", {"title": "Locations"})
        update = mocked.call_args.args[0]
        self.assertEqual(update.method, "PATCH")
        self.assertEqual(update.full_url, self.client.base_url + "/category?id=c")

        self.client.delete_category("c")
        delete = mocked.call_args.args[0]
        self.assertEqual(delete.method, "DELETE")
        self.assertEqual(delete.full_url, self.client.base_url + "/category?id=c")

    @patch("worldanvil_cli.client.urlopen")
    def test_article_create_update_delete_contracts(self, mocked):
        mocked.return_value = Response({"success": True})
        document = {"world": "w", "title": "Harbor", "template": "location"}
        self.client.create_article(document)
        self.assertEqual(mocked.call_args.args[0].method, "PUT")
        self.client.update_article("a", {"title": "Port"})
        self.assertEqual(mocked.call_args.args[0].method, "PATCH")
        self.client.delete_article("a")
        self.assertEqual(mocked.call_args.args[0].method, "DELETE")

    @patch("worldanvil_cli.client.urlopen")
    def test_empty_response_returns_none(self, mocked):
        response = Response(None)
        response.read = lambda: b""
        mocked.return_value = response
        self.assertIsNone(self.client.identity())

    def test_missing_environment_names_without_values(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(WorldAnvilError) as caught:
                WorldAnvilClient.from_env()
        self.assertIn("WORLDANVIL_API_KEY", str(caught.exception))
        self.assertIn("WORLDANVIL_TOKEN", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
