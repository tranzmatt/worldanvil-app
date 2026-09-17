# World Anvil object model

## Core hierarchy

- A **world** is the top-level container and supplies the `world` ID required
  when creating categories and articles.
- A **category** organizes world content. Categories are the closest analogue
  to folders, but do not assume every filesystem behavior maps to them.
- An **article** is a typed content entity. Its `template` determines the
  available template-specific fields; generic `article` is the conservative
  choice only when the user has not requested a more specific type.
- Parent-article relationships and category placement are distinct. Use a
  category for navigation/organization and a parent article only for a genuine
  content relationship.

Other API resources include images, maps, timelines, histories, notebooks,
variables, blocks, secrets, manuscripts, and subscriber groups. Inspect their
contracts before use; the current semantic plan layer supports only categories
and articles.

## Live reference shapes

Collection responses use an object containing `success` and `entities`.
Reference objects commonly contain `id`, `title`, `slug`, `url`, `state`,
`isDraft`, `isWip`, `tags`, and relationship identifiers. Field availability
depends on resource type and granularity.

## Structural decisions

- Folder tree from another system: normally map folders to categories.
- One document: normally map to one article.
- Document type encoded in metadata: map to an article template only when the
  mapping is explicit and valid.
- Cross-document reference: resolve both resources first, then render a World
  Anvil link using the target ID.
- Navigation page with substantive prose: it may warrant both a category and
  an article; do not collapse them without user intent.
