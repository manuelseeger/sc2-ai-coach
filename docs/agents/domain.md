# Domain docs

This repo is configured as a single-context project.

## Layout

- Primary domain context lives at `CONTEXT.md` in the repository root.
- Architectural decision records live under `docs/adr/`.

## Consumer rules

- Skills that need project domain language should read `CONTEXT.md` first when it exists.
- Skills that need architectural history or decision context should read files under `docs/adr/`.
- If `CONTEXT.md` or `docs/adr/` do not exist yet, treat that as "no domain docs are present" rather than guessing or inventing missing documents.
- Do not look for `CONTEXT-MAP.md` unless this repo is later migrated to a multi-context layout.

## Future migration

If this repo becomes a multi-context project later, add a root `CONTEXT-MAP.md` and update this file to describe the per-context locations.