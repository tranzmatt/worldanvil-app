"""Opt-in integration tests. The default suite never contacts World Anvil.

World lifecycle mutation is deliberately absent: live world deletion returned
HTTP 403, so an automated create/delete test could leave orphaned worlds.
"""

import os
import unittest
import uuid

from worldanvil_cli import WorldAnvilClient, WorldAnvilError
from worldanvil_cli.plans import apply_plan, parse_plan


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
        world = self.client.world(TEST_WORLD_ID, granularity=1)
        self.assertEqual(world.get("id"), TEST_WORLD_ID)
        categories = self.client.categories(TEST_WORLD_ID, limit=1)
        articles = self.client.articles(TEST_WORLD_ID, limit=1)
        self.assertTrue(categories.get("success"))
        self.assertIsInstance(categories.get("entities"), list)
        self.assertTrue(articles.get("success"))
        self.assertIsInstance(articles.get("entities"), list)
        if categories["entities"]:
            category = self.client.category(categories["entities"][0]["id"], granularity=1)
            self.assertEqual(category.get("id"), categories["entities"][0]["id"])
        if articles["entities"]:
            article = self.client.article(articles["entities"][0]["id"], granularity=1)
            self.assertEqual(article.get("id"), articles["entities"][0]["id"])


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
                {"world": {"id": TEST_WORLD_ID}, "title": original_title}
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


@unittest.skipUnless(
    RUN_WRITES and HAS_CREDENTIALS and TEST_WORLD_ID,
    "live mutation tests require explicit opt-in, credentials, and a test world",
)
class LiveArticleLifecycleTests(unittest.TestCase):
    def test_create_read_update_read_delete(self):
        client = WorldAnvilClient.from_env()
        original_title = f"API Integration Article {uuid.uuid4()}"
        updated_title = original_title + " Updated"
        article_id = None
        try:
            created = client.create_article({
                "world": {"id": TEST_WORLD_ID},
                "title": original_title,
                "templateType": "article",
            })
            article_id = _resource_id(created)

            read = client.article(article_id, granularity=1)
            self.assertEqual(read.get("id"), article_id)
            self.assertEqual(read.get("title"), original_title)

            client.update_article(article_id, {"title": updated_title})
            reread = client.article(article_id, granularity=1)
            self.assertEqual(reread.get("title"), updated_title)
        finally:
            if article_id:
                client.delete_article(article_id)

        with self.assertRaises(WorldAnvilError) as caught:
            client.article(article_id, granularity=1)
        self.assertEqual(caught.exception.status, 404)


@unittest.skipUnless(
    RUN_WRITES and HAS_CREDENTIALS and TEST_WORLD_ID,
    "live mutation tests require explicit opt-in, credentials, and a test world",
)
class LivePlanLifecycleTests(unittest.TestCase):
    def test_category_lifecycle_through_plans(self):
        client = WorldAnvilClient.from_env()
        original_title = f"API Plan Test {uuid.uuid4()}"
        updated_title = original_title + " Updated"
        category_id = None
        try:
            create = parse_plan({"operations": [{
                "action": "category.create",
                "data": {
                    "world": {"id": TEST_WORLD_ID},
                    "title": original_title,
                },
            }]})
            created = apply_plan(client, create)
            category_id = _resource_id(created["results"][0]["result"])

            update = parse_plan({"operations": [{
                "action": "category.update",
                "id": category_id,
                "data": {"title": updated_title},
            }]})
            applied = apply_plan(client, update)
            self.assertEqual(applied["applied"], 1)
            self.assertEqual(
                client.category(category_id, granularity=1).get("title"),
                updated_title,
            )

            delete = parse_plan({"operations": [{
                "action": "category.delete",
                "id": category_id,
            }]})
            applied = apply_plan(client, delete)
            self.assertEqual(applied["applied"], 1)
            category_id = None
        finally:
            if category_id:
                client.delete_category(category_id)


if __name__ == "__main__":
    unittest.main()
