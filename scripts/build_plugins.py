#!/usr/bin/env python3
"""Build portable ChatGPT/Codex and Claude Desktop plugin archives."""

from __future__ import annotations

import json
import hashlib
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
VERSION = json.loads((ROOT / "plugin.json").read_text(encoding="utf-8"))["version"]


def validate_versions() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    project = pyproject.split("[project]", 1)[-1].split("[", 1)[0]
    match = re.search(r'^version\s*=\s*"([^"]+)"', project, re.MULTILINE)
    if not match:
        raise SystemExit("Could not read project.version from pyproject.toml")
    manifests = {
        "pyproject.toml": match.group(1),
        "plugin.json": VERSION,
        ".codex-plugin/plugin.json": json.loads(
            (ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )["version"],
        ".claude-plugin/plugin.json": json.loads(
            (ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
        )["version"],
        "claude-desktop/manifest.json": json.loads(
            (ROOT / "claude-desktop" / "manifest.json").read_text(encoding="utf-8")
        )["version"],
    }
    mismatches = {name: value for name, value in manifests.items() if value != VERSION}
    if mismatches:
        details = ", ".join(f"{name}={value}" for name, value in mismatches.items())
        raise SystemExit(f"Version mismatch; plugin.json={VERSION}, {details}")


def _copy_tree(source: Path, destination: Path) -> None:
    shutil.copytree(
        source,
        destination,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )


def build_openai() -> Path:
    output = DIST / f"worldanvil-plugin-{VERSION}.zip"
    output.unlink(missing_ok=True)
    with tempfile.TemporaryDirectory() as temporary:
        stage = Path(temporary) / "worldanvil"
        stage.mkdir()
        for name in ("plugin.json", "mcp.json", ".mcp.json", "README.md"):
            shutil.copy2(ROOT / name, stage / name)
        _copy_tree(ROOT / ".codex-plugin", stage / ".codex-plugin")
        _copy_tree(ROOT / "skills", stage / "skills")
        _copy_tree(ROOT / "src", stage / "src")
        _copy_tree(ROOT / "server", stage / "server")
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(stage.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(stage.parent))
    return output


def build_claude_desktop() -> Path:
    output = DIST / f"worldanvil-{VERSION}.mcpb"
    output.unlink(missing_ok=True)
    with tempfile.TemporaryDirectory() as temporary:
        stage = Path(temporary) / "worldanvil"
        server = stage / "server"
        server.mkdir(parents=True)
        shutil.copy2(ROOT / "claude-desktop" / "manifest.json", stage / "manifest.json")
        shutil.copy2(ROOT / "server" / "main.py", server / "main.py")
        _copy_tree(ROOT / "src" / "worldanvil_cli", server / "worldanvil_cli")
        tool = shutil.which("mcpb")
        if tool:
            subprocess.run([tool, "pack", str(stage), str(output)], check=True)
        else:
            with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
                for path in sorted(stage.rglob("*")):
                    if path.is_file():
                        archive.write(path, path.relative_to(stage))
    return output


def verify_archive(path: Path, required: set[str]) -> None:
    with zipfile.ZipFile(path) as archive:
        bad = archive.testzip()
        if bad:
            raise SystemExit(f"{path}: corrupt archive member: {bad}")
        names = set(archive.namelist())
    missing = required - names
    if missing:
        raise SystemExit(f"{path}: missing required entries: {sorted(missing)}")


def digest(path: Path) -> str:
    checksum = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(chunk)
    return checksum.hexdigest()


def main() -> int:
    validate_versions()
    DIST.mkdir(exist_ok=True)
    openai = build_openai()
    desktop = build_claude_desktop()
    verify_archive(openai, {
        "worldanvil/plugin.json",
        "worldanvil/mcp.json",
        "worldanvil/server/main.py",
        "worldanvil/skills/worldanvil/SKILL.md",
        "worldanvil/src/worldanvil_cli/mcp.py",
    })
    verify_archive(desktop, {
        "manifest.json",
        "server/main.py",
        "server/worldanvil_cli/mcp.py",
    })
    outputs = [openai, desktop]
    for output in outputs:
        print(f"{output}  sha256={digest(output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
