# World Anvil CLI

A small, dependency-free Python client and command-line interface for World
Anvil's Boromir API. Credentials are read from environment variables and sent
only as request headers.

## Install and configure

```bash
python -m venv .venv
.venv/bin/python -m pip install -e .

export WORLDANVIL_API_KEY='...'
export WORLDANVIL_TOKEN='...'
```

Do not put credentials in this repository or pass them on the command line.

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
