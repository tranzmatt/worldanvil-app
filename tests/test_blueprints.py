import unittest
from unittest.mock import Mock, call

from worldanvil_cli.blueprints import (
    BlueprintError, apply_blueprint, preview_blueprint, validate_blueprint
)


def sample():
    return {
        "world": {"title": "The Lantern Sea", "state": "private"},
        "categories": [{"key": "places", "title": "Places"}],
        "articles": [
            {
                "key": "harbor",
                "title": "Glasswake Harbor",
                "templateType": "settlement",
                "category": "places",
                "content": "Home of {{article:keeper|the Keeper}}.",
            },
            {
                "key": "keeper",
                "title": "Mara Vey",
                "templateType": "person",
                "content": "She watches {{article:harbor}}.",
            },
        ],
        "homepage": {"homepageContent1": "Begin at {{article:harbor}}."},
    }


class BlueprintTests(unittest.TestCase):
    def test_preview_summarizes_without_credentials(self):
        preview = preview_blueprint(sample())
        self.assertEqual(preview["categoryCount"], 1)
        self.assertEqual(preview["articleCount"], 2)

    def test_rejects_unknown_category_key(self):
        value = sample()
        value["articles"][0]["category"] = "missing"
        with self.assertRaisesRegex(BlueprintError, "unknown key"):
            validate_blueprint(value)

    def test_apply_creates_skeletons_then_renders_links(self):
        client = Mock()
        client.create_world.return_value = {"id": "world-id"}
        client.create_category.return_value = {"id": "category-id"}
        client.create_article.side_effect = [{"id": "harbor-id"}, {"id": "keeper-id"}]

        result = apply_blueprint(client, sample())

        self.assertEqual(result["manifest"]["world"], "world-id")
        client.create_category.assert_called_once_with({
            "title": "Places", "world": {"id": "world-id"}
        })
        self.assertEqual(client.create_article.call_count, 2)
        client.update_article.assert_has_calls([
            call("harbor-id", {"content": "Home of @[the Keeper](person:keeper-id)."}),
            call("keeper-id", {"content": "She watches @[Glasswake Harbor](settlement:harbor-id)."}),
        ])
        client.update_world.assert_called_once_with(
            "world-id",
            {"homepageContent1": "Begin at @[Glasswake Harbor](settlement:harbor-id)."},
        )


if __name__ == "__main__":
    unittest.main()
