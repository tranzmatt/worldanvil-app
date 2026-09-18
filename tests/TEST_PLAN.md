# World Anvil test plan

The suite validates the local client and the workflows an automated operator
needs to inspect and safely change World Anvil. Live tests target only the
world explicitly supplied in `WORLDANVIL_TEST_WORLD_ID`.

## Safety tiers

| Tier | Network | Mutates World Anvil | Gate |
|---|---:|---:|---|
| Offline unit and CLI | No | No | None |
| Live read-only | Yes | No | `WORLDANVIL_RUN_LIVE_TESTS=1` |
| Live lifecycle | Yes | Yes, temporary resources | `WORLDANVIL_RUN_LIVE_MUTATION_TESTS=1` and test world ID |

The default discovery run must skip every live test. Live resources use unique
UUID-suffixed titles. Each lifecycle owns only the resource it creates and
deletes it in `finally` if an intermediate assertion fails.

## Coverage

### Authentication and transport

- Missing credential diagnostics name variables without exposing values.
- Required authentication and JSON headers are constructed.
- JSON, empty, and structured HTTP error responses are handled.
- Query parameters and JSON request bodies reach the expected endpoints.
- Offline doctor output reports credential presence without exposing values.

### Agent and plugin packaging

- MCP initialization and tool discovery return valid JSON-RPC results.
- Offline plan preview works through MCP without credentials.
- MCP mutations refuse execution until `confirmed=true`.
- ChatGPT/Codex, Claude Code, and Claude Desktop manifests share one version.
- Plugin entry points and sensitive credential declarations are present.

### Discovery

- Identity resolves the authenticated user.
- Owned worlds can be listed.
- A selected world can be read.
- Category and article collections can be listed.
- Existing category and article references can be read at higher granularity.
- Pagination parameters are serialized correctly.

### Mutation safety

- Named CLI mutations refuse execution without `--yes`.
- Plan validation runs without credentials or network access.
- Empty, malformed, ambiguous, and unsupported plans are rejected.
- Create operations require nested world references.
- Article creation requires Boromir's `templateType` field.
- Delete operations are counted as destructive in previews.
- Failed plans report the completed prefix and stop.

### Live category lifecycle

- Create a uniquely named empty category.
- Read and verify its ID and title.
- Rename and read back.
- Delete and verify HTTP 404.

### World lifecycle

- Live creation, readback, and update have been verified.
- Live deletion was tested on 2026-09-18 against an owned, empty, private
  world and returned HTTP 403 `access_denied`; the world remained intact.
- World creation/deletion is intentionally excluded from the automated live
  suite. A failed delete leaves an orphaned world, so tests must not create a
  world whose cleanup depends on the API endpoint.
- The retained test world `Mayfly Reach — Deletion Test`
  (`4af1fa19-2efa-4ad1-b2f8-8ce1edb56842`) requires manual deletion through
  the World Anvil web interface.

### Live article lifecycle

- Create a uniquely named generic article.
- Read and verify its ID and title.
- Rename and read back.
- Delete and verify HTTP 404.

### Live plan lifecycle

- Create a category through `apply_plan`.
- Update it through a second validated plan.
- Read back and verify.
- Delete it through a final plan.

## Not yet covered

- Name-to-ID resolution and ambiguous-title handling against live data.
- Automatic traversal beyond one collection page.
- Parent category and parent article relationships.
- Category placement for articles.
- World Anvil content markup and internal link rendering.
- Images, maps, timelines, notebooks, manuscripts, blocks, variables, secrets,
  subscriber groups, and other API resources.
- Rate limiting, retry/backoff, interrupted imports, and persistent manifests.
- Multi-step plans that refer to IDs created earlier in the same plan.

## Known live limitation

The client and plan system preserve `world.delete` so the documented request
can be issued and its response reported. Current live behavior does not permit
the operation with the tested owner credentials. This is not considered a
passing lifecycle, and tests must not interpret the presence of the client
method as proof that world deletion is available.
