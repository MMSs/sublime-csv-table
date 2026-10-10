# AGENTS.md

CSV Table is a Sublime Text 4 plugin with one command, **Format CSV Table**, that rewrites a CSV buffer as an aligned table and colours it.

## Module map

- `csv_format.py`: quote-aware parse, delimiter detection, alignment. Pure Python 3.8, no `sublime` import. Rules in `docs/design.md`.
- `csv_table.py`: `format_csv_table` command, delimiter quick panel, syntax switch, header rule, row stripes (phantoms + a generated scheme in `Packages/User/CSV Table/`).
- `csv_scheme.py`: column scopes (shared with the syntax generator) and the rules merged into the user's colour scheme (stripes, plain columns). Pure, no `sublime` import.
- `scripts/build_syntaxes.py`: writes the four `CSV*.sublime-syntax` files. Never edit those by hand.
- `CSV Table.sublime-settings`, `Default.sublime-commands`, `Main.sublime-menu`: package settings, palette entries, Preferences menu entry.
- `messages.json`, `messages/`: text Package Control shows after install.
- `scripts/release/bump.mjs`: version bump + changelog for the release workflow.

## Commands

- `uv run pytest`: all tests (CI also runs Python 3.8).
- `node --test scripts/release/bump.test.mjs`: release script tests.
- `uv run python scripts/build_syntaxes.py`: regenerate syntaxes after editing the script.

## Rules

- No third-party runtime packages. Sublime runs the plugin on its bundled Python 3.8 (`.python-version`). No syntax newer than 3.8.
- Keep `csv_format.py` and `csv_scheme.py` free of `sublime` imports and import-time side effects; Sublime loads every top-level `.py` as a plugin.
- The installed folder must be named `CSV Table`: syntax paths are `Packages/CSV Table/...`.
- Only write under `Packages/User/CSV Table/`. Nothing else on disk, no network.
- Keep `README.md` and `docs/design.md` in sync with behaviour and settings.
- New top-level files that users don't need go into `.gitattributes` as `export-ignore`, so Package Control doesn't ship them.
- `main` is protected. Branch, open a PR with `gh pr create`, and let the maintainer merge. The PR title is a Conventional Commit and decides the release (see CONTRIBUTING.md). Never edit the version or `CHANGELOG.md`.

## Sublime pitfalls

- Sublime reloads `csv_table.py` on save but keeps the old `csv_format` and `csv_scheme` in `sys.modules`. Pop them and touch `csv_table.py`, or restart Sublime.
- `csv_table.py` adds its own directory to `sys.path` because Sublime imports it as `CSV Table.csv_table`.

## Testing live

Symlink the checkout into `Packages/CSV Table` (CONTRIBUTING.md). To inspect state, drop a temporary `zz_*.py` `WindowCommand` into `Packages/User/`, run it with `subl --command <name>`, have it log what you need, then delete it. Check visual changes by looking at the window, not only at tests.

## Releasing

See `.claude/skills/release/SKILL.md` and `docs/RELEASING.md`.
