"""Plugin entry point for the bundled World Anvil MCP server."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "src"
if SOURCE.is_dir():
    sys.path.insert(0, str(SOURCE))
else:
    # Claude Desktop bundles place the package beside this launcher.
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from worldanvil_cli.mcp import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
