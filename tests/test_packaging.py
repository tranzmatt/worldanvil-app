import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.build_plugins import digest, verify_archive

ROOT = Path(__file__).resolve().parent.parent


class PackagingTests(unittest.TestCase):
    def test_versions_match(self):
        portable = json.loads((ROOT / "plugin.json").read_text(encoding="utf-8"))
        codex = json.loads(
            (ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        claude = json.loads(
            (ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        desktop = json.loads(
            (ROOT / "claude-desktop" / "manifest.json").read_text(encoding="utf-8")
        )
        versions = {item["version"] for item in (portable, codex, claude, desktop)}
        self.assertEqual(versions, {"0.2.0"})

    def test_plugin_entrypoints_exist(self):
        portable_mcp = json.loads((ROOT / "mcp.json").read_text(encoding="utf-8"))
        claude_mcp = json.loads((ROOT / ".mcp.json").read_text(encoding="utf-8"))
        self.assertIn("worldanvil", portable_mcp["mcpServers"])
        self.assertIn("worldanvil", claude_mcp["mcpServers"])
        self.assertTrue((ROOT / "server" / "main.py").is_file())
        self.assertTrue((ROOT / "skills" / "worldanvil" / "SKILL.md").is_file())

    def test_desktop_credentials_are_sensitive(self):
        manifest = json.loads(
            (ROOT / "claude-desktop" / "manifest.json").read_text(encoding="utf-8")
        )
        self.assertTrue(manifest["user_config"]["application_key"]["sensitive"])
        self.assertTrue(manifest["user_config"]["auth_token"]["sensitive"])
        serialized = json.dumps(manifest)
        self.assertNotIn("x-auth-token\":", serialized)

    def test_archive_verification_and_digest(self):
        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / "sample.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("required.txt", "content")
            verify_archive(archive_path, {"required.txt"})
            self.assertEqual(len(digest(archive_path)), 64)

    def test_archive_verification_rejects_missing_members(self):
        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / "sample.zip"
            with zipfile.ZipFile(archive_path, "w"):
                pass
            with self.assertRaisesRegex(SystemExit, "missing required entries"):
                verify_archive(archive_path, {"required.txt"})


if __name__ == "__main__":
    unittest.main()
