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

- Create, read, and update a disposable world.
- Populate it before considering world deletion coverage.
- World deletion remains a separately confirmed destructive test because it
  recursively deletes all contained resources.

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
