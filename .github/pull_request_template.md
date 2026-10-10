<!--
The PR title becomes the squash commit, the changelog line and the version bump:
  fix: / perf:                         -> patch release
  feat:                                -> minor release
  feat!: or "BREAKING CHANGE:" in body -> major release (minor before 1.0)
  docs: refactor: test: ci: chore:     -> no release
Do not edit the version or CHANGELOG.md.
-->

## What and why

## How it was verified

## Checklist

- [ ] The title is a Conventional Commit that picks the right release.
- [ ] `uv run pytest` passes.
- [ ] README.md / docs/design.md are updated if behaviour or settings changed.
