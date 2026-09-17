"""Opt-in integration tests. The default suite never contacts World Anvil."""

import os
import unittest
import uuid

from worldanvil_cli import WorldAnvilClient, WorldAnvilError


RUN_READS = os.environ.get("WORLDANVIL_RUN_LIVE_TESTS") == "1"
RUN_WRITES = os.environ.get("WORLDANVIL_RUN_LIVE_MUTATION_TESTS") == "1"
TEST_WORLD_ID = os.environ.get("WORLDANVIL_TEST_WORLD_ID")
HAS_CREDENTIALS = bool(
    os.environ.get("WORLDANVIL_API_KEY") and os.environ.get("WORLDANVIL_TOKEN")
)


def _resource_id(value):
    candidates = [value]
    if isinstance(value, dict):
        candidates.extend(value.get(key) for key in ("entity", "category", "data"))
    for candidate in candidates:
        if isinstance(candidate, dict) and candidate.get("id"):
            return str(candidate["id"])
    keys = sorted(value) if isinstance(value, dict) else []
    raise AssertionError(f"Response did not contain a resource id; keys={keys}")


@unittest.skipUnless(RUN_READS and HAS_CREDENTIALS, "live read tests are opt-in")
class LiveReadOnlyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = WorldAnvilClient.from_env()

    def test_identity_and_world_listing(self):
        identity = self.client.identity()
        self.assertTrue(identity.get("success"))
        self.assertTrue(identity.get("id"))
        worlds = self.client.worlds(identity["id"], limit=1)
        self.assertTrue(worlds.get("success"))
        self.assertIsInstance(worlds.get("entities"), list)

    @unittest.skipUnless(TEST_WORLD_ID, "set WORLDANVIL_TEST_WORLD_ID")
    def test_world_collections(self):
        categories = self.client.categories(TEST_WORLD_ID, limit=1)
        articles = self.client.articles(TEST_WORLD_ID, limit=1)
        self.assertTrue(categories.get("success"))
        self.assertIsInstance(categories.get("entities"), list)
        self.assertTrue(articles.get("success"))
        self.assertIsInstance(articles.get("entities"), list)


@unittest.skipUnless(
    RUN_WRITES and HAS_CREDENTIALS and TEST_WORLD_ID,
    "live mutation tests require explicit opt-in, credentials, and a test world",
)
class LiveCategoryLifecycleTests(unittest.TestCase):
    def test_create_read_update_read_delete(self):
        client = WorldAnvilClient.from_env()
        original_title = f"API Integration Test {uuid.uuid4()}"
        updated_title = original_title + " Updated"
        category_id = None
        try:
            created = client.create_category(
                {"world": TEST_WORLD_ID, "title": original_title}
            )
            category_id = _resource_id(created)

            read = client.category(category_id, granularity=1)
            self.assertEqual(read.get("id"), category_id)
            self.assertEqual(read.get("title"), original_title)

            client.update_category(category_id, {"title": updated_title})
            reread = client.category(category_id, granularity=1)
            self.assertEqual(reread.get("title"), updated_title)
        finally:
            if category_id:
                client.delete_category(category_id)

        with self.assertRaises(WorldAnvilError) as caught:
            client.category(category_id, granularity=1)
        self.assertEqual(caught.exception.status, 404)


if __name__ == "__main__":
    unittest.main()
