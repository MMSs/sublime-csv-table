import assert from "node:assert/strict";
import { test } from "node:test";
import { bumpFor, nextVersion, prependRelease, releaseLine } from "./bump.mjs";

test("the PR title picks the bump", () => {
  assert.equal(bumpFor("fix: keep quoted numbers quoted", ""), "patch");
  assert.equal(bumpFor("perf: skip highlighting large files", ""), "patch");
  assert.equal(bumpFor("feat: add a pipe delimiter", ""), "minor");
  assert.equal(bumpFor("feat!: rename the command", ""), "major");
  assert.equal(bumpFor("fix: x", "BREAKING CHANGE: y"), "major");
  assert.equal(bumpFor("docs: fix a typo", ""), null);
  assert.equal(bumpFor("not conventional", ""), null);
});

test("a breaking change before 1.0 bumps the minor version", () => {
  assert.equal(nextVersion("0.0.0", "minor"), "0.1.0");
  assert.equal(nextVersion("0.1.0", "patch"), "0.1.1");
  assert.equal(nextVersion("0.3.2", "major"), "0.4.0");
  assert.equal(nextVersion("1.3.2", "major"), "2.0.0");
});

test("a release goes above the previous one", () => {
  const changelog = "# Changelog\n\nIntro.\n\n## [0.1.0] - 2026-01-01\n\n- old (#1)\n";
  const line = releaseLine("fix: new thing", "2");
  assert.equal(line, "- new thing (#2)");
  const result = prependRelease(changelog, "0.1.1", "2026-02-01", line);
  assert.ok(result.indexOf("[0.1.1]") < result.indexOf("[0.1.0]"));
  assert.ok(prependRelease("# Changelog\n", "0.1.0", "d", line).endsWith(`${line}\n`));
});
