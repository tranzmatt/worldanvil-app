# World Anvil CLI

A small, dependency-free Python client and command-line interface for World
Anvil's Boromir API. Credentials are read from environment variables and sent
only as request headers.

The repository is also a portable agent plugin. It bundles the World Anvil
skill with a local Model Context Protocol (MCP) server for ChatGPT/Codex,
Claude Code, and Claude Desktop.

## Build the plugins

After changing any Python source, skill, reference, manifest, or README content,
run the builder from the repository root:

```bash
python3 scripts/build_plugins.py
```

The command safely replaces the two artifacts for the current version, checks
that every manifest uses that same version, tests both ZIP containers, verifies
their required files, and prints a SHA-256 checksum for each result. It does not
contact World Anvil and does not include credentials.

It produces these ignored build artifacts:

- `dist/worldanvil-plugin-0.2.0.zip` for ChatGPT Desktop/Codex plugin import.
- `dist/worldanvil-0.2.0.mcpb` for Claude Desktop's custom Extensions screen.

The build is dependency-free. If the official `mcpb` packer is installed, the
script uses it; otherwise it creates the equivalent MCPB ZIP archive directly.

To rebuild after another source edit, run the same command again. You do not
need to delete `dist/` first.

Before distributing a release, also run:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
python3 scripts/build_plugins.py
```

If you change the release version, keep it identical in `pyproject.toml`,
`plugin.json`, `.codex-plugin/plugin.json`, `.claude-plugin/plugin.json`, and
`claude-desktop/manifest.json`. The builder stops with a version-mismatch
diagnostic instead of producing ambiguous files.

Optional: install the official MCPB validator/packer and rerun the same build
command. When `mcpb` is on `PATH`, the builder automatically uses `mcpb pack`;
otherwise its standard-library fallback remains sufficient for local builds.

### ChatGPT Desktop and Codex

Import `dist/worldanvil-plugin-0.2.0.zip` as a custom plugin. The local MCP
server makes the plugin desktop-only: it runs on your machine and uses the
`WORLDANVIL_API_KEY` and `WORLDANVIL_TOKEN` variables inherited by the
desktop application.

For development from this checkout, the repository root is itself a portable
plugin and can be loaded directly by a compatible Codex host.

### Claude Code

Test the repository plugin in place:

```bash
claude --plugin-dir .
```

The skill is available as `/worldanvil:worldanvil`. Claude Code starts the
same local MCP server from `.mcp.json` and inherits the two credential
environment variables.

### Claude Desktop

Open **Settings > Extensions > Advanced settings > Install Extension**, select
`dist/worldanvil-0.2.0.mcpb`, and enter the two credentials in the extension
configuration. Claude Desktop stores fields marked sensitive in operating
system secure storage; the bundle does not contain credentials.

The Claude Desktop MCPB supplies tools but not the prose skill used by coding
agents. Safety is therefore enforced both by tool descriptions and by the MCP
server: mutation tools reject calls unless `confirmed=true`.

## Install and configure

```bash
python -m venv .venv
.venv/bin/python -m pip install -e .

