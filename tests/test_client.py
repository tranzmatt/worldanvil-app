import io
import json
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


if __name__ == "__main__":
    unittest.main()

