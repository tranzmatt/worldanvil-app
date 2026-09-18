---
name: worldanvil
description: Inspect, organize, create, and update World Anvil worlds, categories, and articles through the local worldanvil CLI. Use for World Anvil content management, structural planning, and migrations; do not use for general Markdown editing without a World Anvil destination.
---

# World Anvil

Use the repository's `worldanvil` Python CLI as the execution boundary. Do not
reimplement HTTP calls when a semantic command exists.

## Workflow

1. Inspect before planning. Resolve user-friendly world, category, and article
   names to IDs with read-only commands.
2. Read [references/object-model.md](references/object-model.md) when choosing
   between categories, parent articles, and templates.
3. Read [references/content.md](references/content.md) when authoring or
   converting article bodies or links.
4. Express multi-object mutations as a JSON plan. Validate it with
   `worldanvil plan PLAN.json` and present that preview to the user.
5. Obtain explicit user confirmation immediately before any create, update, or
   delete. Apply only the confirmed plan with
   `worldanvil apply-plan PLAN.json --yes`.
6. Read changed resources back and verify the requested outcome.

For command and plan formats, read
[references/operations.md](references/operations.md).

## Invariants

- Credentials come only from `WORLDANVIL_API_KEY` and `WORLDANVIL_TOKEN`.
  Never print, persist, or put them in URLs, plans, or command arguments.
- Treat IDs as opaque strings. Never fabricate a World Anvil ID.
- Do not infer an ID from a non-unique title. Ask the user or provide the
  candidates when resolution is ambiguous.
- A validated plan is not authorization. Previewing is read-only; applying it
  mutates the account and requires confirmation.
- Category deletion can delete its contents. Describe that impact explicitly
  before seeking confirmation.
- Do not promise that a world can be deleted through Boromir. On 2026-09-18,
  `DELETE /world?id=...` returned HTTP 403 `access_denied` for an owned, empty,
  private world. Do not retry blindly or change visibility as a workaround.
  Report the failure and direct the user to World Anvil's web interface for
  manual deletion.
- Plan execution is ordered but not transactional. Stop on the first error,
  report completed operations, and do not attempt an automatic rollback.
- Preserve unknown fields when updating an existing resource unless the user
  explicitly asks to remove them.
- Prefer a small verified change over a large speculative migration.

The bundled OpenAPI endpoint files are discovery aids, not a complete schema:
some referenced schema files are absent. Confirm uncertain writable fields
against a read response or official documentation before mutation.