export WORLDANVIL_API_KEY='...'
export WORLDANVIL_TOKEN='...'
```

Do not put credentials in this repository or pass them on the command line.

Check local configuration without making a network request:

```bash
worldanvil doctor
```

Add `--live` for read-only identity and world-list checks.

## Read content

```bash
worldanvil identity
worldanvil worlds                 # discovers the user ID via /identity
worldanvil world WORLD_UUID
worldanvil categories WORLD_UUID
worldanvil articles WORLD_UUID
worldanvil article ARTICLE_UUID --granularity 2
```

The API's collection calls are paginated:

```bash
worldanvil articles WORLD_UUID --limit 50 --offset 50
```

## Create and update an article

Keep request bodies in JSON files so shell quoting cannot corrupt content:

```json
{
  "title": "The Glass Harbor",
  "world": {"id": "WORLD_UUID"},
  "templateType": "location",
  "content": "Harbor description"
}
```

```bash
worldanvil create-article --file new-article.json --yes
worldanvil update-article ARTICLE_UUID --file article-changes.json --yes
worldanvil delete-article ARTICLE_UUID --yes
```

All named mutations require explicit confirmation. For agent-driven or
multi-object work, write and review a mutation plan first:

```bash
worldanvil plan plan.json
worldanvil apply-plan plan.json --yes
```

The repository includes an agent skill at `skills/worldanvil/`. It documents
the object model, content conversion rules, discovery workflow, and safe plan
execution contract.

For a new interconnected world, use a blueprint. It creates the world,
categories, and article skeletons first, then resolves symbolic links and
updates content:

```bash
worldanvil blueprint examples/lantern-sea.json
worldanvil apply-blueprint examples/lantern-sea.json --yes
```

Blueprint results include a UUID manifest. Preserve it beside the source
blueprint so later edits address the created resources instead of duplicating
them.

## Known limitation: deleting worlds

World creation, readback, and updates work through the API. In a live test on
2026-09-18, however, the documented world-delete request returned HTTP 403
`access_denied` for an owned, empty, private world. The client retains the
operation so it can report the server response, but automation must not assume
it can clean up a world it creates. Do not retry the delete blindly or change
world visibility as a workaround; use World Anvil's
[web-interface deletion procedure](https://www.worldanvil.com/learn/interface/delete-world)
when API deletion is denied.

World Anvil's exact writable article fields depend on the article template;
use the supplied `openapi.yml` and its `parts/` schemas when composing files.

## Any Boromir endpoint

The generic command exposes resources not yet covered by convenience commands:

```bash
worldanvil request GET /category --param id=CATEGORY_UUID --param granularity=1
worldanvil request POST /world/categories --param id=WORLD_UUID --file page.json
worldanvil request PATCH /category --param id=CATEGORY_UUID --file changes.json --yes
```

Generic `PUT`, `PATCH`, and `DELETE` requests require `--yes`. The CLI prints
formatted JSON to stdout and diagnostics to stderr, making it suitable for
scripts and `jq` pipelines.

## Python API

```python
from worldanvil_cli import WorldAnvilClient

client = WorldAnvilClient.from_env()
identity = client.identity()
articles = client.articles("WORLD_UUID", limit=50)
```

The client raises `WorldAnvilError` for configuration, network, HTTP, and API
errors. It never includes credentials in URLs or error messages.

## MCP tools

Run the server directly with:

```bash
worldanvil-mcp
```

It communicates over stdio and exposes read-only discovery, offline plan and
blueprint previews, and confirmation-gated plan and blueprint application.
Never write logs or other text to its stdout because stdout is reserved for
MCP JSON-RPC messages.

## Testing

The default suite is offline and never contacts or changes World Anvil:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

Live read-only integration tests are opt-in:

```bash
WORLDANVIL_RUN_LIVE_TESTS=1 \
PYTHONPATH=src python -m unittest tests.test_live_api.LiveReadOnlyTests -v
```

Set `WORLDANVIL_TEST_WORLD_ID` to also test category and article listings for
one world.

The category lifecycle test creates, reads, renames, and deletes one uniquely
named empty category. The mutation module also has separate article and
plan-execution lifecycle classes. They are gated so an ordinary test run can
never mutate the account:

```bash
WORLDANVIL_TEST_WORLD_ID='...' \
WORLDANVIL_RUN_LIVE_MUTATION_TESTS=1 \
PYTHONPATH=src python -m unittest \
  tests.test_live_api.LiveCategoryLifecycleTests -v
```

Running that command is confirmation to perform the described temporary
create/update/delete lifecycle. Use only a world where this test is acceptable.
There is deliberately no automated world lifecycle test: the current API can
create worlds but denied deletion during live validation, which would leave
test worlds behind.
See `tests/TEST_PLAN.md` for the coverage matrix and known gaps.
