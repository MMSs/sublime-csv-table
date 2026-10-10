---
name: release
description: Use when shipping a change, choosing a version, writing a PR title, or when a release workflow run failed in this repo.
---

# Releasing CSV Table

Releases come from merged PR titles. Full details: `docs/RELEASING.md`.

- **Choosing a version = choosing the PR title.** `fix:`/`perf:` → patch, `feat:` → minor, `feat!:` or `BREAKING CHANGE:` in the body → major (minor before 1.0). `docs:` `refactor:` `test:` `ci:` `chore:` → no release.
- **Never push to `main`** and never edit the version in `pyproject.toml` or `CHANGELOG.md`. Branch, commit, `gh pr create`; the maintainer merges.
- **Before asking for a merge:** `uv run pytest` and `node --test scripts/release/bump.test.mjs` pass, `gh pr checks` is green, and for `feat:`/`fix:` the change was tried live in Sublime.
- **Failed release run:** `gh run view <id> --log-failed`, explain the cause, propose the fix as a PR.
- **Ask the maintainer first** before creating a tag or GitHub release by hand, or touching the Package Control channel entry.
