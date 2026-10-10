# Releasing

Releases are automatic. Nobody tags, bumps versions or edits `CHANGELOG.md` by hand.

## How a release happens

1. A pull request is squash-merged into `main`. Its title is the squash commit.
2. `.github/workflows/release.yml` runs `scripts/release/bump.mjs` with the title and body:
   `fix:`/`perf:` → patch, `feat:` → minor, `feat!:` or `BREAKING CHANGE:` → major (minor before 1.0). Other types release nothing.
3. On a bump it updates `version` in `pyproject.toml`, prepends the entry to `CHANGELOG.md`, commits `release vX.Y.Z` to `main`, tags `vX.Y.Z` and creates the GitHub release.
4. Package Control polls the repository and offers the new tag to users, usually within a few hours. Its archive comes from the tag, minus everything marked `export-ignore` in `.gitattributes`.

## How `main` is protected

A repository ruleset ("protect main") blocks deletion and force pushes, requires a pull request with squash merge, and requires the CI `check (…)` jobs and `pr-title` to pass.

The only bypass is a write deploy key, "release workflow". Its private half is the `RELEASE_DEPLOY_KEY` Actions secret. The release job checks out `main` with it, so it can push the version commit and tag. The job never checks out PR code.

### Rotating the deploy key

```sh
R=MMSs/sublime-csv-table
d=$(mktemp -d)
ssh-keygen -t ed25519 -N "" -C "release workflow" -f "$d/key"
gh repo deploy-key list -R "$R"            # note the old key id
gh repo deploy-key add "$d/key.pub" -R "$R" --allow-write --title "release workflow (pushes version commits and tags)"
gh secret set RELEASE_DEPLOY_KEY -R "$R" < "$d/key"
gh repo deploy-key delete <old id> -R "$R"
rm -rf "$d"
```

## Before merging a `feat:` or `fix:`

Check out the branch, link it into `Packages/CSV Table`, restart Sublime, and format a few files: comma, semicolon, tab, a quoted multi-line cell, and a non-CSV buffer.

## When a release run fails

Read the log with `gh run view <id> --log-failed`. Fix the cause in a new pull request; do not push to `main`.

If the version commit landed but the tag or GitHub release is missing, recreate them from that commit:

```sh
git tag vX.Y.Z <version commit> && git push origin vX.Y.Z
gh release create vX.Y.Z --title vX.Y.Z --notes "<line from CHANGELOG.md>"
```

## Package Control listing

Done once, after the first release works. Open a pull request to [sublimehq/package_control_channel](https://github.com/sublimehq/package_control_channel) adding this entry, in alphabetical order, to `repository/c.json`:

```json
{
  "name": "CSV Table",
  "details": "https://github.com/MMSs/sublime-csv-table",
  "labels": ["csv", "tsv", "formatting", "table"],
  "releases": [
    {
      "sublime_text": ">=4107",
      "tags": true
    }
  ]
}
```

Follow the checklist in that repository's pull request template. After it merges, every new tag reaches users with no further steps.
