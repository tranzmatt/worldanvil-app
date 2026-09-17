# Article content and conversion

World Anvil API payloads are JSON, while article bodies contain World Anvil's
supported presentation markup. Transport format and content format are
separate concerns.

When converting Markdown or another source:

1. Preserve the source text until a conversion rule is known.
2. Build a source-path-to-World-Anvil-ID manifest before rewriting links.
3. Convert headings, emphasis, lists, tables, callouts, and embeds explicitly;
   do not assume arbitrary Markdown renders identically.
4. Resolve wiki links and relative links after destination articles exist.
5. Treat plugin syntax, queries, formulas, and unsupported embeds as migration
   warnings rather than silently dropping them.
6. Handle attachments separately. Do not claim an upload succeeded unless the
   target resource can be read back.

For a collection import, use two passes: create the category/article skeleton
and record IDs, then update bodies and relationships with rewritten links.
Keep a persistent manifest to make retries idempotent and avoid duplicates.
