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
  "world": "WORLD_UUID",
  "template": "location",
  "content": "Harbor description"
}
```

```bash
worldanvil create-article --file new-article.json
worldanvil update-article ARTICLE_UUID --file article-changes.json
worldanvil delete-article ARTICLE_UUID --yes
```

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
