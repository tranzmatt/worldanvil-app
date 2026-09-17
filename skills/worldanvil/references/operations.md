# Agent operations

Run from the repository after `python -m pip install -e .`, or prefix commands
with `PYTHONPATH=src python -m worldanvil_cli`.

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
        "world": "WORLD_ID",
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

- `category.create`, `category.update`, `category.delete`
- `article.create`, `article.update`, `article.delete`

Create operations require complete World Anvil payloads. Category creation
requires at least `world` and `title`; article creation requires at least
`world`, `title`, and `template`. Update operations require `id` and contain
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
