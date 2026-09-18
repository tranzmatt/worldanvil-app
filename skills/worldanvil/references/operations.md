# Agent operations

Run from the repository after `python -m pip install -e .`, or prefix commands
with `PYTHONPATH=src python -m worldanvil_cli`.

When installed as a plugin, prefer the equivalent `worldanvil_*` MCP tools.
They return the same JSON-oriented resource shapes. Mutation tools require a
`confirmed=true` argument in addition to the workflow's immediate explicit
user confirmation.

## Read-only discovery

```bash
worldanvil identity
worldanvil worlds
worldanvil categories WORLD_ID
worldanvil category CATEGORY_ID --granularity 2
worldanvil articles WORLD_ID
worldanvil article ARTICLE_ID --granularity 2
```

Use `--limit` and `--offset` on collection commands. Paginate until a page
has fewer results than the requested limit when a complete inventory is required.

## Mutation plan

```json
{
  "operations": [
    {
      "action": "category.create",
      "note": "Create the requested top-level navigation category",
      "data": {
        "world": {"id": "WORLD_ID"},
        "title": "Places"
      }
    },
    {
      "action": "article.update",
      "id": "ARTICLE_ID",
      "data": {
        "title": "Revised title"
      }
    }
  ]
}
```

Supported actions:

- `world.create`, `world.update`, `world.delete`
- `category.create`, `category.update`, `category.delete`
- `article.create`, `article.update`, `article.delete`

`world.delete` is represented because Boromir documents the endpoint, but it
must not be treated as a reliable cleanup operation. A live test on 2026-09-18
returned HTTP 403 `access_denied` for an owned, empty, private world. If this
occurs, stop: do not retry automatically, make the world public, or create a
replacement test world. Tell the user that the world still exists and must be
deleted manually in World Anvil's web interface. Consequently, automated live
tests must not create worlds whose cleanup depends on this endpoint.

Create operations require complete World Anvil payloads. World creation
requires at least `title`. Category creation
requires at least `world` and `title`; article creation requires at least
`world`, `title`, and `templateType`. For both resources, `world` is a reference
object such as `{"id": "WORLD_ID"}`, not a bare UUID. Update operations require `id` and contain
only intended changes in `data`. Delete operations require `id` and no data.

Validate and preview without mutation:

```bash
worldanvil plan plan.json
```

After the user explicitly confirms that exact preview:

```bash
worldanvil apply-plan plan.json --yes
```

Operations execute in array order and stop at the first error. The initial
plan format intentionally does not interpolate IDs returned by earlier
operations; use separate confirmed phases when a later operation needs a newly
created ID.

## World blueprints

Use a blueprint when later content must refer to resources created earlier.
Symbolic tokens are resolved after article skeletons have returned UUIDs:

- `{{article:key}}` or `{{article:key|display label}}`
- `{{category:key}}` or `{{category:key|display label}}`

Preview with `worldanvil blueprint FILE.json`. After confirmation, apply with
`worldanvil apply-blueprint FILE.json --yes`. Execution creates the world,
categories, and article skeletons before updating linked content and homepage
fields. The result contains a UUID manifest. If execution fails, preserve the
manifest reported in the error; do not blindly retry and create duplicates.
