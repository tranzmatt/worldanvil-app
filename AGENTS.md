# World Anvil project instructions

For requests that inspect, organize, create, update, delete, or migrate World
Anvil content, read and follow `skills/worldanvil/SKILL.md` before acting.

Use the local Python package for API access instead of constructing ad hoc curl
commands when it provides the required operation. Keep credentials in
`WORLDANVIL_API_KEY` and `WORLDANVIL_TOKEN`; never print or persist them.

Read-only discovery is permitted when relevant. Before any live create, update,
or delete, show the user the exact mutation plan and obtain explicit
confirmation. Validation or earlier general approval does not replace this
final confirmation.
